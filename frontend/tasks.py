from __future__ import absolute_import, unicode_literals

from labsandbox.celery import app
import os
import decimal
from django.utils import timezone
import numpy as np

from time import time
from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure

import subprocess
import shlex
from shutil import copyfile
import sys
import glob


is_test = "unittest" in sys.modules

if is_test:
    LAB_SCR_HOME = os.environ['LAB_TEST_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_TEST_RESULTS_HOME']
else:
    LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']

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


def system(command, log_file=""):
    if log_file != "":
        with open(log_file, 'w') as out:
            a = subprocess.run(shlex.split(command), stdout=out).returncode
        return a
    else:
        return subprocess.run(shlex.split(command)).returncode

def handle_input_file(drawing):
    if drawing:
        return system("babel -imol initial.mol -oxyz initial.xyz -h --gen3D")
    else:
        if os.path.isfile("initial.mol"):
            return system("babel -imol initial.mol -oxyz initial.xyz")
        elif os.path.isfile("initial.xyz"):
            return 0
        elif os.path.isfile("initial.mol2"):
            return system("babel -imol2 initial.mol2 -oxyz initial.xyz")
        elif os.path.isfile("initial.sdf"):
            return system("babel -isdf initial.sdf -oxyz initial.xyz")


def xtb_opt(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("xtb {} --chrg {} {} --opt".format(in_file, charge, solvent_add), 'xtb_opt.out')

def crest(in_file, charge, solvent, mode):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    if mode == "Final":
        return system("crest {} --chrg {} {} -rthr 0.4 -ewin 4".format(in_file, charge, solvent_add), 'crest.out')
    elif mode == "NMR":
        return system("crest {} --chrg {} {} -nmr".format(in_file, charge, solvent_add), 'crest.out')
    else:
        print("Invalid crest mode selected!")
        return -1


def run_steps(steps, calc_obj, drawing, id):
    a = handle_input_file(drawing)

    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, str(id))))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, str(id))))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    calc_obj.num_steps = len(steps)+1
    for ind, step in enumerate(steps):
        f, args, desc, error = step
        calc_obj.current_status = desc
        calc_obj.current_step = ind+1
        calc_obj.save()
        a = f(*args)
        if a != 0:
            calc_obj.status = 3
            calc_obj.error_message = error
            calc_obj.save()
            return a

    calc_obj.current_step = calc_obj.num_steps
    calc_obj.save()

    return 0

def save_to_results(f, calc_obj, multiple=False):
    for _f in f:
        name = _f.split('.')[0]
        if multiple:
            a = system("babel -ixyz {} -omol {}/conf.mol -m".format(_f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))))
        else:
            a = system("babel -ixyz {} -omol {}/{}.mol".format(_f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id)), name))
        if a != 0:
            calc_obj.status = 3
            calc_obj.error_message = "Failed to convert the optimized geometry"
            calc_obj.save()
            return a
    return 0

@app.task
def geom_opt(id, drawing, charge, solvent, calc_obj=None):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],

    ]
    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results(["xtbopt.xyz"], calc_obj)
    if a != 0:
        return

    with open("xtb_opt.out") as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)
    r.save()

    calc_obj.structure_set.add(r)

    return 0

@app.task
def conf_search(id, drawing, charge, solvent, calc_obj=None):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [crest, ["xtbopt.xyz", charge, solvent, "Final"], "Generating conformer ensemble", "Failed to generate the conformers"],

    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results(["crest_conformers.xyz"], calc_obj, multiple=True)
    a = save_to_results(["crest_conformers.xyz"], calc_obj)

    if a != 0:
        return

    with open("crest.out") as f:
        lines = f.readlines()
        ind = len(lines) - 1

        while lines[ind].find("total number unique points considered further") == -1:
            ind -= 1

        weighted_energy = 0.0

        ind += 1
        while lines[ind].find("T /K") == -1:
            sline = lines[ind].strip().split()
            if len(sline) == 8:
                rel_energy = float(sline[1])*4.184
                energy = float(sline[2])
                weight = float(sline[4])
                number = int(sline[5])
                degeneracy = int(sline[6])
                weighted_energy += energy*weight
                r = Structure.objects.create(number=number, energy=energy, rel_energy=rel_energy, boltzmann_weight=weight, homo_lumo_gap=0.0, degeneracy=degeneracy)
                r.save()
                calc_obj.structure_set.add(r)
            ind += 1

    calc_obj.weighted_energy = weighted_energy
    calc_obj.save()

    return 0

FACTOR = 1
SIGMA = 0.2
SIGMA_L = 6199.21
E = 4.4803204E-10
NA = 6.02214199E23
C = 299792458
HC = 4.135668E15*C
ME = 9.10938E-31

