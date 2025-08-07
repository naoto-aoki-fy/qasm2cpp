#include "qasm.hpp"

extern float_<prec> get_parameter(uint<prec>);
extern uint<prec> get_npaulis();
extern bit<2 * n> get_pauli(int);
extern float_<prec> update_energy(int, uint<prec>, float_<prec>);
/* gate entangler not supported */

class userqasm : public qasm::qasm
{
public:
    int xmeasure(qubit<> q) {
        using namespace qasm;
        
        h()(q);
        return measure(q);
    }
    
    int ymeasure(qubit<> q) {
        using namespace qasm;
        
        s()(q);
        h()(q);
        return measure(q);
    }
    
    int pauli_measurement(bit<2 * n> spec, qubit<n> q) {
        using namespace qasm;
        
        int b = 0;
        for (uint<prec> i : slice(0, n - 1)) {
            int temp;
            if (spec[i] == 1 && spec[n + i] == 0) {
                temp = xmeasure(q[i]);
            }
            if (spec[i] == 0 && spec[n + i] == 1) {
                temp = measure(q[i]);
            }
            if (spec[i] == 1 && spec[n + i] == 1) {
                temp = ymeasure(q[i]);
            }
            b = temp;
        }
        return b;
    }
    
    void trial_circuit(qubit<n> q) {
        using namespace qasm;
        
        for (int l : slice(0, layers - 1)) {
            for (uint<prec> i : slice(0, n - 1)) {
                float_<prec> theta;
                theta = get_parameter(l * layers + i);
                ry(theta)(q[i]);
            }
            if (l != layers - 1) {
                entangler()(q);
            }
        }
    }
    
    uint<prec> counts_for_term(bit<2 * n> spec, qubit<n> q) {
        using namespace qasm;
        
        uint<prec> counts;
        for (unsigned int i : slice(1, shots)) {
            int b;
            reset(q);
            trial_circuit()(q);
            b = pauli_measurement(spec, q);
            counts = ((int)(b));
        }
        return counts;
    }
    
    float_<prec> estimate_energy(qubit<n> q) {
        using namespace qasm;
        
        float_<prec> energy;
        uint<prec> npaulis = get_npaulis();
        for (int t : slice(0, npaulis - 1)) {
            bit spec = clalloc(2 * n);
            spec = get_pauli(t);
            uint<prec> counts;
            counts = counts_for_term(spec, q);
            energy = update_energy(t, counts, energy);
        }
        return energy;
    }
    
    void circuit() {
        using namespace qasm;
        
        constexpr int n = 10;
        constexpr int layers = 3;
        constexpr int prec = 16;
        constexpr int shots = 1000;
        qubits q = qalloc(n);
        float_<prec> energy;
        energy = estimate_energy(q);
        
    }
};

extern "C" qasm::qasm* constructor() { return new userqasm(); }
