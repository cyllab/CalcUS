import decimal

decimal.getcontext().prec = 50

HARTREE_VAL = decimal.Decimal(2625.499638)
E_VAL = decimal.Decimal(2.7182818284590452353602874713527)
R_CONSTANT = decimal.Decimal(8.314)
TEMP = decimal.Decimal(298)
SOLVENT_TABLE = {
    'Acetone': 'acetone',
    'Acetonitrile': 'acetonitrile',
    'Benzene': 'benzene',
    'Dichloromethane': 'ch2cl2',
    'Chloroform': 'chcl3',
    'Carbon disulfide': 'cs2',
    'Dimethylformamide': 'dmf',
    'Dimethylsulfoxide': 'dmso',
    'Diethyl ether': 'ether',
    'Water': 'h2o',
    'Methanol': 'methanol',
    'n-Hexane': 'n-hexane',
    'Tetrahydrofuran': 'thf',
    'Toluene': 'toluene',
        }

#Software->Method/Functional->Basis set->Atom->[m, b, R2]
NMR_REGRESSIONS = {
    'ORCA': {
            'PBEh-3c': {
                    '': {
                        'H': [-1.0758, 32.4963, 0.9957],
                        'C': [-1.0126, 198.0555, 0.9970],
                    },
                },
        },
    'Gaussian': {

        },
}
