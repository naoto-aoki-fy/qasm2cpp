#!/usr/bin/env bash
set -euo pipefail

OPENQASM_COMMIT="cc93f2e397ebd1229461536c8a1e83842bdced13"
BASE_URL="https://raw.githubusercontent.com/openqasm/openqasm/${OPENQASM_COMMIT}/examples"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for name in vqe qft adder; do
    curl -L "${BASE_URL}/${name}.qasm" -o "${SCRIPT_DIR}/${name}.qasm"
done
