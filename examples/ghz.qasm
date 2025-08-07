qubit[14] q;
bit[14] cl;

h q;
for uint i in [0:13] {
    ctrl @ x q[0], q[i];
}

measure q -> cl;