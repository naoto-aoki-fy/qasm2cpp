import subprocess
import sys
from pathlib import Path


def test_qubits_declared_at_top():
    qasm_file = Path(__file__).with_name("late_qubit.qasm")
    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    code = result.stdout
    assert "int circuit" in code

    lines = code.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "int circuit(void) {") + 1
    end = next(i for i, line in enumerate(lines) if line.strip() == "return 0;")
    body = [line.strip() for line in lines[start:end] if line.strip()]
    assert body[0].startswith("qasm::qubit")
    assert body[1].startswith("qasm::qubit")
    assert body[2] == "qasm::h(q);"
    assert body[3] == "qasm::x(r);"
