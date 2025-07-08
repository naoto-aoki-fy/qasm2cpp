import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = [
    Path("openqasm/examples/adder.qasm"),
    Path("openqasm/examples/qft.qasm"),
    Path("openqasm/examples/vqe.qasm"),
]

# Directory to store generated C++ for inspection
OUTPUT_DIR = Path(__file__).with_name("generated")
OUTPUT_DIR.mkdir(exist_ok=True)

@pytest.mark.parametrize("qasm_file", EXAMPLES)
def test_qasm2cpp_conversion(qasm_file: Path):
    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "int main" in result.stdout

    out_file = OUTPUT_DIR / f"{qasm_file.stem}.cpp"
    out_file.write_text(result.stdout)
    print(f"Generated {out_file}")

