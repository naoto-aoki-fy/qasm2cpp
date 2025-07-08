#!/usr/bin/env python3
"""
qasm2cpp.py ― OpenQASM 3 → C++‐like code translator
             （gate／def／for／if／cast／assign 2025-07 対応・新旧 AST 両対応）

  * uint[N]     → QasmUint<N>
  * bit[N]      → QasmBit<N>

Requirements:
    python -m pip install "openqasm3[parser]"

Usage:
    python qasm2cpp.py < input.qasm > output.cpp
    python qasm2cpp.py  input.qasm      # 標準出力へ生成コード
"""

from __future__ import annotations
import sys
import openqasm3
import openqasm3.ast as ast
from openqasm3.visitor import QASMVisitor


# --------------------------------------------------------------------
# 定数置換
# --------------------------------------------------------------------
CONST_REPLACE = {"pi": "M_PI"}        # math.h の円周率マクロ

# --------------------------------------------------------------------
# 旧版フォールバック (名前 / 整数 → 記号)
# --------------------------------------------------------------------
_OLD_NAME_MAP = {
    "ADD": "+", "SUB": "-", "MUL": "*",
    "DIV": "/", "DIVIDE": "/", "SLASH": "/",
    "MOD": "%", "MODULO": "%", "REM": "%",
    "POW": "**",
    "GT":  ">",  "LT":  "<",  "GE": ">=", "LE": "<=",
    "EQ": "==",  "NE": "!=",
    "LAND": "&&", "LOR": "||",
    "BITOR": "|", "BITXOR": "^", "BITAND": "&",
    "SHL": "<<", "SHR": ">>",
}
_OLD_VALUE_MAP = {
     0:  ">",   1:  "<",   2: ">=",  3: "<=",
     4: "==",   5: "!=",   6: "&&",  7: "||",
     8:  "|",   9:  "^",  10:  "&", 11: "<<", 12: ">>",
    13:  "+",  14: "-",  15:  "*", 16:  "/", 17:  "%",
    18: "**",
}

# --------------------------------------------------------------------
# Enum → 記号
# --------------------------------------------------------------------
_DYNAMIC_OPMAP: dict[ast.BinaryOperator | ast.UnaryOperator, str] = {
    **{op: str(op).split('.', 1)[1] for op in ast.BinaryOperator},
    **{op: str(op).split('.', 1)[1] for op in ast.UnaryOperator},
}

def op_str(op: ast.BinaryOperator | ast.UnaryOperator) -> str:
    """OpenQASM 3 演算子 Enum → C 記号"""
    if op in _DYNAMIC_OPMAP:
        return _DYNAMIC_OPMAP[op]
    if (n := getattr(op, 'name', None)) in _OLD_NAME_MAP:
        return _OLD_NAME_MAP[n]
    return _OLD_VALUE_MAP.get(op.value, '?')    # 旧版: 整数値

# --------------------------------------------------------------------
# AST 世代間互換 ― ノード名の差分を吸収
# --------------------------------------------------------------------
GateDefNode = getattr(ast, "QuantumGateDefinition",
                      getattr(ast, "GateDeclaration", None))
if GateDefNode is None:
    raise RuntimeError("この openqasm3 には Gate 定義ノードが見当たりません。")

_DEF_NODE_NAMES = (
    "SubroutineDefinition",      # openqasm3 ≥0.11
    "FunctionDefinition",        # openqasm3 ≥0.10
    "DefStatement",              # 旧称
)
_DEF_NODES = [getattr(ast, n) for n in _DEF_NODE_NAMES if hasattr(ast, n)]

_FOR_NODE_NAMES = ("ForInLoop", "ForStatement", "ForLoop")
_IF_NODE_NAMES  = ("IfStatement", "ConditionalStatement", "BranchingStatement")
CAST_NODE       = getattr(ast, "CastExpression",
                  getattr(ast, "TypeCastExpression", None))

_FOR_NODES = [getattr(ast, n) for n in _FOR_NODE_NAMES if hasattr(ast, n)]
_IF_NODES  = [getattr(ast, n) for n in _IF_NODE_NAMES  if hasattr(ast, n)]

