#include "qasm.hpp"


class userqasm : public qasm::qasm
{
public:
    void circuit() {
        using namespace qasm;
        
        qubits q = qalloc(4);
        bit<4> c;
        reset(q);
        x()(q[0]);
        x()(q[2]);
        /* barrier q */
        h()(q[0]);
        cphase(M_PI / 2)(q[1], q[0]);
        h()(q[1]);
        cphase(M_PI / 4)(q[2], q[0]);
        cphase(M_PI / 2)(q[2], q[1]);
        h()(q[2]);
        cphase(M_PI / 8)(q[3], q[0]);
        cphase(M_PI / 4)(q[3], q[1]);
        cphase(M_PI / 2)(q[3], q[2]);
        h()(q[3]);
        c = measure(q);
        
    }
};

extern "C" qasm::qasm* constructor() { return new userqasm(); }
