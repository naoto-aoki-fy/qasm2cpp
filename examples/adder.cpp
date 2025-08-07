#include "qasm.hpp"

/* gate majority not supported */
/* gate unmaj not supported */

class userqasm : public qasm::qasm
{
public:
    void circuit() {
        using namespace qasm;
        
        qubits cin = qalloc(1);
        qubits a = qalloc(4);
        qubits b = qalloc(4);
        qubits cout = qalloc(1);
        bit ans = clalloc(5);
        uint<4> a_in = 1;
        uint<4> b_in = 15;
        reset(cin);
        reset(a);
        reset(b);
        reset(cout);
        for (unsigned int i : slice(0, 3)) {
            if (((bool)(a_in[i]))) {
                x()(a[i]);
            }
            if (((bool)(b_in[i]))) {
                x()(b[i]);
            }
        }
        majority()(cin[0], b[0], a[0]);
        for (unsigned int i : slice(0, 2)) {
            majority()(a[i], b[i + 1], a[i + 1]);
        }
        cx()(a[3], cout[0]);
        for (unsigned int i : slice(2, -1, 0)) {
            unmaj()(a[i], b[i + 1], a[i + 1]);
        }
        unmaj()(cin[0], b[0], a[0]);
        ans[slice(0, 3)] = measure(b[slice(0, 3)]);
        ans[4] = measure(cout[0]);
        
    }
};

extern "C" qasm::qasm* constructor() { return new userqasm(); }
