#include <vector>

namespace qasm {

template<int size = -1>
struct qubit {
    qubit<1> operator[](int n) const;
    template<int size_new>
    operator qubit<size_new>() const;
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
struct float_ { double value; };


void cx(qubit<1>, qubit<1>);

void h(qubit<1>);

void s(qubit<1>);

template<int F>
void ry(qubit<1>, float_<F>);

template<int A>
void reset(qubit<A>);

template<int A>
int measure(qubit<A>);

} // namespace qasm
