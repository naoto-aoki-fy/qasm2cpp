import subprocess
import sys
from pathlib import Path


def test_gate_definition_comment():
    qasm_file = Path(__file__).with_name("gate_definition.qasm")
    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    code = result.stdout
    assert "/* gate foo not supported */" in code

