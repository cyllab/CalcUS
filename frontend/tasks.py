from __future__ import absolute_import, unicode_literals

from labsandbox.celery import app
import os
import decimal
from django.utils import timezone
import numpy as np

from time import time
from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']

decimal.getcontext().prec = 50

HARTREE_VAL = decimal.Decimal(2625.499638)
E_VAL = decimal.Decimal(2.7182818284590452353602874713527)
R_CONSTANT = decimal.Decimal(8.314)
TEMP = decimal.Decimal(298)

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

@app.task
def geom_opt(id):
    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))
    os.system("babel -imol initial.mol -oxyz initial.xyz -h --gen3D")
    os.system("xtb initial.xyz --opt | tee xtb.out")
    os.system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("cp xtbopt.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz xtbopt.xyz -omol {}/xtbopt.mol".format(os.path.join(LAB_RESULTS_HOME, id)))

    os.system("obabel xtbopt.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))

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
def conf_search(id):
    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))
    os.system("babel -imol initial.mol -oxyz initial.xyz -h --gen3D")
    os.system("crest initial.xyz -rthr 0.4 -ewin 4 | tee crest.out")

    os.system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("cp crest_conformers.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz crest_conformers.xyz -omol {}/conf.mol -m".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz crest_conformers.xyz -omol {}/crest_conformers.mol".format(os.path.join(LAB_RESULTS_HOME, id)))

    os.system("obabel {}/conf1.mol -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id), os.path.join(LAB_RESULTS_HOME, id)))

    energies = []
    with open("crest_conformers.xyz") as f:
        lines = f.readlines()
        ind = 0
        while ind < len(lines) - 1:
            line = lines[ind].strip()
            if len(line.split()) == 1:
                energies.append(float(lines[ind+1]))
                ind += 2
            else:
                ind += 1

    min_val, dd, weights = calc_boltzmann(energies)
    rel_energies = [(i - min_val)*HARTREE_VAL for i in energies]

    for ind, data in enumerate(zip(energies, rel_energies, weights)):
        r = Structure.objects.create(number=ind+1, energy=data[0], rel_energy=data[1], boltzmann_weight=data[2], homo_lumo_gap=0.0)
        r.save()
        calc_obj.structure_set.add(r)

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
def uvvis_simple(id):
    ww = []
    TT = []
    PP = []

    calc_obj = Calculation.objects.get(pk=id)

    calc_obj.status = 1
    calc_obj.save()

    os.chdir(os.path.join(LAB_SCR_HOME, str(id)))
    os.system("babel -imol initial.mol -oxyz initial.xyz -h --gen3D")
    os.system("xtb initial.xyz --opt | tee xtb.out")
    os.system("xtb4stda xtbopt.xyz | tee xtb4stda.out")
    os.system("stda -xtb -e 12 | tee stda.out")

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
        #ww.append(6.62607004*10**-34 * 299792458/ev)
        ww.append(1240/ev)
        TT.append(I)
    PP = sorted(zip(ww, TT), key=lambda i: i[1], reverse=True)
    yy = plot_peaks(f_x, PP)
    yy = np.array(yy)/max(yy)

    os.system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))

    with open("{}/uvvis.csv".format(os.path.join(LAB_RESULTS_HOME, id)), 'w') as out:
        out.write("Wavelength (nm), Absorbance\n")
        for ind, x in enumerate(f_x):
            out.write("{},{:.8f}\n".format(x, yy[ind]))

    os.system("babel -ixyz xtbopt.xyz -omol {}/xtbopt.mol".format(os.path.join(LAB_RESULTS_HOME, id)))

    os.system("obabel xtbopt.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_RESULTS_HOME, id)))

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

