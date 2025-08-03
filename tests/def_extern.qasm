OPENQASM 3;
extern foo(float);
def bar(float x) {
    foo(x);
}
qubit q;
bar(0.5);

