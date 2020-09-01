import os

from .models import *
from django.core.management import call_command
from django.test import TestCase, Client
from .Gaussian_calculation import GaussianCalculation
from .ORCA_calculation import OrcaCalculation

TESTS_DIR = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")

BLUE = '\033[94m'
GREEN = '\033[92m'
END = '\033[0m'

def blue(msg):
    print("{}{} {}".format(BLUE, msg, END))

def green(msg):
    print("{}{} {}".format(GREEN, msg, END))

def gen_calc(params):
    step = BasicStep.objects.get(name=params['type'])

    charge = 0
    multiplicity = 1
    solvent = "Vacuum"
    solvation_model = ""
    basis_set = ""
    theory_level = ""
    method = ""
    misc = ""

    if 'charge' in params.keys():
        charge = int(params['charge'])

    if 'multiplicity' in params.keys():
        multiplicity = int(params['multiplicity'])

    if 'solvent' in params.keys():
        solvent = params['solvent']

    if 'solvation_model' in params.keys():
        solvation_model = params['solvation_model']

    if 'basis_set' in params.keys():
        basis_set = params['basis_set']

    if 'theory_level' in params.keys():
        theory_level = params['theory_level']

    if 'method' in params.keys():
        method = params['method']

    if 'misc' in params.keys():
        misc = params['misc']

    software = params['software']

    p = Parameters.objects.create(charge=charge, multiplicity=multiplicity, solvent=solvent, solvation_model=solvation_model, basis_set=basis_set, theory_level=theory_level, method=method, misc=misc)
    with open(os.path.join(TESTS_DIR, params['in_file'])) as f:
        lines = f.readlines()
        xyz_structure = ''.join(lines)

    s = Structure.objects.create(xyz_structure=xyz_structure)

    dummy = CalculationOrder.objects.create()
    calc = Calculation.objects.create(structure=s, step=step, parameters=p, order=dummy)

    if 'constraints' in params.keys():
        calc.constraints = params['constraints']

    return calc

class GaussianTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')

    def is_equivalent(self, ref, res):
        ref_lines = [i.strip() for i in ref.split('\n')]
        res_lines = [i.strip() for i in res.split('\n')]

        ind = 0
        while ref_lines[ind].find("#p") == -1:
            ind += 1

        ref_lines = ref_lines[ind:]

        ind = 0
        while res_lines[ind].find("#p") == -1:
            ind += 1

        res_lines = res_lines[ind:]

        if len(ref_lines) != len(res_lines):
            print("Different number of lines: {} and {}".format(len(ref_lines), len(res_lines)))
            print("----")
            blue(repr('\n'.join(ref_lines)))
            print("----")
            green(repr('\n'.join(res_lines)))
            print("----")
            return False

        for line1, line2 in zip(ref_lines, res_lines):
            if line1 != line2:
                print("")
                print("Difference found:")
                blue(line1)
                green(line2)
                print("")
                return False

        return True

    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(SMD, Solvent=Chloroform)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_SMD18(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'I.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD18',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(SMD, Solvent=Chloroform, Read)

        CalcUS

        -1 1
        I 0.0 0.0 0.0

        modifysph

        Br 2.60

        I 2.74

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_PCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'PCM',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(PCM, Solvent=Chloroform, Read)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        Radii=Bondi

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_PCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'PCM',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(PCM, Solvent=Chloroform, Read)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        Radii=Bondi

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_HF_CPCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp HF/3-21G SCRF(CPCM, Solvent=Chloroform, Read)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        Radii=Bondi

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_DFT(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_sp_DFT_misc(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'misc': 'nosymm 5D',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p sp M062X/Def2SVP nosymm 5D

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_SE(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_HF(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_opt_DFT(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freq_SE(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq AM1

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freq_HF(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq HF/3-21G

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freq_DFT(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p freq B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    #opt mod SE and HF

    def test_scan_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_1.4_10-1_2;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        B 1 2 S 10 0.03

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_90_10-2_1_3;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        A 2 1 3 S 10 -1.95

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_scan_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_0_10-4_1_5_8;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 4 1 5 8 S 10 17.99

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freeze_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-1_2;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        B 1 2 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_freeze_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-2_1_3;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        A 2 1 3 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))


    def test_freeze_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'Gaussian',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-4_1_5_8;',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(modredundant) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240

        D 4 1 5 8 F

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_nmr_DFT(self):
        params = {
                'type': 'NMR Prediction',
                'in_file': 'Cl.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p nmr B3LYP/6-31+G(d,p)

        CalcUS

        -1 1
        Cl 0.0 0.0 0.0

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

    def test_ts_DFT(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'Gaussian',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        gaussian = GaussianCalculation(calc)

        REF = """
        #p opt(ts, NoEigenTest, CalcFC) B3LYP/6-31+G(d,p)

        CalcUS

        0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677

        """

        self.assertTrue(self.is_equivalent(REF, gaussian.input_file))

        #combination tests


class OrcaTests(TestCase):
    def setUp(self):
        call_command('init_static_obj')


    def is_equivalent(self, ref, res):
        ref_lines = [i.strip() for i in ref.split('\n')]
        res_lines = [i.strip() for i in res.split('\n')]

        ind = 0
        while ref_lines[ind].strip() == '':
            ind += 1

        ind2 = len(ref_lines) - 1
        while ref_lines[ind2].strip() == '':
            ind2 -= 1

        ref_lines = ref_lines[ind:ind2+1]

        ind = 0
        while res_lines[ind].strip() == '':
            ind += 1

        res_lines = res_lines[ind:]

        if len(ref_lines) != len(res_lines):
            print("Different number of lines: {} and {}".format(len(ref_lines), len(res_lines)))
            print("----")
            blue(repr('\n'.join(ref_lines)))
            print("----")
            green(repr('\n'.join(res_lines)))
            print("----")
            return False

        for line1, line2 in zip(ref_lines, res_lines):
            if line1 != line2:
                if line1.find("nprocs") != -1:
                    pass
                else:
                    print("")
                    print("Difference found:")
                    blue(line1)
                    green(line2)
                    print("")
                    return False

        return True

    def test_sp_SE(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_HF(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_HF_SMD(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'SMD',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        %cpcm
        smd true
        SMDsolvent "Chloroform"
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))


    def test_sp_HF_CPCM(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                'solvent': 'Chloroform',
                'solvation_model': 'CPCM',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP HF 3-21G CPCM(Chloroform)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_DFT(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_DFT_misc(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'method': 'M06-2X',
                'basis_set': 'Def2-SVP',
                'charge': '-1',
                'misc': 'TightSCF',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP M062X Def2-SVP TightSCF
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_sp_MP2(self):
        params = {
                'type': 'Single-Point Energy',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'RI-MP2',
                'basis_set': 'cc-pVTZ',
                'charge': '-1',
                'misc': 'cc-pVTZ/C',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !SP RI-MP2 cc-pVTZ cc-pVTZ/C
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_SE(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_HF(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_opt_DFT(self):
        params = {
                'type': 'Geometrical Optimisation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_SE(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'AM1',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ AM1
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_HF(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'HF',
                'basis_set': '3-21G',
                'charge': '-1',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ HF 3-21G
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freq_DFT(self):
        params = {
                'type': 'Frequency Calculation',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !FREQ B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    #opt mod SE and HF

    def test_scan_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_1.4_10-1_2;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        B 0 1 = 9, 1.4, 10
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_scan_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_90_10-2_1_3;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        A 1 0 2 = 9, 90, 10
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_scan_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Scan_9_0_10-4_1_5_8;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Scan
        D 3 0 4 7 = 9, 0, 10
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freeze_bond_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-1_2;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { B 0 1 C }
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_freeze_angle_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-2_1_3;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { A 1 0 2 C }
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))


    def test_freeze_dihedral_DFT(self):
        params = {
                'type': 'Constrained Optimisation',
                'in_file': 'ethanol.xyz',
                'software': 'ORCA',
                'theory_level': 'Semi-empirical',
                'method': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                'constraints': 'Freeze-4_1_5_8;',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPT B3LYP 6-31+G(d,p)
        *xyz 0 1
        C         -1.31970       -0.64380        0.00000
        H         -0.96310       -1.65260        0.00000
        H         -0.96310       -0.13940       -0.87370
        H         -2.38970       -0.64380        0.00000
        C         -0.80640        0.08220        1.25740
        H         -1.16150        1.09160        1.25640
        H         -1.16470       -0.42110        2.13110
        O          0.62360        0.07990        1.25870
        H          0.94410        0.53240        2.04240
        *
        %geom Constraints
        { D 3 0 4 7 C }
        end
        end
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_nmr_DFT(self):
        params = {
                'type': 'NMR Prediction',
                'in_file': 'Cl.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '-1',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !NMR B3LYP 6-31+G(d,p)
        *xyz -1 1
        Cl 0.0 0.0 0.0
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

    def test_ts_DFT(self):
        params = {
                'type': 'TS Optimisation',
                'in_file': 'mini_ts.xyz',
                'software': 'ORCA',
                'theory_level': 'DFT',
                'charge': '0',
                'method': 'B3LYP',
                'basis_set': '6-31+G(d,p)',
                }

        calc = gen_calc(params)
        orca = OrcaCalculation(calc)

        REF = """
        !OPTTS B3LYP 6-31+G(d,p)
        *xyz 0 1
        N   1.08764072053386     -0.33994563112543     -0.00972525479568
        H   1.99826836912112      0.05502842705407      0.00651240826058
        H   0.59453997172323     -0.48560162159600      0.83949232123172
        H   0.66998093862168     -0.58930117433261     -0.87511947469677
        *
        %pal
        nprocs 1
        end
        """

        self.assertTrue(self.is_equivalent(REF, orca.input_file))

        #combination tests
