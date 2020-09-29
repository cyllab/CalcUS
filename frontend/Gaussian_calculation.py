import os
import periodictable
from .constants import *
from .calculation_helper import *
from .libxyz import *
import basis_set_exchange

L_PAL = os.environ['OMP_NUM_THREADS'][0]
L_STACKSIZE = os.environ['OMP_STACKSIZE']
if L_STACKSIZE.find("G") != -1:
    L_STACKSIZE = int(L_STACKSIZE.replace('G', ''))*1024
elif L_STACKSIZE.find("MB") != -1:
    L_STACKSIZE = int(L_STACKSIZE.replace('MB', ''))

L_MEM = int(L_PAL)*L_STACKSIZE

class GaussianCalculation:

    SMD18_APPENDIX = """modifysph

    Br 2.60
    I 2.74
    """

    TEMPLATE = """%chk=in.chk
    %nproc={}
    %mem={}MB
    #p {}{}

    CalcUS

    {} {}
    {}
    {}
    """

    KEYWORDS = {
                'Geometrical Optimisation': 'opt',
                'Constrained Optimisation': 'opt',
                'TS Optimisation': 'opt',
                'Frequency Calculation': 'freq',
                'NMR Prediction': 'nmr',
                'Single-Point Energy': 'sp',
            }

    #Number of processors
    #Amount of memory
    #Command line
    #Additional commands
    #Charge
    #Multiplicity
    #XYZ structure
    #Appendix

    def __init__(self, calc):
        self.calc = calc
        self.has_scan = False
        self.pal = 0
        self.appendix = []
        self.command_line = ""
        self.additional_commands = ""
        self.command_specifications = []
        self.xyz_structure = ""
        self.input_file = ""

        self.handle_specifications()
        self.handle_command()
        self.handle_xyz()

        self.handle_solvation()

        self.create_input_file()

    def handle_specifications(self):
        specs = {}
        def add_spec(key, option, val):
            if val == "":
                option_val = option
            else:
                option_val = "{}={}".format(option, val)
            if key in specs.keys():
                specs[key].append(option_val)
            else:
                specs[key] = [option_val]
        for spec in self.calc.parameters.specifications.lower().split(';'):
            if spec.strip() == '':
                continue
            key, option = spec.split('(')
            option = option.replace(')', '')
            val = ""
            if option.find('=') != -1:
                option, val = option.split('=')
            if option not in SPECIFICATIONS[self.calc.parameters.software][key].keys():
                raise Exception("Unknown specification")
            if key in self.KEYWORDS.values():
                if key != self.KEYWORDS[self.calc.step.name]:
                    raise Exception("Invalid specification for the requested step")
                if val == '':
                    self.command_specifications.append(option)
                else:
                    self.command_specifications.append("{}={}".format(option, val))
            else:
                add_spec(key, option, val)

        for spec in specs.keys():
            specs_str = ','.join(specs[spec])
            self.additional_commands += '{}({}) '.format(spec, specs_str)

    def handle_command(self):
        cmd = ""
        base_specs = []
        if self.calc.step.name == 'NMR Prediction':
            cmd = "nmr"
        elif self.calc.step.name == 'Geometrical Optimisation':
            cmd = "opt"
        elif self.calc.step.name == 'TS Optimisation':
            cmd = "opt"
            base_specs = ['ts', 'NoEigenTest', 'CalcFC']
        elif self.calc.step.name == 'Frequency Calculation':
            cmd = "freq"
        elif self.calc.step.name == 'Constrained Optimisation':
            cmd = "opt"
            base_specs = ['modredundant']
            lines = [i + '\n' for i in clean_xyz(self.calc.structure.xyz_structure).split('\n')[2:]]

            xyz = []
            for line in lines:
                if line.strip() != '':
                    a, x, y, z = line.split()
                    xyz.append([a, np.array([float(x), float(y), float(z)])])
            gaussian_constraints = ""
            has_scan = False
            scans = []
            freeze = []

            if self.calc.constraints.strip() == '':
                raise Exception("No constraint in constrained optimisation mode")

            scmd = self.calc.constraints.split(';')

            for c in scmd:
                if c.strip() == '':
                    continue
                _c, ids = c.split('-')
                _c= _c.split('_')
                ids = ids.split('_')
                ids = [int(i) if i.strip() != '' else -1 for i in ids]
                type = len(ids)

                if _c[0] == "Scan":
                    has_scan = True
                    end = float(_c[2])
                    num_steps = int(float(_c[3]))

                    if type == 2:
                        start = get_distance(xyz, *ids)
                        step_size = "{:.2f}".format((end-start)/num_steps)
                        gaussian_constraints += "B {} {} S {} {}\n".format(*ids, num_steps, step_size)
                    if type == 3:
                        start = get_angle(xyz, *ids)
                        step_size = "{:.2f}".format((end-start)/num_steps)
                        gaussian_constraints += "A {} {} {} S {} {}\n".format(*ids, num_steps, step_size)
                    if type == 4:
                        start = get_dihedral(xyz, *ids)
                        step_size = "{:.2f}".format((end-start)/num_steps)
                        gaussian_constraints += "D {} {} {} {} S {} {}\n".format(*ids, num_steps, step_size)
                else:
                    if type == 2:
                        gaussian_constraints += "B {} {} F\n".format(*ids)
                    if type == 3:
                        gaussian_constraints += "A {} {} {} F\n".format(*ids)
                    if type == 4:
                        gaussian_constraints += "D {} {} {} {} F\n".format(*ids)

            self.has_scan = has_scan
            self.appendix.append(gaussian_constraints)
        elif self.calc.step.name == 'Single-Point Energy':
            cmd = "sp"

        full_specs = base_specs + self.command_specifications
        if len(full_specs) == 0:
            cmd_specifications_str = ""
        else:
            cmd_specifications_str = "({})".format(', '.join(full_specs))

        self.command_line += "{}{} ".format(cmd, cmd_specifications_str)
        method = get_method(self.calc.parameters.method, "Gaussian")
        basis_set = get_basis_set(self.calc.parameters.basis_set, "Gaussian")
        custom_basis_set = self.calc.parameters.custom_basis_sets

        if method == "":
            if self.calc.parameters.theory_level == "HF":
                method = "HF"
            else:
                raise Exception("No method")

        if basis_set != "":
            if custom_basis_set == "":
                if self.calc.parameters.density_fitting != '':
                    self.command_line += "{}/{}/{} ".format(method, basis_set, self.calc.parameters.density_fitting)
                else:
                    self.command_line += "{}/{} ".format(method, basis_set)
            else:
                gen_keyword, to_append = self.parse_custom_basis_set()
                self.appendix.append(to_append)
                self.command_line += "{}/{} ".format(method, gen_keyword)
        else:
            self.command_line += "{} ".format(method)

        self.additional_commands += self.calc.parameters.additional_command.strip()

    def parse_custom_basis_set(self):
        custom_basis_set = self.calc.parameters.custom_basis_sets
        entries = [i.strip() for i in custom_basis_set.split(';') if i.strip() != ""]
        to_append_gen = []
        to_append_ecp = []

        custom_atoms_requested = []
        for entry in entries:
            sentry = entry.split('=')

            if len(sentry) != 2:
                raise Exception("Invalid custom basis set string")

            el, bs_keyword = sentry
            custom_atoms_requested.append(el)


        unique_atoms = []
        normal_atoms = []
        for line in self.calc.structure.xyz_structure.split('\n')[2:]:
            if line.strip() == "":
                continue
            a, *_ = line.split()
            if a not in unique_atoms:
                unique_atoms.append(a)
                if a not in normal_atoms and a not in custom_atoms_requested:
                    normal_atoms.append(a)

        custom_atoms = []
        ecp = False
        for entry in entries:
            sentry = entry.split('=')

            el, bs_keyword = sentry

            if el not in unique_atoms:
                continue

            custom_atoms.append(el)
            try:
                el_num = ATOMIC_NUMBER[el]
            except KeyError:
                raise Exception("Invalid atom in custom basis set string")

            bs = basis_set_exchange.get_basis(bs_keyword, fmt='gaussian94', elements=[el_num], header=False)
            if bs.find('-ECP') != -1:
                ecp = True
                sbs = bs.split('\n')
                ecp_ind = -1
                for ind, line in enumerate(sbs):
                    if sbs[ind].find("-ECP") != -1:
                        ecp_ind = ind
                        break
                bs_gen = '\n'.join(sbs[:ecp_ind-2]) + '\n'
                bs_ecp = '\n'.join(sbs[ecp_ind-2:]) + '\n'
                to_append_gen.append(bs_gen)
                to_append_ecp.append(bs_ecp)
            else:
                to_append_gen.append(bs)

        if len(custom_atoms) > 0:
            if ecp:
                gen_keyword = "GenECP"
            else:
                gen_keyword = "Gen"


            custom_bs = ""

            if len(normal_atoms) > 0:
                custom_bs += ' '.join(normal_atoms) + ' 0\n'
                custom_bs += self.calc.parameters.basis_set + '\n'
                custom_bs += '****\n'

            custom_bs += ''.join(to_append_gen)
            custom_bs += ''.join(to_append_ecp)

            return gen_keyword, custom_bs
        else:
            return self.calc.parameters.basis_set, ''

    def handle_xyz(self):
        lines = [i + '\n' for i in clean_xyz(self.calc.structure.xyz_structure).split('\n')[2:] if i != '' ]
        self.xyz_structure = ''.join(lines)

    def handle_solvation(self):
        if self.calc.parameters.solvent != "Vacuum":
            if self.calc.parameters.solvation_model == "SMD":
                if self.calc.parameters.solvation_radii == "Default":
                    self.command_line += "SCRF(SMD, Solvent={}) ".format(self.calc.parameters.solvent)
                else:
                    self.command_line += "SCRF(SMD, Solvent={}, Read) ".format(self.calc.parameters.solvent)
                    self.appendix.append(self.SMD18_APPENDIX)
            elif self.calc.parameters.solvation_model == "PCM":
                if self.calc.parameters.solvation_radii in ["UFF", ""]:
                    self.command_line += "SCRF(PCM, Solvent={}) ".format(self.calc.parameters.solvent)
                else:
                    self.command_line += "SCRF(PCM, Solvent={}, Read) ".format(self.calc.parameters.solvent)
                    self.appendix.append("Radii={}\n".format(self.calc.parameters.solvation_radii))
            elif self.calc.parameters.solvation_model == "CPCM":
                if self.calc.parameters.solvation_radii in ["UFF", ""]:
                    self.command_line += "SCRF(CPCM, Solvent={}) ".format(self.calc.parameters.solvent)
                else:
                    self.command_line += "SCRF(CPCM, Solvent={}, Read) ".format(self.calc.parameters.solvent)
                    self.appendix.append("Radii={}\n".format(self.calc.parameters.solvation_radii))
            else:
                raise Exception("Invalid solvation method for Gaussian")

    def create_input_file(self):
        if self.calc.local:
            PAL = L_PAL
            MEM = L_MEM
        else:
            r = self.calc.order.resource
            PAL = r.pal
            MEM = r.memory

        raw = self.TEMPLATE.format(PAL, MEM, self.command_line, self.additional_commands, self.calc.parameters.charge, self.calc.parameters.multiplicity, self.xyz_structure, '\n'.join(self.appendix))
        self.input_file = '\n'.join([i.strip() for i in raw.split('\n')]).replace('\n\n\n', '\n\n')