_CONST_NODE_NAMES = (
    "ConstantDeclaration",     # openqasm3 ≥0.10
    "ConstDeclaration",        # 旧称
    "ConstantDefinition",      # 派生実装の別名
)
_CONST_NODES = [getattr(ast, n) for n in _CONST_NODE_NAMES if hasattr(ast, n)]

def _visit_const_common(self, node):
    """const 宣言を C++ constexpr へ変換"""
    ctype = self._ctype(node.type)
    name  = node.identifier.name
    rhs   = self._expr(getattr(node, "value",
                     getattr(node, "init_expression", None)))
    self.emit(f"constexpr {ctype} {name} = {rhs};")

# ----------  ★ Assignment ノード名を拡充 (2025-07)  ----------
_ASSIGN_NODE_NAMES = (
    "AssignmentStatement", "UpdateStatement", "SetStatement", "Assignment",
    "ClassicalAssignment",              # 新 AST
    "AssignmentExpression",             # ExpressionStatement から検出
)
_ASSIGN_NODES = [getattr(ast, n) for n in _ASSIGN_NODE_NAMES if hasattr(ast, n)]

def _visit_assign_common(self, node):
    """代入文: 左辺と右辺の属性名が世代で異なるので網羅的に拾う"""
    lhs = next((getattr(node, a) for a in
               ("target", "lvalue", "identifier", "left", "lhs") if hasattr(node, a)), None)
    rhs = next((getattr(node, a) for a in
               ("expression", "value", "rvalue", "rhs", "right") if hasattr(node, a)), None)
    if lhs is None or rhs is None:      # 予防
        return
    self.emit(f"{self._expr(lhs)} = {self._expr(rhs)};")

