import os
import periodictable
from .constants import *
from .calculation_helper import *

ATOMIC_NUMBER = {}
ATOMIC_SYMBOL = {}
LOWERCASE_ATOMIC_SYMBOLS = {}

L_PAL = os.environ['OMP_NUM_THREADS'][0]
L_STACKSIZE = os.environ['OMP_STACKSIZE']
if L_STACKSIZE.find("G") != -1:
    L_STACKSIZE = int(L_STACKSIZE.replace('G', ''))*1024
elif L_STACKSIZE.find("MB") != -1:
    L_STACKSIZE = int(L_STACKSIZE.replace('MB', ''))

L_MEM = int(L_PAL)*L_STACKSIZE

for el in periodictable.elements:
    ATOMIC_NUMBER[el.symbol] = el.number
    ATOMIC_SYMBOL[el.number] = el.symbol
    LOWERCASE_ATOMIC_SYMBOLS[el.symbol.lower()] = el.symbol


class OrcaCalculation:

    calc = None

    has_scan = False
    pal = 0
    blocks = []

    TEMPLATE = """!{}
    *xyz {} {}
    {}*
    {}"""
    #Command Line
    #Charge
    #Multiplicity
    #XYZ structure
    #Options blocks

    command_line = ""
    xyz_structure = ""
    block_lines = ""

    input_file = ""

    def __init__(self, calc):
        self.calc = calc
        self.has_scan = False
        self.pal = 0
        self.blocks = []
        self.command_line = ""
        self.xyz_structure = ""
        self.block_lines = ""
        self.input_file = ""



        self.handle_command()
        self.handle_xyz()

        self.handle_pal()
        self.handle_solvation()

        self.create_input_file()

    def handle_command(self):
        if self.calc.step.name == 'NMR Prediction':
            self.command_line = "NMR "
        elif self.calc.step.name == 'Geometrical Optimisation':
            self.command_line = "OPT "
        elif self.calc.step.name == 'TS Optimisation':
            self.command_line = "OPTTS "
        elif self.calc.step.name == 'MO Calculation':
            self.command_line = "SP "
            struct = clean_xyz(self.calc.structure.xyz_structure)

            electrons = 0
            for line in struct.split('\n')[2:]:
                if line.strip() == "":
                    continue
                el = line.split()[0]
                electrons += ATOMIC_NUMBER[el]

            electrons -= self.calc.parameters.charge

            if self.calc.parameters.multiplicity != 1:
                print("Unimplemented multiplicity")
                return -1

            n_HOMO = int(electrons/2)-1
            n_LUMO = int(electrons/2)
            n_LUMO1 = int(electrons/2)+1
            n_LUMO2 = int(electrons/2)+2

            mo_block = """%plots
                        dim1 45
                        dim2 45
                        dim3 45
                        min1 0
                        max1 0
                        min2 0
                        max2 0
                        min3 0
                        max3 0
                        Format Gaussian_Cube
                        MO("in-HOMO.cube",{},0);
                        MO("in-LUMO.cube",{},0);
                        MO("in-LUMOA.cube",{},0);
                        MO("in-LUMOB.cube",{},0);
                        end
                        """.format(n_HOMO, n_LUMO, n_LUMO1, n_LUMO2)
            self.blocks.append(mo_block)
        elif self.calc.step.name == 'Frequency Calculation':
            self.command_line = "FREQ "
        elif self.calc.step.name == 'Constrained Optimisation':
            self.command_line = "OPT "

            orca_constraints = ""
            has_scan = False
            scans = []
            freeze = []
            for cmd in self.calc.constraints.split(';'):
                if cmd.strip() == '':
                    continue
                _cmd, ids = cmd.split('-')
                _cmd = _cmd.split('_')
                ids = ids.split('_')
                ids = [int(i)-1 for i in ids]
                type = len(ids)
                if _cmd[0] == "Scan":
                    has_scan = True
                else:
                    if type == 2:
                        freeze.append("{{ B {} {} C }}\n".format(*ids))
                    if type == 3:
                        freeze.append("{{ A {} {} {} C }}\n".format(*ids))
                    if type == 4:
                        freeze.append("{{ D {} {} {} {} C }}\n".format(*ids))
            if has_scan:
                for cmd in self.calc.constraints.split(';'):
                    if cmd.strip() == '':
                        continue
                    _cmd, ids = cmd.split('-')
                    ids = ids.split('_')
                    _cmd = _cmd.split('_')
                    ids_str = "{}".format(int(ids[0])-1)
                    for i in ids[1:]:
                        ids_str += " {}".format(int(i)-1)
                    if len(ids) == 2:
                        type = "B"
                    if len(ids) == 3:
                        type = "A"
                    if len(ids) == 4:
                        type = "D"
                    if _cmd[0] == "Scan":
                        scans.append("{} {} = {}, {}, {}\n".format(type, ids_str, *_cmd[1:]))

            self.has_scan = has_scan

            if len(scans) > 0:
                scan_block = """%geom Scan
                {}
                end
                end"""
                self.blocks.append(scan_block.format(''.join(scans).strip()))

            if len(freeze) > 0:
                freeze_block = """%geom Constraints
                {}
                end
                end"""
                self.blocks.append(freeze_block.format(''.join(freeze).strip()))
        elif self.calc.step.name == 'Single-Point Energy':
            self.command_line = "SP "

        method = get_method(self.calc.parameters.method, "ORCA")
        basis_set = get_basis_set(self.calc.parameters.basis_set, "ORCA")

        if method == "":
            if self.calc.parameters.theory_level == "HF":
                method = "HF"
            elif self.calc.parameters.theory_level == "RI-MP2":
                method = "RI-MP2"
            else:
                raise Exception("No method")

        self.command_line += "{} {} ".format(method, basis_set)

        if self.calc.parameters.misc.strip() != "":
            self.command_line += "{} ".format(self.calc.parameters.misc.strip())

    def handle_xyz(self):
        lines = [i + '\n' for i in clean_xyz(self.calc.structure.xyz_structure).split('\n')[2:] if i != '' ]
        self.xyz_structure = ''.join(lines)

    def handle_pal(self):
        if self.calc.parameters.theory_level == "Semi-empirical":
            self.pal = 1
        else:
            if self.calc.local:
                self.pal = L_PAL
            else:
                self.pal = self.calc.order.resource.pal

        pal_block = """%pal
        nprocs {}
        end""".format(self.pal)

        self.blocks.append(pal_block)

    def handle_solvation(self):
        if self.calc.parameters.solvent != "Vacuum":
            if self.calc.parameters.solvation_model == "SMD":
                smd_block = '''%cpcm
                smd true
                SMDsolvent "{}"
                end'''.format(self.calc.parameters.solvent)
                self.blocks.append(smd_block)
            elif self.calc.parameters.solvation_model == "SMD18":
                smd_block = '''%cpcm
                smd true
                SMDsolvent "{}"
                radius[I] 2.74
                radius[Br] 2.60
                end'''.format(self.calc.parameters.solvent)
                self.blocks.append(smd_block)

            elif self.calc.parameters.solvation_model == "CPCM":
                self.command_line += "CPCM({}) ".format(self.calc.parameters.solvent)
            else:
                raise Exception("Invalid solvation method for ORCA")

    def create_input_file(self):
        self.block_lines = '\n'.join(self.blocks)
        raw = self.TEMPLATE.format(self.command_line, self.calc.parameters.charge, self.calc.parameters.multiplicity, self.xyz_structure, self.block_lines)
        self.input_file = '\n'.join([i.strip() for i in raw.split('\n')])

