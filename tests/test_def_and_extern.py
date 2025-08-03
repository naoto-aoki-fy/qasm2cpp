import subprocess
import sys
from pathlib import Path


def test_def_as_method_and_extern_global():
    qasm_file = Path(__file__).with_name("def_extern.qasm")
    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    code = result.stdout

    lines = code.splitlines()
    class_idx = next(i for i, line in enumerate(lines) if line.strip().startswith("class userqasm"))

    extern_lines = [line.strip() for line in lines[:class_idx] if line.strip()]
    assert any(line.startswith("extern void foo") for line in extern_lines)

    circuit_idx = next(i for i, line in enumerate(lines) if line.strip().startswith("void circuit"))
    method_lines = []
    for line in lines[class_idx + 1 : circuit_idx]:
        stripped = line.strip()
        if stripped and stripped not in {"public:", "{"}:
            method_lines.append(stripped)
    assert method_lines[0].startswith("void bar")

    start = next(
        i for i, line in enumerate(lines[circuit_idx:], circuit_idx) if line.strip() == "using namespace qasm;"
    ) + 1
    end = next(i for i, line in enumerate(lines[start:], start) if line.strip() == "}")
    body = [line.strip() for line in lines[start:end] if line.strip()]
    assert body[0].startswith("qubit")
    assert body[1] == "bar(0.5);"

