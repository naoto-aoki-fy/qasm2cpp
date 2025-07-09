import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def clone_openqasm_repo(tmp_path_factory):
    repo_path = Path("openqasm")
    if repo_path.exists():
        return
    subprocess.run(
        ["git", "clone", "https://github.com/openqasm/openqasm.git", str(repo_path)],
        check=True,
    )
