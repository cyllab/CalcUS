from __future__ import absolute_import, unicode_literals

from labsandbox.celery import app

from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure
from django.utils import timezone

import os
import numpy as np
import decimal

from time import time, sleep

import subprocess
import shlex
from shutil import copyfile
import glob
import ssh2
from threading import Lock
import threading

from ssh2.sftp import LIBSSH2_FXF_READ, LIBSSH2_SFTP_S_IWGRP, LIBSSH2_SFTP_S_IRWXU
from ssh2.sftp import LIBSSH2_FXF_CREAT, LIBSSH2_FXF_WRITE, \
    LIBSSH2_SFTP_S_IRUSR, LIBSSH2_SFTP_S_IRGRP, LIBSSH2_SFTP_S_IWUSR, \
    LIBSSH2_SFTP_S_IROTH

try:
    is_test = os.environ['LAB_TEST']
except:
    is_test = False


if is_test:
    LAB_SCR_HOME = os.environ['LAB_TEST_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_TEST_RESULTS_HOME']
else:
    LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']

PAL = os.environ['OMP_NUM_THREADS'][0]
ORCAPATH = os.environ['ORCAPATH']

decimal.getcontext().prec = 50

REMOTE = False
connections = {}
locks = {}
remote_dirs = {}


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

def direct_command(command, conn, lock):
    lock.acquire()
    sess = conn[2]

    try:
        chan = sess.open_session()
        if isinstance(chan, int):
            print("Failed to open channel, trying again")
            lock.release()
            sleep(1)
            direct_command(command, conn, lock)
            return
        chan.execute("source ~/.bashrc; " + command)

    except ssh2.exceptions.Timeout:
        print("Command timed out")
        lock.release()
        return


    try:
        chan.wait_eof()
        chan.close()
        chan.wait_closed()
        size, data = chan.read()
    except ssh2.exceptions.Timeout:
        print("Channel timed out")
        lock.release()
        return

    total = b''
    while size > 0:
        total += data
        size, data = chan.read()

    lock.release()

    if total != None:
        return total.decode('utf-8').split('\n')

def sftp_get(src, dst, conn, lock):
    _src = str(src).replace('//', '/')
    _dst = str(dst).replace('//', '/')

    sftp = conn[3]
    lock.acquire()

    system("mkdir -p {}".format('/'.join(_dst.split('/')[:-1])), force_local=True)

    if src.strip() == "":
        lock.release()
        return

    try:
        with sftp.open(_src, LIBSSH2_FXF_READ, LIBSSH2_SFTP_S_IRUSR) as f:
            with open(_dst, 'wb') as local:
                for size, data in f:
                    if data[-1:] == b'\x00':
                        local.write(data[:-1])
                        break
                    else:
                        local.write(data)
    except ssh2.exceptions.SFTPProtocolError:
        print("Could not get remote file {}".format(src))
        lock.release()
        return
    except ssh2.exceptions.Timeout:
        print("Timeout")
        lock.release()
        sftp_get(src, dst, conn)
        return
    lock.release()


def sftp_put(src, dst, conn, lock):

    if not os.path.exists(src):
        lock.release()
        return

    direct_command("mkdir -p {}".format('/'.join(dst.split('/')[:-1])), conn, lock)

    sftp = conn[3]

    lock.acquire()
    mode = LIBSSH2_SFTP_S_IRUSR | \
               LIBSSH2_SFTP_S_IWUSR

    f_flags = LIBSSH2_FXF_CREAT | LIBSSH2_FXF_WRITE

    try:
        with open(src, 'rb') as local, \
                sftp.open(dst, f_flags, mode) as remote:
            for data in local:
                if data[-1:] == b'\x00' or data[-1:] == b'\x04' or data[-1:] == b'\x03':
                    remote.write(data[:-1])
                    break
                else:
                    remote.write(data)

    except ssh2.exceptions.Timeout:
        print("Timeout while uploading, retrying...")
        lock.release()
        sftp_put(src, dst, conn, lock)
        return

    lock.release()

