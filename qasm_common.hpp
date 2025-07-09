#include <vector>

namespace qasm {

template<int size>
struct qubit {
    qubit<1> operator[](int n) const;
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


template<int A, int B>
void cx(qubit<A>, qubit<B>);
template<int A>
void h(qubit<A>);
template<int A>
void s(qubit<A>);
template<int Q, int F>
void ry(qubit<Q>, float_<F>);
template<int A>
void reset(qubit<A>);

template<int A>
int measure(qubit<A>);
} // namespace qasm