def plot_peaks(_x, PP):
    val = 0
    for w, T in PP:
        val += np.sqrt(np.pi)*E**2*NA/(1000*np.log(10)*C**2*ME)*T/SIGMA*np.exp(-((HC/_x-HC/w)/(HC/SIGMA_L))**2)
    return val


def xtb4stda(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add_xtb = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add_xtb = ''

    return system("xtb4stda {} -chrg {} {}".format(in_file, charge, solvent_add_xtb), 'xtb4stda.out')

def stda(charge, solvent):
    if solvent != "Vacuum":
        solvent_add_xtb = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add_xtb = ''

    return system("stda -xtb -e 12", 'stda.out')

@app.task
def uvvis_simple(id, drawing, charge, solvent, calc_obj=None):
    ww = []
    TT = []
    PP = []

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [xtb4stda, ["xtbopt.xyz", charge, solvent], "Performing ground-state calculation", "Failed to calculate ground-state electronic density"],
        [stda, [charge, solvent], "Performing time-dependant calculation", "Failed to calculate perform time-dependant calculation"],
    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results(["xtbopt.xyz"], calc_obj, multiple=True)
    if a != 0:
        return

    f_x = np.arange(120.0, 1200.0, 1.0)

    with open("tda.dat") as f:
        lines = f.readlines()
    ind = 0
    while lines[ind].find("DATXY") == -1:
        ind += 1
    ind += 1
    for line in lines[ind:]:
        n, ev, I, _x, _y, _z = line.split()
        ev = float(ev)
        I = float(I)
        ww.append(1240/ev)
        TT.append(I)
    PP = sorted(zip(ww, TT), key=lambda i: i[1], reverse=True)
    yy = plot_peaks(f_x, PP)
    yy = np.array(yy)/max(yy)


    with open("{}/uvvis.csv".format(os.path.join(LAB_RESULTS_HOME, str(id))), 'w') as out:
        out.write("Wavelength (nm), Absorbance\n")
        for ind, x in enumerate(f_x):
            out.write("{},{:.8f}\n".format(x, yy[ind]))

    with open("xtb_opt.out") as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)
    r.save()

    calc_obj.structure_set.add(r)

    return 0

def enso(charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-solv {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("enso.py {} --charge {}".format(solvent_add, charge), 'enso_pre.out')

def enso_run():
    return system("enso.py -run", 'enso.out')

@app.task
def nmr_enso(id, drawing, charge, solvent, calc_obj=None):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [crest, ["xtbopt.xyz", charge, solvent, "NMR"], "Generating conformer ensemble", "Failed to generate the conformers"],
        [enso, [charge, solvent], "Preparing the NMR prediction calculation", "Failed to prepare the NMR prediction calculation"],
        [enso_run, [], "Running the NMR prediction calculation", "Failed to run the NMR prediction calculation"],
    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results(["xtbopt.xyz"], calc_obj)
    if a != 0:
        return

    a = save_to_results(["crest_conformers.xyz"], calc_obj, multiple=True)
    if a != 0:
        return

    #r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)

    #r.save()
    #calc_obj.structure_set.add(r)

    with open("anmr.dat") as f:
        lines = f.readlines()
        with open("{}/nmr.csv".format(os.path.join(LAB_RESULTS_HOME, id)), 'w') as out:
                out.write("Chemical shift (ppm),Intensity\n")
                for ind, line in enumerate(lines):
                    if ind % 15 == 0:
                        sline = line.strip().split()
                        if float(sline[1]) > 0.001:
                            out.write("{},{}\n".format(-float(sline[0]), sline[1]))

    return 0

time_dict = {}

@task_prerun.connect
def task_prerun_handler(signal, sender, task_id, task, args, kwargs, **extras):
    time_dict[task_id] = time()

    calc_obj = Calculation.objects.get(pk=args[0])

    calc_obj.status = 1
    calc_obj.save()

    os.chdir(os.path.join(LAB_SCR_HOME, str(args[0])))
    args.append(calc_obj)


@task_postrun.connect
def task_postrun_handler(signal, sender, task_id, task, args, kwargs, retval, state, **extras):
    try:
        execution_time = time() - time_dict.pop(task_id)
    except KeyError:
        cost = -1

    job_id = args[0]
    calc_obj = Calculation.objects.get(pk=job_id)
    calc_obj.execution_time = int(execution_time)
    calc_obj.date_finished = timezone.now()

    for f in glob.glob(os.path.join(LAB_SCR_HOME, str(job_id)) + '/*.out'):
        fname = f.split('/')[-1]
        copyfile(f, os.path.join(LAB_RESULTS_HOME, str(job_id)) + '/' + fname)

    if retval == 0:
        calc_obj.status = 2
    else:
        calc_obj.status = 3
        calc_obj.error_message = "Unknown error"

    calc_obj.save()

    author = calc_obj.author
    author.calculation_time_used += execution_time
    author.save()

@app.task(name='celery.ping')
def ping():
    return 'pong'
