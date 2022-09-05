%chk=in.chk
%nproc=1
%mem=2000MB
#p sp M062X/Def2SVP SCRF(CPCM, Solvent=methanol, Read)

File created by ccinput

0 1
C    4.29180000   3.65880000   0.00000000
H    4.64850000   2.65000000   0.00000000
H    4.64850000   4.16320000   0.87070000
H    4.64850000   4.16320000  -0.87970000
H    3.22180000   3.65880000   0.00000000

Radii=bondi