# --------------------------------------------------------------------
# C++‐like コード出力
# --------------------------------------------------------------------
class CEmitter(QASMVisitor[None]):
    def __init__(self) -> None:
        self.lines: list[str] = []
        self._indent = 0

    # ------------- 出力支援
    def emit(self, line: str = "") -> None:
        self.lines.append("    " * self._indent + line)

    def code(self) -> str:
        return "\n".join(self.lines)

    # ------------- 型
    def _ctype(self, ctype: ast.ClassicalType) -> str:  # noqa: C901
        if isinstance(ctype, ast.UintType) and ctype.size is not None:
            return f"QasmUint<{self._expr(ctype.size)}>"
        if isinstance(ctype, ast.BitType) and ctype.size is not None:
            return f"QasmBit<{self._expr(ctype.size)}>"
        if isinstance(ctype, ast.FloatType) and getattr(ctype, "size", None) is not None:
            return f"QasmFloat<{self._expr(ctype.size)}>"
        if hasattr(ast, "AngleType") and isinstance(ctype, ast.AngleType) and getattr(ctype, "size", None) is not None:
            return f"QasmFloat<{self._expr(ctype.size)}>"
        if isinstance(ctype, (ast.BitType, ast.IntType)):
            return "int"
        if isinstance(ctype, ast.UintType):
            return "unsigned int"
        if isinstance(ctype, ast.FloatType):
            return "double"
        if hasattr(ast, "AngleType") and isinstance(ctype, ast.AngleType):
            return "double"
        if isinstance(ctype, ast.BoolType):
            return "bool"
        return "int"

    # ------------- 式
    def _expr(self, expr: ast.Expression):  # noqa: C901
        # 型キャスト
        if (
            (CAST_NODE and isinstance(expr, CAST_NODE))
            or (hasattr(ast, "Cast") and isinstance(expr, ast.Cast))
        ):
            tgt   = getattr(expr, "type",
                    getattr(expr, "target_type",
                    getattr(expr, "target", None)))
            inner = getattr(expr, "expression",
                    getattr(expr, "argument",
                    getattr(expr, "value", None)))
            if tgt and inner:
                return f"(({self._ctype(tgt)})({self._expr(inner)}))"

        # ----------  ★ AssignmentExpression も式として扱う  ----------
        if "AssignmentExpression" in _ASSIGN_NODE_NAMES and isinstance(expr, getattr(ast, "AssignmentExpression", ())):
            lval = self._expr(expr.lvalue)
            rval = self._expr(expr.rvalue)
            return f"({lval} = {rval})"

        match expr:
            case ast.Identifier(name=n):
                return CONST_REPLACE.get(n, n)
            case ast.IntegerLiteral(value=v) | ast.FloatLiteral(value=v):
                return str(v)
            case ast.BooleanLiteral(value=v):
                return "true" if v else "false"
            case ast.UnaryExpression(op=o, expression=e):
                return f"{op_str(o)}{self._expr(e)}"
            case ast.BinaryExpression(op=o, lhs=l, rhs=r):
                return f"{self._expr(l)} {op_str(o)} {self._expr(r)}"
            case ast.FunctionCall(name=ast.Identifier(name=n), arguments=args):
                return f"{n}(" + ", ".join(self._expr(a) for a in args) + ")"
            case _ if hasattr(ast, "CallExpression") and isinstance(expr, ast.CallExpression):
                callee = getattr(expr, "callee", None)
                args   = getattr(expr, "arguments", [])
                callee_str = self._expr(callee) if not isinstance(callee, ast.Identifier) else callee.name
                return f"{callee_str}(" + ", ".join(self._expr(a) for a in args) + ")"
            case ast.QuantumMeasurement(qubit=q):
                return f"MEASURE({self._qubit(q)})"
            case ast.IndexExpression(collection=c, index=i):
                return f"{self._expr(c)}[{self._index(i)}]"
            case ast.RangeDefinition():
                return self._index(expr)
            case _:
                return "<expr>"

    def _index(self, idx: ast.IndexElement):  # noqa: C901
        if isinstance(idx, ast.DiscreteSet):
            return ", ".join(self._expr(v) for v in idx.values)
        if isinstance(idx, ast.RangeDefinition):
            s = self._expr(idx.start) if idx.start else ""
            e = self._expr(idx.end)   if idx.end   else ""
            p = self._expr(idx.step)  if idx.step  else ""
            if p:
                return f"QasmSlice({s}, {e}, {p})"
            return f"QasmSlice({s}, {e})"
        if isinstance(idx, list) and len(idx) == 1:
            return self._expr(idx[0])
        return "<idx>"

    def _qubit(self, q) -> str:
        if isinstance(q, ast.Identifier):
            return q.name
        if isinstance(q, ast.IndexExpression):
            return self._expr(q)
        if isinstance(q, ast.IndexedIdentifier):
            base = q.name.name
            parts = "][".join(self._index(i) for i in q.indices)
            return f"{base}[{parts}]"
        return str(q)

    # ----------------------------------------------------------------
    # visitor 実装
    # ----------------------------------------------------------------
    def visit_Program(self, node: ast.Program):
        self.emit("#include <stdio.h>")
        self.emit("#include <math.h>")
        self.emit("#include \"qasm_common.hpp\"")
        self.emit("")

        # --- グローバル constexpr 生成 ---
        for s in node.statements:
            if isinstance(s, tuple(_CONST_NODES)):
                self.visit(s)

        # extern 宣言
        for s in node.statements:
            if hasattr(ast, "ExternDeclaration") and isinstance(s, ast.ExternDeclaration):
                self.visit(s)

        # gate / def 前方宣言
        for s in node.statements:
            if isinstance(s, (GateDefNode, * _DEF_NODES)):
                self.visit(s)

        self.emit("int main(void) {")
        self._indent += 1
        extern_cls = getattr(ast, "ExternDeclaration", None)
        exclude = (GateDefNode, *_DEF_NODES, *_CONST_NODES)
        if extern_cls is not None:
            exclude = (*exclude, extern_cls)
        for s in node.statements:
            if not isinstance(s, exclude):
                self.visit(s)
        self.emit("return 0;")
        self._indent -= 1
        self.emit("}")
        return self.code()

    # ---- gate 定義
    def visit_QuantumGateDefinition(self, node: GateDefNode):  # type: ignore[override]
        gname = node.name.name
        qs = [f"qubit {q.name}" for q in node.qubits]
        cs = [f"double {p.name}" for p in getattr(node, "arguments", [])]
        sig = ", ".join(qs + cs) or "void"
        self.emit(f"void {gname}({sig}) {{")
        self._indent += 1
        for s in node.body:
            self.visit(s)
        self._indent -= 1
        self.emit("}")
        self.emit("")

    # ---- def / function / subroutine
    def _visit_def_common(self, node):  # noqa: C901
        fname = node.name.name
        params: list[str] = []

        # Collect parameter list across AST generations
        param_list = None
        for attr in ("parameters", "arguments"):
            if hasattr(node, attr):
                param_list = getattr(node, attr)
                break
        if param_list is None:
            param_list = []

        for p in param_list:
            ptype = getattr(p, "type", None)
            pname = getattr(p, "identifier", getattr(p, "name", None))
            if isinstance(pname, ast.Identifier):
                pname = pname.name

            is_qubit_arg = False
            if hasattr(ast, "QuantumArgument") and isinstance(p, ast.QuantumArgument):
                is_qubit_arg = True
            elif hasattr(ast, "QubitType") and isinstance(ptype, ast.QubitType):
                is_qubit_arg = True

            if is_qubit_arg:
                if hasattr(p, "size") and p.size is not None:
                    params.append(f"qubit {pname}[{self._expr(p.size)}]")
                else:
                    params.append(f"qubit {pname}")
            else:
                params.append(f"{self._ctype(ptype)} {pname}")

        sig = ", ".join(params) if params else "void"
        rtype = self._ctype(getattr(node, "return_type", None)) if getattr(node, "return_type", None) else "void"
        self.emit(f"{rtype} {fname}({sig}) {{")
        self._indent += 1
        body = getattr(node, "body",
                       getattr(node, "program",
                       getattr(node, "block", [])))
        if isinstance(body, ast.Program):
            body = body.statements
        for s in body:
            self.visit(s)
        self._indent -= 1
        self.emit("}")
        self.emit("")

    for cls in _DEF_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_def_common    # type: ignore

    # ---- 宣言
    def visit_ExternDeclaration(self, node: ast.ExternDeclaration):
        name = node.name.name
        params = ", ".join(self._ctype(a.type) for a in node.arguments)
        rtype = self._ctype(node.return_type) if node.return_type else "void"
        self.emit(f"extern {rtype} {name}({params});")

    def visit_QubitDeclaration(self, node: ast.QubitDeclaration):
        size = self._expr(node.size) if node.size else "1"
        self.emit(f"qubit {node.qubit.name}[{size}];")

    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration):  # noqa: C901
        ctype_str = self._ctype(node.type)
        name  = node.identifier.name

        is_template_uint   = isinstance(node.type, ast.UintType)  and node.type.size is not None
        is_template_bit    = isinstance(node.type, ast.BitType)   and node.type.size is not None
        is_template_float  = isinstance(node.type, ast.FloatType) and node.type.size is not None
        template = is_template_uint or is_template_bit or is_template_float
        arr = "" if template else (
            f"[{self._expr(node.type.size)}]"
            if isinstance(node.type, (ast.BitType, ast.UintType)) and node.type.size else "")

        if node.init_expression is not None:
            rhs = (str(node.init_expression.value) if is_template_uint and isinstance(node.init_expression, ast.IntegerLiteral)
                   else f"MEASURE({self._qubit(node.init_expression.qubit)})"
                   if isinstance(node.init_expression, ast.QuantumMeasurement)
                   else self._expr(node.init_expression))
            self.emit(f"{ctype_str} {name}{arr} = {rhs};")
        else:
            self.emit(f"{ctype_str} {name}{arr};")

    # ---- 量子命令
    def visit_QuantumGate(self, node: ast.QuantumGate):
        gname = node.name.name
        qargs = ", ".join(self._qubit(q) for q in node.qubits)
        params = ", ".join(self._expr(a) for a in node.arguments)
        arglist = ", ".join(x for x in (qargs, params) if x)
        self.emit(f"{gname}({arglist});")

    def visit_QuantumMeasurementStatement(self, node: ast.QuantumMeasurementStatement):
        src = self._qubit(node.measure.qubit)
        if node.target:
            tgt = self._qubit(node.target)
            self.emit(f"{tgt} = MEASURE({src});")
        else:
            self.emit(f"MEASURE({src});")

    def visit_ReturnStatement(self, node: ast.ReturnStatement):
        expr = self._expr(node.expression) if getattr(node, "expression", None) else ""
        self.emit(f"return {expr};")

    def visit_QuantumBarrier(self, node: ast.QuantumBarrier):
        qs = ", ".join(self._qubit(q) for q in node.qubits)
        self.emit(f"/* barrier {qs} */")

    def visit_QuantumReset(self, node: ast.QuantumReset):
        self.emit(f"RESET({self._qubit(node.qubits)});")

    # ---------- if / for（世代差分を共通処理に集約） ----------
    def _visit_if_common(self, node):
        cond = self._expr(getattr(node, "condition",
                          getattr(node, "cond", None)))
        then_attrs = ("then_branch", "then_body", "if_block", "body", "true_body", "program")
        tbody = next((getattr(node, a) for a in then_attrs if hasattr(node, a)), [])
        if not isinstance(tbody, list):
            tbody = [tbody]
        else_attrs = ("else_branch", "else_body", "false_body")
        ebody = next((getattr(node, a) for a in else_attrs if hasattr(node, a)), None)
        if ebody and not isinstance(ebody, list):
            ebody = [ebody]
        self.emit(f"if ({cond}) {{")
        self._indent += 1
        for s in tbody:
            self.visit(s)
        self._indent -= 1
        if ebody:
            self.emit("} else {")
            self._indent += 1
            for s in ebody:
                self.visit(s)
            self._indent -= 1
        self.emit("}")

    def _visit_for_common(self, node):  # noqa: C901
        var = getattr(node, "loop_variable",
               getattr(node, "target",
               getattr(node, "identifier", None)))
        vname = var.name if isinstance(var, ast.Identifier) else str(var)
        itr = None
        for attr in ("set_declaration", "set", "set_expression", "iter"):
            if hasattr(node, attr):
                itr = getattr(node, attr)
                break
        body  = getattr(node, "body", getattr(node, "block", []))
        if isinstance(body, ast.Program):
            body = body.statements
        if isinstance(itr, ast.RangeDefinition):
            start = self._expr(itr.start or ast.IntegerLiteral(0))
            end   = self._expr(itr.end   or ast.IntegerLiteral(0))
            step  = self._expr(itr.step) if itr.step is not None else None
            vctype = "int"
            if hasattr(node, "type"):
                vctype = self._ctype(node.type)
            elif hasattr(var, "type"):
                vctype = self._ctype(var.type)
            slice_expr = f"QasmSlice({start}, {end})" if step is None else f"QasmSlice({start}, {step}, {end})"
            self.emit(f"for ({vctype} {vname} : {slice_expr}) {{")
            self._indent += 1
        elif isinstance(itr, ast.DiscreteSet):
            vals = ", ".join(self._expr(v) for v in itr.values)
            arr  = f"__vals_{id(node)}"
            self.emit(f"int {arr}[] = {{{vals}}};")
            self.emit(f"for (size_t __i = 0; __i < sizeof({arr})/sizeof({arr}[0]); ++__i) {{")
            self._indent += 1
            self.emit(f"int {vname} = {arr}[__i];")
        else:
            self.emit("/* unsupported for-loop */ for (;;) {")
            self._indent += 1
        for s in body:
            self.visit(s)
        self._indent -= 1
        self.emit("}")

    for cls in _IF_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_if_common      # type: ignore
    for cls in _FOR_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_for_common     # type: ignore
    for cls in _ASSIGN_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_assign_common  # type: ignore

    # ----------  ★ ExpressionStatement をサポート  ----------
    def visit_ExpressionStatement(self, node: ast.ExpressionStatement):
        self.emit(f"{self._expr(node.expression)};")

# ノードを visitor にバインド（const）
for cls in _CONST_NODES:
    setattr(CEmitter, f"visit_{cls.__name__}", _visit_const_common)

# --------------------------------------------------------------------
# front-end
# --------------------------------------------------------------------
def translate(qasm_src: str) -> str:
    program = openqasm3.parse(qasm_src)
    return CEmitter().visit(program)


def main() -> None:
    src = sys.stdin.read() if len(sys.argv) == 1 else open(sys.argv[1]).read()
    print(translate(src))


if __name__ == "__main__":
    main()