def wait_until_done(job_id, conn, lock):
    DELAY = [5, 10, 15, 20, 30]
    ind = 0
    while True:
        sleep(DELAY[ind])
        if ind < len(DELAY)-1:
            ind += 1
        output = direct_command("squeue -j {}".format(job_id), conn, lock)
        if output != None and len(output) < 2:
            return 0

def system(command, log_file="", force_local=False):
    if REMOTE and not force_local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        if log_file != "":
            output = direct_command("cd {}; cp /home/{}/calcus/submit.sh .; echo '{} | tee {}' >> submit.sh; sbatch submit.sh".format(remote_dir, conn[0].cluster_username, command, log_file), conn, lock)
        else:
            output = direct_command("cd {}; cp /home/{}/calcus/submit.sh .; echo '{}' >> submit.sh; sbatch submit.sh".format(remote_dir, conn[0].cluster_username, command), conn, lock)

        if output[-2].find("Submitted batch job") != -1:
            job_id = output[-2].replace('Submitted batch job', '').strip()
            wait_until_done(job_id, conn, lock)
            return 0
        else:
            return 1
    else:
        if log_file != "":
            with open(log_file, 'w') as out:
                a = subprocess.run(shlex.split(command), stdout=out, stderr=out).returncode
            return a
        else:
            return subprocess.run(shlex.split(command)).returncode

