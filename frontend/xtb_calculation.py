import os
import periodictable
from .constants import *
from .calculation_helper import *

class XtbCalculation:

    def __init__(self, calc):
        self.calc = calc
        self.program = ""
        self.cmd_arguments = ""
        self.option_file = ""
        self.specifications = ""
        self.force_constant = 1.0

        self.handle_command()
        self.handle_specifications()

        if self.calc.step.name == "Constrained Conformational Search":
            self.handle_constraints_crest()
        elif self.calc.step.name == "Constrained Optimisation":
            self.handle_constraints_scan()

        self.handle_parameters()

        self.create_command()

    def handle_parameters(self):
        if self.calc.parameters.solvent.lower() != "vacuum":
            try:
                solvent_keyword = get_solvent(self.calc.parameters.solvent, self.calc.parameters.software)
            except KeyError:
                self.raise_error("Invalid solvent")

            if self.calc.parameters.solvation_model == "GBSA":
                self.cmd_arguments += '-g {} '.format(solvent_keyword)
            elif self.calc.parameters.solvation_model == "ALPB":
                self.cmd_arguments += '--alpb {} '.format(solvent_keyword)
            else:
                self.raise_error("Invalid solvation method for xtb: {}".format(self.calc.parameters.solvation_model))


        if self.calc.parameters.charge != 0:
            self.cmd_arguments += '--chrg {} '.format(self.calc.parameters.charge)

        if self.calc.parameters.multiplicity != 1:
            self.cmd_arguments += '--uhf {} '.format(self.calc.parameters.multiplicity)

    def handle_constraints_scan(self):
        constraints = self.calc.constraints.split(';')[:-1]
        if constraints == "":
            return

        self.option_file += "$constrain\n"
        self.option_file += "force constant={}\n".format(self.force_constant)
        self.has_scan = False
        for cmd in constraints:
            _cmd, ids = cmd.split('-')
            _cmd = _cmd.split('_')
            ids = ids.split('_')
            type = len(ids)
            if type == 2:
                self.option_file += "distance: {}, {}, auto\n".format(*ids)
            if type == 3:
                self.option_file += "angle: {}, {}, {}, auto\n".format(*ids)
            if type == 4:
                self.option_file += "dihedral: {}, {}, {}, {}, auto\n".format(*ids)
            if _cmd[0] == "Scan":
                self.has_scan = True
        if self.has_scan:
            self.option_file += "$scan\n"
            for counter, cmd in enumerate(constraints):
                _cmd, ids = cmd.split('-')
                _cmd = _cmd.split('_')
                if _cmd[0] == "Scan":
                    self.option_file += "{}: {}, {}, {}\n".format(counter+1, *_cmd[1:])

    def handle_constraints_crest(self):
        num_atoms = len(self.calc.structure.xyz_structure.split('\n'))-2
        constraints = self.calc.constraints.split(';')[:-1]
        self.option_file += "$constrain\n"
        self.option_file += "force constant={}\n".format(self.force_constant)
        self.option_file += "reference=in.xyz\n"
        constr_atoms = []
        for cmd in constraints:
            _cmd, ids = cmd.split('-')
            _cmd = _cmd.split('_')
            ids = ids.split('_')
            type = len(ids)
            if type == 2:
                self.option_file += "distance: {}, {}, auto\n".format(*ids)
            elif type == 3:
                self.option_file += "angle: {}, {}, {}, auto\n".format(*ids)
            elif type == 4:
                self.option_file += "dihedral: {}, {}, {}, {}, auto\n".format(*ids)
            constr_atoms += ids
        self.option_file += "atoms: {}\n".format(','.join([str(i) for i in constr_atoms]))

        mtd_atoms = list(range(1, num_atoms))
        for a in constr_atoms:
            if int(a) in mtd_atoms:
                mtd_atoms.remove(int(a))

        mtd_atoms_str = ""
        def add_to_str(curr):
            if len(curr) == 0:
                return ""
            elif len(curr) == 1:
                return ",{}".format(curr[0])
            else:
                return ",{}-{}".format(curr[0], curr[-1])

        curr_atoms = []

        for a in mtd_atoms:
            if len(curr_atoms) == 0:
                curr_atoms.append(a)
            else:
                if a == curr_atoms[-1] + 1:
                    curr_atoms.append(a)
                else:
                    mtd_atoms_str += add_to_str(curr_atoms)
                    curr_atoms = [a]

        mtd_atoms_str += add_to_str(curr_atoms)

        self.option_file += "$metadyn\n"
        self.option_file += "atoms: {}\n".format(mtd_atoms_str[1:])#remove the first comma

    def handle_specifications(self):
        SPECIFICATIONS = {
                    'general': {
                        'acc': 1,
                        'iterations': 1,
                        'gfn2-xtb': 0,
                        'gfn1-xtb': 0,
                        'gfn0-xtb': 0,
                        'gfn-ff': 0,
                    },
                    'Geometrical Optimisation': {
                        'opt(crude)': 0,
                        'opt(sloppy)': 0,
                        'opt(loose)': 0,
                        'opt(lax)': 0,
                        'opt(normal)': 0,
                        'opt(tight)': 0,
                        'opt(vtight)': 0,
                        'opt(extreme)': 0,
                    },
                    'Conformational Search': {
                        'gfn2-xtb//gfn-ff': 0,
                        'rthr': 1,
                        'ewin': 1,
                    },
        }

        accuracy = -1
        iterations = -1
        method = "gfn2-xtb"
        opt_level = "tight"
        rthr = 0.6
        ewin = 6
        cmd_arguments = ""

        ALLOWED = "qwertyuiopasdfghjklzxcvbnm-1234567890./= "
        clean_specs = ''.join([i for i in self.specifications + self.calc.parameters.specifications.lower() if i in ALLOWED])
        clean_specs = clean_specs.replace('=', ' ').replace('  ', ' ')

        specs = clean_specs.strip().split('--')

        for spec in specs:
            if spec.strip() == '':
                continue
            ss = spec.strip().split()
            if len(ss) == 1:
                if ss[0] in ['gfn2', 'gfn1', 'gfn0', 'gfnff', 'gfn2//gfnff']:
                    if ss[0] == 'gfn2//gfnff' and self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid method for calculation type: {}".format(ss[0]))
                    if ss[0] in ['gfn2', 'gfn1', 'gfn0']:
                        method = "{} {}".format(ss[0][:-1], ss[0][-1])
                    else:
                        method = ss[0]
                else:
                    self.raise_error("Invalid specification")
            elif len(ss) == 2:
                if ss[0] == 'o' or ss[0] == 'opt':
                    if ss[1] not in ['crude', 'sloppy', 'loose', 'lax', 'normal', 'tight', 'vtight', 'extreme']:
                        self.raise_error("Invalid optimization specification")
                    opt_level = ss[1]
                elif ss[0] == 'rthr':
                    if self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid specification for calculation type: rthr")
                    rthr = ss[1]
                elif ss[0] == 'ewin':
                    if self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid specification for calculation type: ewin")
                    ewin = ss[1]
                elif ss[0] == 'acc':
                    accuracy = float(ss[1])
                elif ss[0] == 'iterations':
                    try:
                        iterations = int(ss[1])
                    except ValueError:
                        self.raise_error("Invalid number of iterations: must be an integer")
                elif ss[0] == 'forceconstant':
                    try:
                        self.force_constant = float(ss[1])
                    except ValueError:
                        self.raise_error("Invalid force constant: must be a floating point value")
                elif ss[0] == 'gfn':
                    if ss[1] not in ['0', '1', '2']:
                        self.raise_error("Invalid GFN version")
                    method = "{} {}".format(ss[0], ss[1])
                else:
                    self.raise_error("Unknown specification: {}".format(ss[0]))
            else:
                self.raise_error("Invalid specification: {}".format(ss))

        if accuracy != -1:
            self.cmd_arguments += "--acc {:.2f} ".format(accuracy)
        if iterations != -1:
            self.cmd_arguments += "--iterations {} ".format(iterations)
        if method != "gfn2-xtb" and method != "gfn 2":
            self.cmd_arguments += "--{} ".format(method)
        if opt_level != "normal":
            self.cmd_arguments = self.cmd_arguments.replace('--opt ', '--opt {} '.format(opt_level))

        if self.calc.step.name in ['Conformational Search', 'Constrained Conformational Search']:
            self.cmd_arguments += "--rthr {} --ewin {} ".format(rthr, ewin)

            self.cmd_arguments = self.cmd_arguments.replace('--', '-')#Crest 2.10.2 does not read arguments with double dashes


    def raise_error(self, msg):
        self.calc.status = 3
        self.calc.error_message = msg
        self.calc.save()
        raise Exception(msg)

    def handle_command(self):
        if self.calc.step.name == "Geometrical Optimisation":
            self.specifications = "--opt tight "
            self.cmd_arguments += "--opt "
            self.program = "xtb"
        elif self.calc.step.name == "Conformational Search":
            self.specifications = "--rthr 0.6 --ewin 6 "
            self.program = "crest"
        elif self.calc.step.name == "Constrained Conformational Search":
            self.cmd_arguments += "-cinp input "
            self.program = "crest"
        elif self.calc.step.name == "Constrained Optimisation":
            self.cmd_arguments += "--opt --input input "
            self.program = "xtb"
        elif self.calc.step.name == "Frequency Calculation":
            self.cmd_arguments += "--hess "
            self.program = "xtb"
        elif self.calc.step.name == "Single-Point Energy":
            self.program = "xtb"


    def create_command(self):
        self.command = "{} in.xyz {}".format(self.program, self.cmd_arguments)
