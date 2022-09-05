"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


from .models import *
from .tasks import generate_xyz_structure
from .libxyz import parse_xyz_from_file

TESTS_DIR = os.path.join("/".join(__file__.split("/")[:-1]), "tests/")


def gen_param(params):
    charge = 0
    multiplicity = 1
    solvent = "Vacuum"
    solvation_model = ""
    solvation_radii = ""
    basis_set = ""
    theory_level = ""
    method = ""
    custom_basis_sets = ""
    density_fitting = ""
    specifications = ""

    if "charge" in params.keys():
        charge = int(params["charge"])

    if "multiplicity" in params.keys():
        multiplicity = int(params["multiplicity"])

    if "solvent" in params.keys():
        solvent = params["solvent"]

    if "solvation_model" in params.keys():
        solvation_model = params["solvation_model"]
        if "solvation_radii" in params.keys():
            solvation_radii = params["solvation_radii"]

    if "basis_set" in params.keys():
        basis_set = params["basis_set"]

    if "custom_basis_sets" in params.keys():
        custom_basis_sets = params["custom_basis_sets"]

    if "density_fitting" in params.keys():
        density_fitting = params["density_fitting"]

    if "theory_level" in params.keys():
        theory_level = params["theory_level"]

    if "method" in params.keys():
        method = params["method"]

    if "specifications" in params.keys():
        specifications = params["specifications"]

    software = params["software"]

    p = Parameters.objects.create(
        charge=charge,
        multiplicity=multiplicity,
        solvent=solvent,
        solvation_model=solvation_model,
        solvation_radii=solvation_radii,
        basis_set=basis_set,
        theory_level=theory_level,
        method=method,
        custom_basis_sets=custom_basis_sets,
        density_fitting=density_fitting,
        specifications=specifications,
        software=software,
    )
    return p


def gen_calc(params, profile):
    step = BasicStep.objects.get(name=params["type"])

    p = gen_param(params)

    mol = Molecule.objects.create()
    e = Ensemble.objects.create(parent_molecule=mol)
    s = Structure.objects.create(parent_ensemble=e)

    with open(os.path.join(TESTS_DIR, params["in_file"])) as f:
        lines = f.readlines()

        in_file = "".join(lines)
        ext = params["in_file"].split(".")[-1]
        xyz = generate_xyz_structure(False, in_file, ext)
        s.xyz_structure = xyz
        s.save()

    proj = Project.objects.create()
    dummy = CalculationOrder.objects.create(project=proj, author=profile)
    calc = Calculation.objects.create(
        structure=s, step=step, parameters=p, order=dummy, task_id=1
    )

    if step.creates_ensemble:
        calc.result_ensemble = Ensemble.objects.create(parent_molecule=mol)

    if "constraints" in params:
        calc.constraints = params["constraints"]

    if "aux_file" in params:
        with open(os.path.join(TESTS_DIR, params["aux_file"])) as f:
            aux_xyz = "".join(f.readlines())
        aux_s = Structure.objects.create(
            parent_ensemble=e, number=2, xyz_structure=aux_xyz
        )
        calc.aux_structure = aux_s

    calc.save()

    return calc
