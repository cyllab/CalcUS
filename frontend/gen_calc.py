from .models import *

TESTS_DIR = os.path.join('/'.join(__file__.split('/')[:-1]), "tests/")

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

    if 'charge' in params.keys():
        charge = int(params['charge'])

    if 'multiplicity' in params.keys():
        multiplicity = int(params['multiplicity'])

    if 'solvent' in params.keys():
        solvent = params['solvent']

    if 'solvation_model' in params.keys():
        solvation_model = params['solvation_model']
        if 'solvation_radii' in params.keys():
            solvation_radii = params['solvation_radii']
        else:
            if solvation_model == "SMD":
                solvation_radii = "Default"
            if solvation_model in ["PCM", "CPCM"]:
                solvation_radii = "UFF"

    if 'basis_set' in params.keys():
        basis_set = params['basis_set']

    if 'custom_basis_sets' in params.keys():
        custom_basis_sets = params['custom_basis_sets']

    if 'density_fitting' in params.keys():
        density_fitting = params['density_fitting']

    if 'theory_level' in params.keys():
        theory_level = params['theory_level']

    if 'method' in params.keys():
        method = params['method']

    if 'specifications' in params.keys():
        specifications = params['specifications']

    software = params['software']

    p = Parameters.objects.create(charge=charge, multiplicity=multiplicity, solvent=solvent, solvation_model=solvation_model, solvation_radii=solvation_radii, basis_set=basis_set, theory_level=theory_level, method=method, custom_basis_sets=custom_basis_sets, density_fitting=density_fitting, specifications=specifications, software=software)
    return p

def gen_calc(params, profile):
    step = BasicStep.objects.get(name=params['type'])

    p = gen_param(params)

    mol = Molecule.objects.create()
    e = Ensemble.objects.create(parent_molecule=mol)
    s = Structure.objects.create(parent_ensemble=e)

    with open(os.path.join(TESTS_DIR, params['in_file'])) as f:
        lines = f.readlines()

        in_file = ''.join(lines)
        ext = params['in_file'].split('.')[-1]
        if ext == 'mol':
            s.mol_structure = in_file
            generate_xyz_structure(False, s)
        elif ext == 'xyz':
            s.xyz_structure = in_file
        elif ext == 'sdf':
            s.sdf_structure = in_file
            generate_xyz_structure(False, s)
        elif ext == 'mol2':
            s.mol2_structure = in_file
            generate_xyz_structure(False, s)
        elif ext == 'log':
            s.xyz_structure = get_Gaussian_xyz(in_file)
        else:
            raise Exception("Unknown file format")
        xyz_structure = ''.join(lines)


    proj = Project.objects.create()
    dummy = CalculationOrder.objects.create(project=proj, author=profile)
    calc = Calculation.objects.create(structure=s, step=step, parameters=p, order=dummy)

    if 'constraints' in params.keys():
        calc.constraints = params['constraints']

    return calc

