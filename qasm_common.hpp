#include <vector>

namespace qasm {

struct qubit {
    qubit operator[](int n) const;
};

struct slice {
    slice(int a, int b);
    slice(int a, int b, int c);
    std::vector<int>::const_iterator begin() const;
    std::vector<int>::const_iterator end() const;
};

template<int size>
struct bit {
    uint(unsigned int);
    int operator[](int n) const;
};

template<int size>
struct uint {
    uint();
    uint(unsigned int);
    int operator[](int n) const;
    int operator+(int n) const;
    friend int operator+(int lhs, uint const rhs);
    constexpr operator int() const noexcept;
};

template<int size>
struct float_ { };


void cx(qubit, qubit);
void h(qubit);
void s(qubit);
template<int size>
void ry(qubit, float_<size>);
void reset(qubit);

int measure(qubit);
} // namespace qasm
