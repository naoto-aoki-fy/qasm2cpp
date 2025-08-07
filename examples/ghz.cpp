#include "qasm.hpp"


class userqasm : public qasm::qasm
{
public:
    void circuit() {
        using namespace qasm;
        
        qubits q = qalloc(14);
        bit<14> cl;
        h()(q);
        for (unsigned int i : slice(0, 13)) {
            x()(q[0], q[i]);
        }
        cl = measure(q);
        
    }
};

extern "C" qasm::qasm* constructor() { return new userqasm(); }
