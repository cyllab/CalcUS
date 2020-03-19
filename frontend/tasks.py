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
    'Dichloromethane': 'CH2Cl2',
    'Chloroform': 'CHCl3',
    'Dimethylformamide': 'DMF',
    'Dimethylsulfoxide': 'DMSO',
    'Diethyl ether': 'ether',
    'Water': 'H2O',
    'Methanol': 'methanol',
    'n-Hexane': 'n-hexane',
    'Tetrahydrofuran': 'THF',
    'Toluene': 'toluene',
        }

'''
def calc_boltzmann(data):

    #if hartree:
    gas_constant = decimal.Decimal(R_CONSTANT/HARTREE_VAL/1000)
    #else: #kcal/mol
    #    gas_constant = decimal.Decimal(R_CONSTANT/4.184)

    for i, _ in enumerate(data):
        data[i] = decimal.Decimal(data[i])

    minval = decimal.Decimal(min(data))

    sumnum = decimal.Decimal(0)
    sumdenum = decimal.Decimal(0)
    for i in range(1, len(data)):
        exp_val = E_VAL**(-(data[i]-data[0])/(gas_constant*TEMP))
        sumnum += decimal.Decimal(exp_val)*(data[i])
        sumdenum += exp_val
    weights = []
    for i, _ in enumerate(data):
        weights.append(E_VAL**(-(data[i]-data[0])/(gas_constant*TEMP))/(decimal.Decimal(1)+sumdenum))

    #_sum = [(gas_constant*temp), (decimal.Decimal(1)+sumdenum)]

    return minval, float((data[0]+sumnum)/(decimal.Decimal(1)+sumdenum)), weights
'''

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

@app.task
def geom_opt(id, drawing, charge, solvent):
    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    if solvent != "Vacuum":
        solvent_add = '-solv {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))

    a = handle_input_file(drawing)

    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    a = system("xtb initial.xyz --chrg {} {} --opt".format(charge, solvent_add), 'xtb.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to optimize the structure"
        calc_obj.save()
        return

    a = system("cp xtbopt.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to copy the results to the results directory"
        calc_obj.save()
        return

    a = system("babel -ixyz xtbopt.xyz -omol {}/xtbopt.mol".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the optimized geometry"
        calc_obj.save()
        return

    with open("xtb.out") as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)

    r.save()
    calc_obj.structure_set.add(r)
    calc_obj.status = 2
    calc_obj.save()

    return 0

@app.task
def conf_search(id, drawing, charge, solvent):
    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))

    a = handle_input_file(drawing)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    a = system("crest initial.xyz --chrg {} {} -rthr 0.4 -ewin 4".format(charge, solvent_add), 'crest.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to find the conformers"
        calc_obj.save()
        return

    a = system("cp crest_conformers.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to copy the results to the results directory"
        calc_obj.save()
        return

    a = system("babel -ixyz crest_conformers.xyz -omol {}/conf.mol -m".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert conformers"
        calc_obj.save()
        return

    a = system("babel -ixyz crest_conformers.xyz -omol {}/crest_conformers.mol".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert conformers"
        calc_obj.save()
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
    calc_obj.status = 2
    calc_obj.date_finished = timezone.now()
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


@app.task
def uvvis_simple(id, drawing, charge, solvent):
    ww = []
    TT = []
    PP = []

    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))

    a = handle_input_file(drawing)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    a = system("xtb initial.xyz --chrg {} {} --opt".format(charge, solvent_add), 'xtb.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to optimize the structure"
        calc_obj.save()
        return

    a = system("xtb4stda xtbopt.xyz --chrg {} {}".format(charge, solvent_add), 'xtb4stda.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to perform the ground-state calculation"
        calc_obj.save()
        return

    a = system("stda -xtb -e 12", 'stda.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to perform the time-dependent DFT calculation"
        calc_obj.save()
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


    with open("{}/uvvis.csv".format(os.path.join(LAB_RESULTS_HOME, id)), 'w') as out:
        out.write("Wavelength (nm), Absorbance\n")
        for ind, x in enumerate(f_x):
            out.write("{},{:.8f}\n".format(x, yy[ind]))

    a = system("babel -ixyz xtbopt.xyz -omol {}/xtbopt.mol".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the optimized geometry"
        calc_obj.save()
        return


    with open("xtb.out") as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)

    r.save()
    calc_obj.structure_set.add(r)

    calc_obj.status = 2
    calc_obj.date_finished = timezone.now()
    calc_obj.save()

    return 0

@app.task
def nmr(id, drawing, charge, solvent):

    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    if solvent != "Vacuum":
        solvent_add = '{}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))

    a = handle_input_file(drawing)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    a = system("xtb initial.xyz --chrg {} {} --opt".format(charge, solvent_add), 'xtb.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to optimize the structure"
        calc_obj.save()
        return

    a = system("crest xtbopt.xyz --chrg {} {} -rthr 0.4 -ewin 4 --nmr".format(charge, solvent_add), 'crest.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to find the conformers"
        calc_obj.save()
        return

    a = system("enso.py {} --charge {} -sm4 smd -sm3 smd -sm smd -smgsolv2 sm -O 8 -prog_rrho xtb -ancopt on".format(solvent_add, charge), 'enso_pre.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to prepare the NMR prediction calculation"
        calc_obj.save()
        return

    a = system("enso.py -run", 'enso.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to run the NMR prediction calculation"
        calc_obj.save()
        return

    a = system("anmr", 'anmr.out')
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the final NMR spectrum"
        calc_obj.save()
        return

time_dict = {}

@task_prerun.connect
def task_prerun_handler(signal, sender, task_id, task, args, kwargs, **extras):
    time_dict[task_id] = time()


@task_postrun.connect
def task_postrun_handler(signal, sender, task_id, task, args, kwargs, retval, state, **extras):
    try:
        execution_time = time() - time_dict.pop(task_id)
    except KeyError:
        cost = -1

    job_id = args[0]
    calc_obj = Calculation.objects.get(pk=job_id)
    calc_obj.execution_time = int(execution_time)
    calc_obj.save()

    author = calc_obj.author
    author.calculation_time_used += execution_time
    author.save()

