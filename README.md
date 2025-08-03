# qasm2cpp

This repository contains a simple translator from [OpenQASM 3](https://openqasm.github.io/) to C++‑like code.  The `qasm2cpp.py` script reads an OpenQASM file and prints C++ source that relies on a minimal runtime provided in `qasm.hpp`.

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

The generated code includes `qasm.hpp` and produces a small subclass of `qasm::qasm` with a `circuit` method.  Quantum operations are emitted using the fluent gate API, for example `h()(q);` or `(ctrl(2) * h())(q[0], q[1], q[2]);`.

## Example

Running the converter on one of the OpenQASM examples:

```bash
python qasm2cpp.py openqasm/examples/adder.qasm > adder.cpp
```

This produces a C++ file beginning with

```cpp
#include "qasm.hpp"

class userqasm : public qasm::qasm {
public:
    void circuit() {
        using namespace qasm;
        // ...
    }
};

extern "C" qasm::qasm* constructor() { return new userqasm(); }
```

The `circuit` method contains the translated quantum program.

