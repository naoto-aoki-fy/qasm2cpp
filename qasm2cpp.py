#!/usr/bin/env python3
"""
qasm2c.py ― OpenQASM 3 → C++‑like code translator
           （gate／for／if／cast 対応・新旧 AST 両対応）
   * uint[N]     → QasmUint<N>
   * bit[N]      → QasmBit<N>

Requirements:
    python -m pip install "openqasm3[parser]"

Usage:
    python qasm2c.py < input.qasm > output.cpp
    python qasm2c.py  input.qasm      # 標準出力へ生成コード
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
# Binary と Unary をまとめたキャッシュ
_DYNAMIC_OPMAP: dict[ast.BinaryOperator | ast.UnaryOperator, str] = {
    **{op: str(op).split('.', 1)[1] for op in ast.BinaryOperator},
    **{op: str(op).split('.', 1)[1] for op in ast.UnaryOperator},
}

def op_str(op: ast.BinaryOperator | ast.UnaryOperator) -> str:
    """OpenQASM 3 演算子 Enum → C 記号"""
    if op in _DYNAMIC_OPMAP:                    # ← ここを変更
        return _DYNAMIC_OPMAP[op]
    if (n := getattr(op, 'name', None)) in _OLD_NAME_MAP:
        return _OLD_NAME_MAP[n]
    return _OLD_VALUE_MAP.get(op.value, '?')    # 旧版: 整数値

# --------------------------------------------------------------------
# AST 世代間互換
# --------------------------------------------------------------------
GateDefNode = getattr(ast, "QuantumGateDefinition",
                      getattr(ast, "GateDeclaration", None))
if GateDefNode is None:
    raise RuntimeError("この openqasm3 には Gate 定義ノードが見当たりません。")

# for / if / cast ノード
_FOR_NODE_NAMES = ("ForInLoop", "ForStatement", "ForLoop")
_IF_NODE_NAMES  = ("IfStatement", "ConditionalStatement", "BranchingStatement")
CAST_NODE       = getattr(ast, "CastExpression",
                  getattr(ast, "TypeCastExpression", None))

_FOR_NODES = [getattr(ast, n) for n in _FOR_NODE_NAMES if hasattr(ast, n)]
_IF_NODES  = [getattr(ast, n) for n in _IF_NODE_NAMES  if hasattr(ast, n)]

# --------------------------------------------------------------------
# C++‑like コード出力
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
        """OpenQASM classical type → C++ type string"""
        # 専用テンプレート型: uint[N] → QasmUint<N>, bit[N] → QasmBit<N>
        if isinstance(ctype, ast.UintType) and ctype.size is not None:
            size = self._expr(ctype.size)
            return f"QasmUint<{size}>"
        if isinstance(ctype, ast.BitType) and ctype.size is not None:
            size = self._expr(ctype.size)
            return f"QasmBit<{size}>"

        # フォールバック
        if isinstance(ctype, (ast.BitType, ast.IntType)):
            return "int"
        if isinstance(ctype, ast.UintType):
            return "unsigned int"
        if isinstance(ctype, ast.FloatType):
            return "double"
        if isinstance(ctype, ast.BoolType):
            return "bool"
        return "int"

    # ------------- 式
    def _expr(self, expr: ast.Expression):  # noqa: C901
        # --- 型キャスト対応（新旧 Cast ノードを包括）
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

            # ★ 関数呼び出しは純粋に関数として出力
            case ast.FunctionCall(name=ast.Identifier(name=n), arguments=args):
                return f"{n}(" + ", ".join(self._expr(a) for a in args) + ")"

            # ★ openqasm3 ≥0.11 の CallExpression も同様
            case _ if hasattr(ast, "CallExpression") and isinstance(expr, ast.CallExpression):  # type: ignore[attr-defined]
                callee = getattr(expr, "callee", None)
                args   = getattr(expr, "arguments", [])
                callee_str = self._expr(callee) if not isinstance(callee, ast.Identifier) else callee.name
                return f"{callee_str}(" + ", ".join(self._expr(a) for a in args) + ")"

            case ast.IndexExpression(collection=c, index=i):
                return f"{self._expr(c)}[{self._index(i)}]"
            case ast.RangeDefinition():
                return self._index(expr)
            case _:
                return "<expr>"

    def _index(self, idx: ast.IndexElement):  # noqa: C901
        if isinstance(idx, ast.DiscreteSet):                  # {0,2,4}
            return ", ".join(self._expr(v) for v in idx.values)
        if isinstance(idx, ast.RangeDefinition):              # 0:3(:1)
            s = self._expr(idx.start) if idx.start else ""
            e = self._expr(idx.end)   if idx.end   else ""
            p = self._expr(idx.step)  if idx.step  else ""
            # OpenQASM スライス → C 側では QasmSlice(lo, hi [, step]) マクロで表現
            if p:                                     # 3 引数 (start:end:step)
                return f"QasmSlice({s}, {e}, {p})"
            return f"QasmSlice({s}, {e})"             # 2 引数 (start:end)
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
    # ---- ルート
    def visit_Program(self, node: ast.Program):
        self.emit("#include <stdio.h>")
        self.emit("#include <math.h>")
        self.emit("")

        for s in node.statements:              # gate 前方宣言
            if isinstance(s, GateDefNode):
                self.visit(s)

        self.emit("int main(void) {")
        self._indent += 1
        for s in node.statements:
            if not isinstance(s, GateDefNode):
                self.visit(s)
        self.emit("return 0;")
        self._indent -= 1
        self.emit("}")
        return self.code()

    # ---- gate
    def visit_QuantumGateDefinition(self, node: GateDefNode):  # type: ignore[override]
        gname = node.name.name.upper()
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

    # ---- 宣言
    def visit_QubitDeclaration(self, node: ast.QubitDeclaration):
        size = self._expr(node.size) if node.size else "1"
        self.emit(f"qubit {node.qubit.name}[{size}];")

    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration):  # noqa: C901
        ctype_str = self._ctype(node.type)
        name  = node.identifier.name

        # テンプレート型かどうか判断
        is_template_uint = isinstance(node.type, ast.UintType) and node.type.size is not None
        is_template_bit  = isinstance(node.type, ast.BitType) and node.type.size is not None

        # 配列修飾子: テンプレート型なら付けない
        if is_template_uint or is_template_bit:
            arr = ""
        else:
            arr = (
                f"[{self._expr(node.type.size)}]"
                if isinstance(node.type, (ast.BitType, ast.UintType)) and node.type.size else ""
            )

        # 右辺生成
        if node.init_expression is not None:
            if is_template_uint and isinstance(node.init_expression, ast.IntegerLiteral):
                rhs = str(node.init_expression.value)
            elif isinstance(node.init_expression, ast.QuantumMeasurement):
                rhs = f"MEASURE({self._qubit(node.init_expression.qubit)})"
            else:
                rhs = self._expr(node.init_expression)
            self.emit(f"{ctype_str} {name}{arr} = {rhs};")
        else:
            self.emit(f"{ctype_str} {name}{arr};")

    # ---- 量子命令
    def visit_QuantumGate(self, node: ast.QuantumGate):
        gname = node.name.name.upper()
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

    def visit_QuantumBarrier(self, node: ast.QuantumBarrier):
        qs = ", ".join(self._qubit(q) for q in node.qubits)
        self.emit(f"/* barrier {qs} */")

    def visit_QuantumReset(self, node: ast.QuantumReset):
        self.emit(f"RESET({self._qubit(node.qubits)});")

    # ---------- if / for（世代差分を共通処理に集約） ------------------
    def _visit_if_common(self, node):
        cond = self._expr(getattr(node, "condition",
                          getattr(node, "cond", None)))
        then_attrs = ("then_branch", "then_body", "if_block",
                      "body", "true_body", "program")
        tbody = next((getattr(node, a) for a in then_attrs if hasattr(node, a)),
                     [])
        if not isinstance(tbody, list):
            tbody = [tbody]
        else_attrs = ("else_branch", "else_body", "false_body")
        ebody = next((getattr(node, a) for a in else_attrs if hasattr(node, a)),
                     None)
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
            if step is None:
                # 2-引数レンジ (start:end) ― そのまま
                slice_expr = f"QasmSlice({start}, {end})"
            else:
                # 3-引数レンジ (start:step:end) → QasmSlice(start, step, end)
                slice_expr = f"QasmSlice({start}, {step}, {end})"
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

    # --- ノード名にバインド
    for cls in _IF_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_if_common      # type: ignore
    for cls in _FOR_NODES:
        locals()[f"visit_{cls.__name__}"] = _visit_for_common     # type: ignore

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
