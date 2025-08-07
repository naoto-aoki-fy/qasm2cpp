import subprocess
import sys
from pathlib import Path

def test_ctrl_modifier(tmp_path: Path):
    qasm = """OPENQASM 3;
qubit[2] q;
ctrl @ x q[0], q[1];
"""
    qasm_file = tmp_path / "ctrl.qasm"
    qasm_file.write_text(qasm)

    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "(ctrl() * x())(q[0], q[1]);" in result.stdout
