import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
DOWNLOAD_SCRIPT = EXAMPLES_DIR / "download_examples.sh"
subprocess.run(["bash", str(DOWNLOAD_SCRIPT)], check=True)

EXAMPLES = ["adder", "qft", "vqe"]

# Directory to store generated C++ for inspection
OUTPUT_DIR = Path(__file__).with_name("generated")
OUTPUT_DIR.mkdir(exist_ok=True)


@pytest.mark.parametrize("name", EXAMPLES)
def test_qasm2cpp_conversion(name: str):
    qasm_file = EXAMPLES_DIR / f"{name}.qasm"

    result = subprocess.run(
        [sys.executable, "qasm2cpp.py", str(qasm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "class userqasm" in result.stdout

    out_file = OUTPUT_DIR / f"{name}.cpp"
    out_file.write_text(result.stdout)
    print(f"Generated {out_file}")
