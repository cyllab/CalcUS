from __future__ import absolute_import, unicode_literals

from labsandbox.celery import app
import os
import decimal

from .models import Calculation, Result

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_TODO_HOME = os.environ['LAB_TODO_HOME']
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
    os.system("xtb initial.xyz --opt")
    os.system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("cp xtbopt.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz xtbopt.xyz -omol {}/xtbopt.mol".format(os.path.join(LAB_RESULTS_HOME, id)))

    with open("xtbopt.xyz") as f:
        lines = f.readlines()
        E = float(lines[1].split()[1])

    r = Result.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1.)

    r.save()
    calc_obj.result_set.add(r)
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
    os.system("crest initial.xyz -rthr 0.4 -ewin 4")

    os.system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("cp crest_conformers.xyz {}/".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz crest_conformers.xyz -omol {}/conf.mol -m".format(os.path.join(LAB_RESULTS_HOME, id)))
    os.system("babel -ixyz crest_conformers.xyz -omol {}/crest_conformers.mol".format(os.path.join(LAB_RESULTS_HOME, id)))

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
        r = Result.objects.create(number=ind+1, energy=data[0], rel_energy=data[1], boltzmann_weight=data[2])
        r.save()
        calc_obj.result_set.add(r)

    calc_obj.status = 2
    calc_obj.save()

    return 0
