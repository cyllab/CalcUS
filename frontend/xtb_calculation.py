import os
import periodictable
from .constants import *


class XtbCalculation:

    def __init__(self, calc):
        self.calc = calc
        self.program = ""
        self.cmd_arguments = ""
        self.option_file = ""

        self.handle_command()
        self.handle_specifications()
        self.handle_parameters()

        self.create_command()

    def handle_parameters(self):
        if self.calc.parameters.solvent != "Vacuum":
            self.cmd_arguments += '-g {} '.format(SOLVENT_TABLE[self.calc.parameters.solvent])

        if self.calc.parameters.charge != 0:
            self.cmd_arguments += '--chrg {} '.format(self.calc.parameters.charge)

        if self.calc.parameters.multiplicity != 1:
            self.cmd_arguments += '--uhf {} '.format(self.calc.parameters.multiplicity)

    def handle_constraints_scan(self):
        constraints = self.calc.constraints.split(';')[:-1]
        if constraints == "":
            return

        self.option_file += "$constrain\n"
        self.option_file += "force constant=1\n"
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
            mtd_atoms.remove(int(a))
        self.option_file += "$metadyn\n"
        self.option_file += "atoms: {}\n".format(','.join([str(i) for i in mtd_atoms]))
        self.option_file += "$end\n"

    def handle_specifications(self):
        return
        for spec in self.calc.parameters.specifications.split(';'):
            if spec.find("=") != -1:
                self.cmd_arguments += "-{} {}".format(*spec.split('='))
            elif spec.find("(") != -1:
                pass#########
            else:
                self.cmd_arguments += "-{}".format(spec)
    def handle_command(self):
        if self.calc.step.name == "Geometrical Optimisation":
            self.cmd_arguments += "-o vtight -a 0.05 "
            self.program = "xtb"
        elif self.calc.step.name == "Conformational Search":
            self.cmd_arguments = "-rthr 0.6 -ewin 6"
            self.program = "crest"
            if self.calc.parameters.method == "GFN-FF":
                self.cmd_arguments += "-gff "
            elif self.calc.parameters.method == "GFN2-xTB//GFN-FF":
                self.cmd_arguments += "-gfn2//gfnff "
        elif self.calc.step.name == "Constrained Conformational Search":
            self.cmd_arguments += "--cinp input "
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
