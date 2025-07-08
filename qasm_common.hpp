#include <vector>

struct qubit {
    qubit operator[](int n) const;
};

struct QasmSlice {
    QasmSlice(int a, int b);
    QasmSlice(int a, int b, int c);
    std::vector<int>::const_iterator begin() const;
    std::vector<int>::const_iterator end() const;
};

template<int size>
struct QasmBit {
    QasmUint(unsigned int);
    int operator[](int n) const;
};

template<int size>
struct QasmUint {
    QasmUint();
    QasmUint(unsigned int);
    int operator[](int n) const;
    int operator+(int n) const;
    friend int operator+(int lhs, QasmUint const rhs);
    constexpr operator int() const noexcept;
};

template<int size>
struct QasmFloat { };


namespace qasm {
void cx(qubit, qubit);
void h(qubit);
void s(qubit);
template<int size>
void ry(qubit, QasmFloat<size>);
void reset(qubit);

int measure(qubit);
} // namespace qasm
