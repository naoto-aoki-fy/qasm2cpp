# qasm2cpp

This repository contains a simple translator from [OpenQASM 3](https://openqasm.github.io/) to C++‑like code.  The `qasm2cpp.py` script reads an OpenQASM file and prints C++ source that relies on a minimal runtime provided in `qasm_common.hpp`.

The folder `openqasm` is a copy of the official OpenQASM specification and examples for reference.  Only the translator script and the small header in this directory are required to use the converter.

## Requirements

- Python 3
- The `openqasm3` parser package

Dependencies can be installed with

```bash
python -m pip install -r requirements.txt
```

## Usage

```bash
python qasm2cpp.py < input.qasm > output.cpp
# or
python qasm2cpp.py input.qasm > output.cpp
```

The generated code includes `qasm_common.hpp` and calls functions such as `qasm::cx`, `qasm::h` or `qasm::measure`.  These are declared in the header as stubs so the output can be compiled or further adapted.

## Example

Running the converter on one of the OpenQASM examples:

```bash
python qasm2cpp.py openqasm/examples/adder.qasm > adder.cpp
```

This produces a C++ file beginning with

```cpp
#include <stdio.h>
#include <math.h>
#include "qasm_common.hpp"
```

which contains C++ functions for each gate and a `circuit` function inside the
`qasm` namespace implementing the quantum program.