def handle_input_file(drawing, calc_obj):
    if os.path.isfile("{}/initial_2D.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
        return system("obabel {}/initial_2D.mol -O {}/initial.xyz -h --gen3D".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)

    if drawing:
        SCALE = 20
        #return system("babel -imol {}/initial.mol -oxyz {}/initial.xyz -h --gen3D".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)
    else:
        SCALE = 1

    if os.path.isfile("{}/initial.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
        #return system("babel -imol initial.mol -oxyz {}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)
        with open(os.path.join("{}/initial.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))))) as f:
            lines = f.readlines()[4:]
        with open(os.path.join("{}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))), 'w') as out:
            to_print = []
            for line in lines:
                sline = line.split()
                try:
                    a = int(sline[3])
                except ValueError:
                    to_print.append("{} {} {} {}\n".format(sline[3], float(sline[0])*SCALE, float(sline[1])*SCALE, float(sline[2])*SCALE))
                else:
                    break
            num = len(to_print)
            out.write("{}\n".format(num))
            out.write("CalcUS\n")
            for line in to_print:
                out.write(line)
            return 0

    elif os.path.isfile("{}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
        return 0
    elif os.path.isfile("{}/initial.mol2".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
        return system("babel -imol2 {}/initial.mol2 -oxyz {}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)
    elif os.path.isfile("{}/initial.sdf".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
        return system("babel -isdf {}/initial.sdf -oxyz {}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)


def xtb_opt(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("xtb {} --chrg {} {} --opt".format(in_file, charge, solvent_add), 'xtb_opt.out')

def xtb_ts(in_file, charge, solvent, id):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    ORCA_TEMPLATE = """!xtb OPTTS
    %pal
    nprocs {}
    end
    {}
    *xyz {} 1 
    {}
    *"""

    if solvent == "Vacuum":
        solvent_add = ""
    else:
        solvent_add = '''%cpcm
        smd true
        SMDsolvent "{}"
        end'''.format(solvent)

    with open(os.path.join(LAB_SCR_HOME, str(id), in_file)) as f:
        lines = f.readlines()[2:]

    with open(os.path.join(LAB_SCR_HOME, str(id), 'ts.inp'), 'w') as out:
        out.write(ORCA_TEMPLATE.format(PAL, solvent_add, charge, ''.join(lines)))

    return system("{}/orca ts.inp".format(ORCAPATH), 'xtb_ts.out')

def xtb_scan(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("xtb {} --input scan --chrg {} {} --opt".format(in_file, charge, solvent_add), 'xtb_opt.out')

def xtb_freq(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("xtb {} --uhf 1 --chrg {} {} --hess".format(in_file, charge, solvent_add), 'xtb_freq.out')

def animate_vib(in_file, calc_obj):
    with open(os.path.join(LAB_SCR_HOME, str(calc_obj.id), in_file)) as f:
        lines = f.readlines()
        num_atoms = int(lines[0].strip())
        lines = lines[2:]

    hess = []
    struct = []

    for line in lines:
        a, x, y, z = line.strip().split()
        struct.append([a, float(x), float(y), float(z)])

    with open("hessian") as f:
        lines = f.readlines()[1:]
        for line in lines:
            hess += [float(i) for i in line.strip().split()]

        num_freqs = len(hess)/(3*num_atoms)
        if not num_freqs.is_integer():
            print("Incorrect number of frequencies!")
            exit(0)

        num_freqs = int(num_freqs)
    SCALING = 0.05
    hess = [i*SCALING for i in hess]
    def output_with_displacement(mol, out, hess):
        t = 10
        mols = [mol]
        for _t in range(t):
            new_mol = []
            for ind, (a, x, y, z) in enumerate(mols[-1]):
                _x = x + hess[3*ind]
                _y = y + hess[3*ind+1]
                _z = z + hess[3*ind+2]
                new_mol.append([a, _x, _y, _z])
            mols.append(new_mol)

        for _t in range(t):
            new_mol = []
            for ind, (a, x, y, z) in enumerate(mols[0]):
                _x = x - hess[3*ind]
                _y = y - hess[3*ind+1]
                _z = z - hess[3*ind+2]
                new_mol.append([a, _x, _y, _z])
            mols.insert(0, new_mol)

        for mol in mols:
            out.write("{}\n".format(num_atoms))
            out.write("Free\n")
            for a, x, y, z in mol:
                out.write("{} {} {} {}\n".format(a, x, y, z))

    for ind in range(num_freqs):
        _hess = hess[3*num_atoms*ind:3*num_atoms*(ind+1)]
        with open(os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), "freq_{}.xyz".format(ind)), 'w') as out:
            output_with_displacement(struct, out, _hess)
    return 0

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

def xtb4stda(in_file, charge, solvent):
    if solvent != "Vacuum":
        solvent_add_xtb = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add_xtb = ''

    return system("xtb4stda {} -chrg {} {}".format(in_file, charge, solvent_add_xtb), 'xtb4stda.out')

def stda(charge, solvent):
    return system("stda -xtb -e 12", 'stda.out')

def enso(charge, solvent):
    if solvent != "Vacuum":
        solvent_add = '-solv {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    return system("enso.py {} --charge {}".format(solvent_add, charge), 'enso_pre.out')

def enso_run():
    return system("enso.py -run", 'enso.out')

def anmr():
    return system("anmr", 'anmr.out')

def run_steps(steps, calc_obj, drawing, id):

    a = handle_input_file(drawing, calc_obj)

    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to convert the input structure"
        calc_obj.save()
        return

    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, str(id))), force_local=True)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    a = system("obabel {}/initial.xyz -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_RESULTS_HOME, str(id))), force_local=True)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to generate the icon"
        calc_obj.save()
        return

    if REMOTE:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = "/scratch/{}/calcus/{}".format(conn[0].cluster_username, calc_obj.id)
        remote_dirs[pid] = remote_dir

        direct_command("mkdir -p {}".format(remote_dir), conn, lock)
        for f in glob.glob(os.path.join(LAB_SCR_HOME, str(calc_obj.id)) + '/*'):
            fname = f.split('/')[-1]
            sftp_put(f, os.path.join(remote_dir, fname), conn, lock)

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

    if REMOTE:
        files = direct_command("ls {}".format(remote_dir), conn, lock)
        for f in files:
            if f.strip() != '':
                sftp_get(os.path.join(remote_dir, f), os.path.join(LAB_SCR_HOME, str(calc_obj.id), f), conn, lock)
    return 0

def save_to_results(f, calc_obj, multiple=False, out_name=""):
    s = f.split('.')
    fname = f.split('/')[-1]
    if out_name == "":
        out_name = fname
    if len(s) == 2:
        name, ext = s
        if ext == 'xyz':
            if multiple:
                a = system("babel -ixyz {}/{} -oxyz {}/conf.xyz -m".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
            else:
                copyfile(os.path.join(LAB_SCR_HOME, str(calc_obj.id), fname), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
        else:
            copyfile(os.path.join(LAB_SCR_HOME, str(calc_obj.id), fname), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
    elif len(s) == 1:
        name = s
        copyfile(os.path.join(LAB_SCR_HOME, str(calc_obj.id), fname), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
    else:
        print("Odd number of periods!")
        return -1
    return 0


FACTOR = 1
SIGMA = 0.2
SIGMA_L = 6199.21
E = 4.4803204E-10
NA = 6.02214199E23
C = 299792458
HC = 4.135668E15*C
ME = 9.10938E-31

FUZZ_INT = 1./30
FUZZ_WIDTH = 50000

def plot_peaks(_x, PP):
    val = 0
    for w, T in PP:
        val += np.sqrt(np.pi)*E**2*NA/(1000*np.log(10)*C**2*ME)*T/SIGMA*np.exp(-((HC/_x-HC/w)/(HC/SIGMA_L))**2)
    return val

def plot_vibs(_x, PP):
    val = 0
    for w, T in PP:
        val += FUZZ_INT*(1 - np.exp(-(FUZZ_WIDTH/w-FUZZ_WIDTH/_x)**2))
    return val


@app.task
def geom_opt(id, drawing, charge, solvent, calc_obj=None, remote=False):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],

    ]
    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("xtbopt.xyz", calc_obj)
    if a != 0:
        return

    with open("{}/xtb_opt.out".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
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
def geom_opt_freq(id, drawing, charge, solvent, calc_obj=None, remote=False):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [xtb_freq, ["xtbopt.xyz", charge, solvent], "Calculating frequency modes", "Failed to calculate frequency modes"],
        [animate_vib, ["xtbopt.xyz", calc_obj], "Animating frequency modes", "Failed to animate frequency modes"],
    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("xtbopt.xyz", calc_obj)
    if a != 0:
        return

    a = save_to_results("vibspectrum", calc_obj, multiple=True)
    if a != 0:
        return

    with open("{}/xtb_freq.out".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-4].split()[3])
        G = float(lines[ind-2].split()[4])

    vib_file = os.path.join(LAB_RESULTS_HOME, str(id), "vibspectrum")

    if os.path.isfile(vib_file):
        with open(vib_file) as f:
            lines = f.readlines()

        vibs = []
        intensities = []
        for line in lines:
            if len(line.split()) > 4 and line[0] != '#':
                sline = line.split()
                try:
                    a = float(sline[1])
                    if a == 0.:
                        continue
                except ValueError:
                    pass
                vib = float(line[20:33].strip())
                vibs.append(vib)
                try:
                    intensity = float(sline[3])
                except ValueError:
                    continue
                else:
                    intensities.append(intensity)
        if len(vibs) == len(intensities):
            x = np.arange(500, 4000, 1)
            spectrum = plot_vibs(x, zip(vibs, intensities))
            with open(os.path.join(LAB_RESULTS_HOME, str(id), "IR.csv"), 'w') as out:
                out.write("Wavenumber,Intensity\n")
                intensities = 1000*np.array(intensities)/max(intensities)
                for _x, i in sorted((zip(list(x), spectrum)), reverse=True):
                    out.write("-{:.1f},{:.5f}\n".format(_x, i))



    r = Structure.objects.create(number=1, energy=E, free_energy=G, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)
    r.save()

    calc_obj.structure_set.add(r)

    return 0

@app.task
def ts_freq(id, drawing, charge, solvent, calc_obj=None, remote=False):

    steps = [
        [xtb_ts, ["initial.xyz", charge, solvent, calc_obj.id], "Optimizing the transition state", "Failed to optimize the transition state"],
        [xtb_freq, ["ts.xyz", charge, solvent], "Calculating frequency modes", "Failed to calculate frequency modes"],
        [animate_vib, ["ts.xyz", calc_obj], "Animating frequency modes", "Failed to animate frequency modes"],
    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("ts.xyz", calc_obj)
    if a != 0:
        return

    a = save_to_results("vibspectrum", calc_obj, multiple=True)
    if a != 0:
        return

    with open("{}/xtb_freq.out".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-4].split()[3])
        G = float(lines[ind-2].split()[4])

    vib_file = os.path.join(LAB_RESULTS_HOME, id, "vibspectrum")

    if os.path.isfile(vib_file):
        with open(vib_file) as f:
            lines = f.readlines()

        vibs = []
        intensities = []
        for line in lines:
            if len(line.split()) > 4 and line[0] != '#':
                sline = line.split()
                try:
                    a = float(sline[1])
                    if a == 0.:
                        continue
                except ValueError:
                    pass
                vib = float(line[20:33].strip())
                vibs.append(vib)
                try:
                    intensity = float(sline[3])
                except ValueError:
                    continue
                else:
                    intensities.append(intensity)
        if len(vibs) == len(intensities):
            x = np.arange(500, 4000, 1)
            spectrum = plot_vibs(x, zip(vibs, intensities))
            with open(os.path.join(LAB_RESULTS_HOME, id, "IR.csv"), 'w') as out:
                out.write("Wavenumber,Intensity\n")
                intensities = 1000*np.array(intensities)/max(intensities)
                for _x, i in sorted((zip(list(x), spectrum)), reverse=True):
                    out.write("-{:.1f},{:.5f}\n".format(_x, i))



    r = Structure.objects.create(number=1, energy=E, free_energy=G, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)
    r.save()

    calc_obj.structure_set.add(r)

    return 0

@app.task
def conf_search(id, drawing, charge, solvent, calc_obj=None, remote=False):
    #os.path.join(LAB_SCR_HOME, str(calc_obj.id))
    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [crest, ["xtbopt.xyz", charge, solvent, "Final"], "Generating conformer ensemble", "Failed to generate the conformers"],

    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("crest_conformers.xyz", calc_obj, multiple=True)
    a = save_to_results("crest_conformers.xyz", calc_obj)

    if a != 0:
        return

    with open("{}/crest.out".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
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

@app.task
def uvvis_simple(id, drawing, charge, solvent, calc_obj=None, remote=False):

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

    a = save_to_results("xtbopt.xyz", calc_obj, multiple=True)
    if a != 0:
        return

    f_x = np.arange(120.0, 1200.0, 1.0)

    with open("{}/tda.dat".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
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

@app.task
def nmr_enso(id, drawing, charge, solvent, calc_obj=None, remote=False):

    steps = [
        [xtb_opt, ["initial.xyz", charge, solvent], "Optimizing geometry", "Failed to optimize the geometry"],
        [crest, ["xtbopt.xyz", charge, solvent, "NMR"], "Generating conformer ensemble", "Failed to generate the conformers"],
        [enso, [charge, solvent], "Preparing the NMR prediction calculation", "Failed to prepare the NMR prediction calculation"],
        [enso_run, [], "Running the NMR prediction calculation", "Failed to run the NMR prediction calculation"],
        [anmr, [], "Creating the final spectrum", "Failed to create the final spectrum"],
    ]

    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("xtbopt.xyz", calc_obj)
    if a != 0:
        return

    a = save_to_results("crest_conformers.xyz", calc_obj, multiple=True)
    if a != 0:
        return


    #r = Structure.objects.create(number=1, energy=E, rel_energy=0., boltzmann_weight=1., homo_lumo_gap=hl_gap)

    #r.save()
    #calc_obj.structure_set.add(r)

    with open("{}/anmr.dat".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))) as f:
        lines = f.readlines()
        with open("{}/nmr.csv".format(os.path.join(LAB_RESULTS_HOME, id)), 'w') as out:
                out.write("Chemical shift (ppm),Intensity\n")
                for ind, line in enumerate(lines):
                    if ind % 15 == 0:
                        sline = line.strip().split()
                        if float(sline[1]) > 0.001:
                            out.write("{},{}\n".format(-float(sline[0]), sline[1]))
                        else:
                            out.write("{},{}\n".format(-float(sline[0]), 0.0))
                if float(lines[0].strip().split()[0]) > 0.:
                    x = np.arange(-float(lines[0].strip().split()[0]), 0.0, 0.1)
                    for _x in x:
                        out.write("{:.2f},0.0\n".format(_x))
                if float(lines[-1].strip().split()[0]) < 10.:
                    x = np.arange(-10.0, -float(lines[-1].strip().split()[0]), 0.1)
                    for _x in x:
                        out.write("{:.2f},0.0\n".format(_x))
    return 0

@app.task
def constraint_opt(id, drawing, charge, solvent, constraints, calc_obj=None, remote=False):

    steps = [
        [xtb_scan, ["initial.xyz", charge, solvent], "Performing the constrained optimisation", "Failed to perform the constrained optimisation"],

    ]

    with open("{}/scan".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))), 'w') as out:
        out.write("$constrain\n")
        out.write("force constant=99\n")
        has_scan = False
        for cmd in constraints:
            type = len(cmd[-1])
            if type == 2:
                out.write("distance: {}, {}, auto\n".format(*cmd[-1]))
            if type == 3:
                out.write("angle: {}, {}, {}, auto\n".format(*cmd[-1]))
            if type == 4:
                out.write("dihedral: {}, {}, {}, {}, auto\n".format(*cmd[-1]))
            if cmd[0] == "Scan":
                has_scan = True
        if has_scan:
            calc_obj.has_scan = True
            out.write("$scan\n")
            counter = 1
            for cmd in constraints:
                if cmd[0] == "Scan":
                    out.write("{}: {}, {}, {}\n".format(counter, *cmd[1]))
                    counter += 1
        out.write("$end")


    a = run_steps(steps, calc_obj, drawing, id)
    if a != 0:
        return

    a = save_to_results("xtbopt.xyz", calc_obj)
    if has_scan:
        a = save_to_results("xtbscan.log", calc_obj, out_name="xtbscan.xyz")

    if a != 0:
        return

    return 0


time_dict = {}

@task_prerun.connect
def task_prerun_handler(signal, sender, task_id, task, args, kwargs, **extras):
    if task != ping:
        time_dict[task_id] = time()

        calc_obj = Calculation.objects.get(pk=args[0])

        calc_obj.status = 1
        calc_obj.save()

        os.chdir(os.path.join(LAB_SCR_HOME, str(args[0])))
        args.append(calc_obj)


@task_postrun.connect
def task_postrun_handler(signal, sender, task_id, task, args, kwargs, retval, state, **extras):
    if task != ping:
        try:
            execution_time = time() - time_dict.pop(task_id)
        except KeyError:
            execution_time = -1

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
            if calc_obj.error_message == "":
                calc_obj.error_message = "Unknown error"

        calc_obj.save()

        author = calc_obj.author
        author.calculation_time_used += execution_time
        author.save()

@app.task(name='celery.ping')
def ping():
    return 'pong'


