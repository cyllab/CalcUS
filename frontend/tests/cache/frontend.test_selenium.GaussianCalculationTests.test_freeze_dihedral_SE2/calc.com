%chk=in.chk
%nproc=4
%mem=2000MB
#p opt(modredundant) AM1

File created by ccinput

0 1
C    4.29180000   3.65880000   0.00000000
H    4.64850000   2.65000000   0.00000000
H    4.64850000   4.16320000   0.87070000
H    4.64850000   4.16320000  -0.87970000
H    3.22180000   3.65880000   0.00000000

D 1 2 3 4 F
D 2 3 4 5 F
