import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve

import pytest

OPENQASM_COMMIT = "cc93f2e397ebd1229461536c8a1e83842bdced13"

EXAMPLES = {
    "adder": f"https://raw.githubusercontent.com/openqasm/openqasm/{OPENQASM_COMMIT}/examples/adder.qasm",
    "qft": f"https://raw.githubusercontent.com/openqasm/openqasm/{OPENQASM_COMMIT}/examples/qft.qasm",
    "vqe": f"https://raw.githubusercontent.com/openqasm/openqasm/{OPENQASM_COMMIT}/examples/vqe.qasm",
}

# Directory to store generated C++ for inspection
OUTPUT_DIR = Path(__file__).with_name("generated")
OUTPUT_DIR.mkdir(exist_ok=True)


@pytest.mark.parametrize("name,url", EXAMPLES.items())
def test_qasm2cpp_conversion(name: str, url: str, tmp_path: Path):
    qasm_file = tmp_path / f"{name}.qasm"
    urlretrieve(url, qasm_file)

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

