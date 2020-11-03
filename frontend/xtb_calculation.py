import os
import periodictable
from .constants import *


class XtbCalculation:

    def __init__(self, calc):
        self.calc = calc
        self.program = ""
        self.cmd_arguments = ""
        self.option_file = ""
        self.specifications = ""

        self.handle_command()
        self.handle_specifications()
        self.handle_parameters()

        self.create_command()

    def handle_parameters(self):
        if self.calc.parameters.solvent != "Vacuum":
            #self.cmd_arguments += '-g {} '.format(SOLVENT_TABLE[self.calc.parameters.solvent.lower()])
            self.cmd_arguments += '-g {} '.format(self.calc.parameters.solvent.lower())

        if self.calc.parameters.charge != 0:
            self.cmd_arguments += '--chrg {} '.format(self.calc.parameters.charge)

        if self.calc.parameters.multiplicity != 1:
            self.cmd_arguments += '--uhf {} '.format(self.calc.parameters.multiplicity)

    def handle_constraints_scan(self):
        constraints = self.calc.constraints.split(';')[:-1]
        if constraints == "":
            return

        self.option_file += "$constrain\n"
        self.option_file += "force constant=1.0\n"
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
        self.option_file += "$end"

    def handle_constraints_crest(self):
        num_atoms = len(self.calc.structure.xyz_structure.split('\n'))-2
        constraints = self.calc.constraints.split(';')[:-1]
        self.option_file += "$constrain\n"
        self.option_file += "force constant=1.0\n"
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
        mtd_atoms = list(range(1, num_atoms+1))
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
        self.option_file += "$end\n"

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

        ALLOWED = "qwertyuiopasdfghjklzxcvbnm-1234567890. "
        clean_specs = ''.join([i for i in self.specifications + self.calc.parameters.specifications.lower() if i in ALLOWED])

        specs = clean_specs.strip().split('--')

        for spec in specs:
            if spec.strip() == '':
                continue
            ss = spec.strip().split()
            if len(ss) == 1:
                if ss[0] in ['gfn2-xtb', 'gfn1-xtb', 'gfn0-xtb', 'gfn-ff', 'gfn2-xtb//gfn-ff']:
                    if ss[0] == 'gfn2-xtb//gfn-ff' and self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid specifications")
                    method = ss
            elif len(ss) == 2:
                if ss[0] == 'o' or ss[0] == 'opt':
                    if ss[1] not in ['crude', 'sloppy', 'loose', 'lax', 'normal', 'tight', 'vtight', 'extreme']:
                        self.raise_error("Invalid specifications")
                    opt_level = ss[1]
                elif ss[0] == 'rthr':
                    if self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid specifications")
                    rthr = ss[1]
                elif ss[0] == 'ewin':
                    if self.calc.step.name not in ['Conformational Search', 'Constrained Conformational Search']:
                        self.raise_error("Invalid specifications")
                    ewin = ss[1]
                elif ss[0] == 'acc':
                    accuracy = float(ss[1])
                elif ss[0] == 'iterations':
                    iterations = int(ss[1])
            else:
                self.raise_error("Invalid specifications")

        if accuracy != -1:
            self.cmd_arguments += "--acc {:.2f} ".format(accuracy)
        if iterations != -1:
            self.cmd_arguments += "--iterations {} ".format(iterations)
        if method != "gfn2-xtb":
            self.cmd_arguments += "--{}".format(method)
        if opt_level != "normal":
            self.cmd_arguments = self.cmd_arguments.replace('--opt ', '--opt {} '.format(opt_level))

        if self.calc.step.name in ['Conformational Search', 'Constrained Conformational Search']:
            self.cmd_arguments += "--rthr {} --ewin {} ".format(rthr, ewin)


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
            if self.calc.parameters.method == "GFN-FF":
                self.cmd_arguments += "-gff "
            elif self.calc.parameters.method == "GFN2-xTB//GFN-FF":
                self.cmd_arguments += "-gfn2//gfnff "
        elif self.calc.step.name == "Constrained Conformational Search":
            self.cmd_arguments += "-cinp input "
            self.program = "crest"
            self.handle_constraints_crest()
        elif self.calc.step.name == "Constrained Optimisation":
            self.cmd_arguments += "--opt --input input "
            self.program = "xtb"
            self.handle_constraints_scan()
        elif self.calc.step.name == "Frequency Calculation":
            self.cmd_arguments += "--hess "
            self.program = "xtb"
        elif self.calc.step.name == "Single-Point Energy":
            self.program = "xtb"

    def create_command(self):
        self.command = "{} in.xyz {}".format(self.program, self.cmd_arguments)
