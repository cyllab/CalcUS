from __future__ import absolute_import, unicode_literals

from calcus.celery import app
import string
import signal
import psutil
import pika
import requests

from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure
from django.utils import timezone

from django.db.utils import IntegrityError
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult

import os
import numpy as np
import decimal
import math
from time import time, sleep

import subprocess
import shlex
from shutil import copyfile, rmtree
import glob
import ssh2
from threading import Lock
import threading

from .libxyz import *

from celery import group
from celery.task.control import revoke

from .models import *
from ssh2.sftp import LIBSSH2_FXF_READ, LIBSSH2_SFTP_S_IWGRP, LIBSSH2_SFTP_S_IRWXU
from ssh2.sftp import LIBSSH2_FXF_CREAT, LIBSSH2_FXF_WRITE, \
    LIBSSH2_SFTP_S_IRUSR, LIBSSH2_SFTP_S_IRGRP, LIBSSH2_SFTP_S_IWUSR, \
    LIBSSH2_SFTP_S_IROTH

from .ORCA_calculation import OrcaCalculation
from .Gaussian_calculation import GaussianCalculation
from .xtb_calculation import XtbCalculation
from .calculation_helper import *

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False


import traceback
import periodictable

if is_test:
    CALCUS_SCR_HOME = os.environ['CALCUS_TEST_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_TEST_RESULTS_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_TEST_CLUSTER_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_TEST_KEY_HOME']
else:
    CALCUS_SCR_HOME = os.environ['CALCUS_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_RESULTS_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_CLUSTER_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_KEY_HOME']

PAL = os.environ['OMP_NUM_THREADS'][0]
STACKSIZE = os.environ['OMP_STACKSIZE']
if STACKSIZE.find("G") != -1:
    STACKSIZE = int(STACKSIZE.replace('G', ''))*1024
elif STACKSIZE.find("MB") != -1:
    STACKSIZE = int(STACKSIZE.replace('MB', ''))

MEM = int(PAL)*STACKSIZE

EBROOTORCA = os.environ['EBROOTORCA']

REMOTE = False
connections = {}
locks = {}
remote_dirs = {}
kill_sig = []

def direct_command(command, conn, lock):
    lock.acquire()
    sess = conn[2]

    try:
        chan = sess.open_session()
        if isinstance(chan, int):
            print("Failed to open channel, trying again")
            lock.release()
            sleep(1)
            return direct_command(command, conn, lock)
    except ssh2.exceptions.Timeout:
        print("Command timed out")
        lock.release()
        return 0
    except ssh2.exceptions.ChannelFailure:
        print("Channel failure")
        lock.release()
        sleep(1)
        return direct_command(command, conn, lock)
    except ssh2.exceptions.SocketSendError:
        print("Socket send error, trying again")
        lock.release()
        sleep(1)
        return direct_command(command, conn, lock)

    chan.execute("source ~/.bashrc; " + command)

    try:
        chan.wait_eof()
        chan.close()
        chan.wait_closed()
        size, data = chan.read()
    except ssh2.exceptions.Timeout:
        print("Channel timed out")
        lock.release()
        return 1

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
        return -1

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
        return -1
    except ssh2.exceptions.Timeout:
        print("Timeout")
        lock.release()
        return sftp_get(src, dst, conn, lock)
    lock.release()
    return 0


def sftp_put(src, dst, conn, lock):

    if not os.path.exists(src):
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

def wait_until_logfile(remote_dir, conn, lock):
    if is_test:
        DELAY = [5]
    else:
        DELAY = [5, 30, 60, 180, 300, 600]

    ind = 0
    while ind < len(DELAY):
        output = direct_command("ls {}".format(remote_dir), conn, lock)
        if not isinstance(output, int):
            if len(output) == 1 and output[0].strip() == '':
                print("Received nothing, ignoring")
            else:
                _output = [i for i in output if i.strip() != '' ]
                for i in _output:
                    if i.find("CalcUS-") != -1 and i.find(".log") != -1:
                        job_id = i.replace('CalcUS-', '').replace('.log', '')
                        print("Log found: {}".format(job_id))
                        return job_id
        sleep(DELAY[ind])
        ind += 1
    print("Failed to find a job log")
    return -1

def wait_until_done(calc, conn, lock):
    job_id = calc.remote_id
    print("Waiting for job {} to finish".format(job_id))

    if is_test:
        DELAY = [5]
    else:
        DELAY = [5, 20, 30, 60, 120, 240, 600]

    ind = 0

    pid = int(threading.get_ident())

    while True:
        sleep(DELAY[ind])
        if ind < len(DELAY)-1:
            ind += 1
        output = direct_command("squeue -j {}".format(job_id), conn, lock)
        if not isinstance(output, int):
            if len(output) == 1 and output[0].strip() == '':
                #Not sure
                print("Job done")
                return 0
            else:
                _output = [i for i in output if i.strip() != '' ]
                print("Waiting ({})".format(job_id))
                if _output != None and len(_output) < 2:
                    print("Job done")
                    return 0
                else:
                    status = _output[1].split()[4]
                    if status == "R" and calc.status == 0:
                        calc.date_started = timezone.now()
                        calc.status = 1
                        calc.save()

        if pid in kill_sig:
            direct_command("scancel {}".format(job_id), conn, lock)
            kill_sig.remove(pid)
            return -2

        if pid not in connections.keys():
            print("Thread aborted for calculation {}".format(calc.id))
            return 7

def system(command, log_file="", force_local=False, software="xtb", calc_id=-1):
    if REMOTE and not force_local:
        assert calc_id != -1

        calc = Calculation.objects.get(pk=calc_id)

        pid = int(threading.get_ident())
        #Get the variables based on thread ID
        #These are already set by cluster_daemon when running
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        if calc.status == 0:
            #calc.status = 1
            #calc.save()

            if log_file != "":
                output = direct_command("cd {}; cp /home/{}/calcus/submit_{}.sh .; echo '{} | tee {}' >> submit_{}.sh; sbatch submit_{}.sh | tee calcus".format(remote_dir, conn[0].cluster_username, software, command, log_file, software, software), conn, lock)
            else:
                output = direct_command("cd {}; cp /home/{}/calcus/submit_{}.sh .; echo '{}' >> submit_{}.sh; sbatch submit_{}.sh | tee calcus".format(remote_dir, conn[0].cluster_username, software, command, software, software), conn, lock)

            if output == 1:#Channel timed out
                if calc_id != -1:
                    ind = 0

                    while ind < 20:
                        output = direct_command("cd {}; cat calcus".format(remote_dir), conn, lock)
                        if isinstance(output, int):
                            ind += 1
                            sleep(1)
                        else:
                            break
                    if not isinstance(output, int):
                        if len(output) == 1 and output[0].strip() == '':
                            print("Calcus file empty, waiting for a log file")
                            job_id = wait_until_logfile(remote_dir, conn, lock)
                            if job_id == -1:
                                return 1
                            else:
                                calc.remote_id = int(job_id)
                                calc.save()
                                ret = wait_until_done(calc, conn, lock)
                                return ret
                        else:
                            job_id = output[-2].replace('Submitted batch job', '').strip()

                            calc.remote_id = int(job_id)
                            calc.save()
                            ret = wait_until_done(calc, conn, lock)
                            return ret
                    else:
                        return output
                else:
                    print("Channel timed out and no calculation id is set")
                    return 1
            elif output == 0:
                print("Command timed out")
                return 1
            else:
                if output[-2].find("Submitted batch job") != -1:
                    job_id = output[-2].replace('Submitted batch job', '').strip()
                    calc.remote_id = int(job_id)
                    calc.save()
                    ret = wait_until_done(calc, conn, lock)
                    return ret
                else:
                    return 1
        else:
            ret = wait_until_done(calc, conn, lock)
            return ret
    else:#Local
        if calc_id != -1:
            calc = Calculation.objects.get(pk=calc_id)
            calc.status = 1
            calc.date_started = timezone.now()
            calc.save()
            res = AbortableAsyncResult(calc.task_id)

        if log_file != "":
            with open(log_file, 'w') as out:
                t = subprocess.Popen(shlex.split(command), stdout=out, stderr=out)
                while True:
                    poll = t.poll()

                    if not poll is None:
                        return t.returncode

                    if calc_id != -1 and res.is_aborted() == True:
                        t.terminate()
                        t.kill()
                        t.wait()
                        return -2

                    sleep(1)
        else:
            t = subprocess.Popen(shlex.split(command))
            while True:
                poll = t.poll()

                if not poll is None:
                    return t.returncode

                if calc_id != -1 and res.is_aborted() == True:

                    parent = psutil.Process(t.pid)
                    children = parent.children(recursive=True)
                    for process in children:
                        process.send_signal(signal.SIGTERM)

                    #t.kill()
                    t.terminate()
                    t.wait()
                    return -1

                sleep(1)

def generate_xyz_structure(drawing, structure):
    if structure.xyz_structure == "":
        if structure.mol_structure != '':
            t = time()
            fname = "{}_{}".format(t, structure.id)
            if drawing:
                with open("/tmp/{}.mol".format(fname), 'w') as out:
                    out.write(structure.mol_structure)
                a = system("obabel /tmp/{}.mol -O /tmp/{}.xyz -h --gen3D".format(fname, fname), force_local=True)
                with open("/tmp/{}.xyz".format(fname)) as f:
                    lines = f.readlines()
                    structure.xyz_structure = clean_xyz(''.join(lines))
                    structure.save()
                    return 0
            else:
                to_print = []
                for line in structure.mol_structure.split('\n')[4:]:
                    sline = line.split()
                    try:
                        a = int(sline[3])
                    except ValueError:
                        to_print.append("{} {} {} {}\n".format(sline[3], float(sline[0]), float(sline[1]), float(sline[2])))
                    else:
                        break
                num = len(to_print)
                _xyz = "{}\n".format(num)
                _xyz += "CalcUS\n"
                for line in to_print:
                    _xyz += line
                structure.xyz_structure = clean_xyz(_xyz)
                structure.save()
                return 0
        elif structure.sdf_structure != '':
            t = time()
            fname = "{}_{}".format(t, structure.id)

            with open("/tmp/{}.sdf".format(fname), 'w') as out:
                out.write(structure.sdf_structure)
            a = system("obabel /tmp/{}.sdf -O /tmp/{}.xyz".format(fname, fname), force_local=True)

            with open("/tmp/{}.xyz".format(fname)) as f:
                lines = f.readlines()
            structure.xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))
            structure.save()
            return 0
        elif structure.mol2_structure != '':
            t = time()
            fname = "{}_{}".format(t, structure.id)

            with open("/tmp/{}.mol2".format(fname), 'w') as out:
                out.write(structure.mol2_structure.replace('&lt;', '<').replace('&gt;', '>'))
            a = system("obabel /tmp/{}.mol2 -O /tmp/{}.xyz".format(fname, fname), force_local=True)

            with open("/tmp/{}.xyz".format(fname)) as f:
                lines = f.readlines()
            structure.xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))
            structure.save()
            return 0

        else:
            print("Unimplemented")
            return -1
    else:
        return 0


def launch_xtb_calc(in_file, calc, files):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    folder = '/'.join(in_file.split('/')[:-1])

    xtb = XtbCalculation(calc)
    calc.input_file = xtb.command
    calc.save()

    if xtb.option_file != "":
        with open(os.path.join(local_folder, "input"), 'w') as out:
            out.write(xtb.option_file)

    os.chdir(local_folder)

    if not calc.local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/in.xyz".format(local_folder), os.path.join(folder, "in.xyz"), conn, lock)
        if xtb.option_file != "":
            sftp_put("{}/input".format(local_folder), os.path.join(folder, "input"), conn, lock)

        ret = system(xtb.command, 'calc.out', software='xtb', calc_id=calc.id)
    else:
        os.chdir(local_folder)
        ret = system(xtb.command, 'calc.out', software='xtb', calc_id=calc.id)

    if ret != 0:
        return ret

    if not calc.local:
        for f in files:
            a = sftp_get("{}/{}".format(folder, f), os.path.join(CALCUS_SCR_HOME, str(calc.id), f), conn, lock)
            if a == -1:
                return -1
        a = sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)
        if a != -1:
            return -1

    for f in files:
        if not os.path.isfile("{}/{}".format(local_folder, f)):
            return -1

    '''
    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        for line in lines:
            if line.find("[WARNING] Runtime exception occurred") != -1:
                return 1
    '''
    #Frequency calculations on unoptimized geometries give an error

    return 0


def xtb_opt(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_xtb_calc(in_file, calc, ['calc.out', 'xtbopt.xyz'])

    if ret != 0:
        return ret

    with open("{}/xtbopt.xyz".format(local_folder)) as f:
        lines = f.readlines()

    xyz_structure = clean_xyz(''.join(lines))

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=1)
    prop = get_or_create(calc.parameters, s)
    prop.homo_lumo_gap = hl_gap
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()
    return 0

def xtb_mep(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    with open(os.path.join(local_folder, 'struct2.xyz'), 'w') as out:
        out.write(calc.aux_structure.xyz_structure)

    ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc_MEP_trj.xyz'])

    if ret != 0:
        return ret

    with open("{}/calc_MEP_trj.xyz".format(local_folder)) as f:
        lines = f.readlines()

    num_atoms = lines[0]
    inds = []
    ind = 0
    while ind < len(lines)-1:
        if lines[ind] == num_atoms:
            inds.append(ind)
        ind += 1
    inds.append(len(lines))

    min_E = 0
    for metaind, mol in enumerate(inds[:-1]):
        sline = lines[inds[metaind]+1].strip().split()
        E = float(sline[-1])
        #E = float(lines[inds[metaind]+1].split()[2])
        struct = ''.join([i.strip() + '\n' for i in lines[inds[metaind]:inds[metaind+1]]])

        r = Structure.objects.create(number=metaind+1, degeneracy=1)
        prop = get_or_create(calc.parameters, r)
        prop.energy = E
        prop.geom = True
        prop.save()
        r.xyz_structure = clean_xyz(struct)
        r.save()
        if E < min_E:
            min_E = E

        calc.result_ensemble.structure_set.add(r)

    return 0

def xtb_sp(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_xtb_calc(in_file, calc, ['calc.out'])

    if ret != 0:
        return ret

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-2].split()[3])

    prop = get_or_create(calc.parameters, calc.structure)
    prop.homo_lumo_gap = hl_gap
    prop.energy = E
    prop.save()
    return 0

def get_or_create(params, struct):
    for p in struct.properties.all():
        if p.parameters == params:
            return p
    return Property.objects.create(parameters=params, parent_structure=struct)

def xtb_ts(in_file, calc):

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc.xyz'])

    if ret != 0:
        return ret

    with open(os.path.join(local_folder, "calc.xyz")) as f:
        lines = f.readlines()

    with open(os.path.join(local_folder, "calc.out")) as f:
        olines= f.readlines()
        ind = len(olines)-1
        while olines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(olines[ind].split()[4])

        while olines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(olines[ind].split()[3])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=clean_xyz(''.join(lines)), number=calc.structure.number, degeneracy=calc.structure.degeneracy)
    prop = get_or_create(calc.parameters, s)
    prop.homo_lumo_gap = hl_gap
    prop.energy = E
    prop.geom = True

    s.xyz_structure = '\n'.join([i.strip() for i in lines])

    s.save()
    prop.save()
    return 0


def xtb_scan(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    preparse = XtbCalculation(calc)

    if preparse.has_scan:
        ret = launch_xtb_calc(in_file, calc, ['calc.out', 'xtbscan.log'])
    else:
        ret = launch_xtb_calc(in_file, calc, ['calc.out', 'xtbopt.xyz'])

    if ret != 0:
        return ret

    if preparse.has_scan:
        if not os.path.isfile("{}/xtbscan.log".format(local_folder)):
            return 1

        with open(os.path.join(local_folder, 'xtbscan.log')) as f:
            lines = f.readlines()
            num_atoms = lines[0]
            inds = []
            ind = 0
            while ind < len(lines)-1:
                if lines[ind] == num_atoms:
                    inds.append(ind)
                ind += 1
            inds.append(len(lines))

            min_E = 0
            for metaind, mol in enumerate(inds[:-1]):
                sline = lines[inds[metaind]+1].strip().split()
                en_index = sline.index('energy:')
                E = float(sline[en_index+1])
                struct = ''.join([i.strip() + '\n' for i in lines[inds[metaind]:inds[metaind+1]]])

                r = Structure.objects.create(number=metaind+1, degeneracy=1)
                prop = get_or_create(calc.parameters, r)
                prop.energy = E
                prop.geom = True
                prop.save()
                r.xyz_structure = clean_xyz(struct)
                r.save()
                if E < min_E:
                    min_E = E

                calc.result_ensemble.structure_set.add(r)
    else:
        if not os.path.isfile("{}/xtbopt.xyz".format(local_folder)):
            return 1

        with open(os.path.join(local_folder, 'xtbopt.xyz')) as f:
            lines = f.readlines()
            r = Structure.objects.create(number=calc.structure.number)
            r.xyz_structure = clean_xyz(''.join(lines))

        with open(os.path.join(local_folder, "calc.out")) as f:
            lines = f.readlines()
            ind = len(lines)-1

            while lines[ind].find("HOMO-LUMO GAP") == -1:
                ind -= 1
            hl_gap = float(lines[ind].split()[3])
            E = float(lines[ind-2].split()[3])
            prop = get_or_create(calc.parameters, r)
            prop.energy = E
            prop.homo_lumo_gap = hl_gap

            r.homo_lumo_gap = hl_gap
            r.save()
            prop.save()
            calc.result_ensemble.structure_set.add(r)
            calc.result_ensemble.save()

    return 0

def xtb_freq(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_xtb_calc(in_file, calc, ['calc.out', 'vibspectrum', 'g98.out'])

    if ret != 0:
        return ret

    a = save_to_results(os.path.join(local_folder, "vibspectrum"), calc)

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-4].split()[3])
        G = float(lines[ind-2].split()[4])

    vib_file = os.path.join(local_folder, "vibspectrum")

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
        if len(vibs) == len(intensities) and len(intensities) > 0:
            x = np.arange(500, 4000, 1)#Wave number in cm^-1
            spectrum = plot_vibs(x, zip(vibs, intensities))
            with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "IR.csv"), 'w') as out:
                out.write("Wavenumber,Intensity\n")
                intensities = 1000*np.array(intensities)/max(intensities)
                for _x, i in sorted((zip(list(x), spectrum)), reverse=True):
                    out.write("-{:.1f},{:.5f}\n".format(_x, i))

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = E
    prop.free_energy = G
    prop.freq = calc.id
    prop.save()

    lines = [i +'\n' for i in calc.structure.xyz_structure.split('\n')]
    num_atoms = int(lines[0].strip())
    lines = lines[2:]
    hess = []
    struct = []

    for line in lines:
        if line.strip() != '':
            a, x, y, z = line.strip().split()
            struct.append([a, float(x), float(y), float(z)])

    with open(os.path.join(local_folder, "g98.out")) as f:
        lines = f.readlines()
        ind = 0
        while lines[ind].find("Atom AN") == -1:
            ind += 1
        ind += 1

        vibs = []
        while ind < len(lines) - 1:

            vib = []
            sline = lines[ind].split()
            num_vibs = int((len(sline)-2)/3)
            for i in range(num_vibs):
                vib.append([])
            while ind < len(lines) and len(lines[ind].split()) > 3:
                sline = lines[ind].split()
                n = sline[0].strip()
                Z = sline[1].strip()
                for i in range(num_vibs):
                    x, y, z = sline[2+3*i:5+3*i]
                    vib[i].append([x, y, z])
                ind += 1
            for i in range(num_vibs):
                vibs.append(vib[i])
            while ind < len(lines)-1 and lines[ind].find("Atom AN") == -1:
                ind += 1
            ind += 1

        for ind in range(len(vibs)):
            with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "freq_{}.xyz".format(ind)), 'w') as out:
                out.write("{}\n".format(num_atoms))
                assert len(struct) == num_atoms
                out.write("CalcUS\n")
                for ind2, (a, x, y, z) in enumerate(struct):
                    out.write("{} {:.4f} {:.4f} {:.4f} {} {} {}\n".format(a, x, y, z, *vibs[ind][ind2]))

    return 0

def crest(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_xtb_calc(in_file, calc, ['calc.out', 'crest_conformers.xyz'])

    if ret != 0:
        return ret

    with open(os.path.join(local_folder, "calc.out")) as f:
        lines = f.readlines()
        ind = len(lines) - 1

        while lines[ind].find("total number unique points considered further") == -1:
            ind -= 1

        weighted_energy = 0.0
        ind += 1
        while lines[ind].find("T /K") == -1:
            sline = lines[ind].strip().split()
            if len(sline) == 8:
                energy = float(sline[2])
                weight = float(sline[4])
                number = int(sline[5])
                degeneracy = int(sline[6])
                weighted_energy += energy*weight
                r = Structure.objects.create(number=number, degeneracy=degeneracy)
                prop = get_or_create(calc.parameters, r)
                prop.energy = energy
                prop.geom = True

                r.save()
                prop.save()
                calc.result_ensemble.structure_set.add(r)
            ind += 1
        calc.result_ensemble.save()

    with open(os.path.join(local_folder, 'crest_conformers.xyz')) as f:
        lines = f.readlines()
        num_atoms = lines[0]
        inds = []
        ind = 0
        while ind < len(lines)-1:
            if lines[ind] == num_atoms:
                inds.append(ind)
            ind += 1
        inds.append(len(lines))

        assert len(inds)-1 == len(calc.result_ensemble.structure_set.all())
        for metaind, mol in enumerate(inds[:-1]):
            E = float(lines[inds[metaind]+1].strip())
            raw_lines = lines[inds[metaind]:inds[metaind+1]]
            clean_lines = raw_lines[:2]

            for l in raw_lines[2:]:
                clean_lines.append(clean_struct_line(l))

            struct = clean_xyz(''.join([i.strip() + '\n' for i in clean_lines]))
            r = calc.result_ensemble.structure_set.get(number=metaind+1)
            r.xyz_structure = struct
            r.save()

    return 0

def clean_struct_line(line):
    a, x, y, z = line.split()
    return "{} {} {} {}\n".format(LOWERCASE_ATOMIC_SYMBOLS[a.lower()], x, y, z)

def launch_orca_calc(in_file, calc, files):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    folder = '/'.join(in_file.split('/')[:-1])

    orca = OrcaCalculation(calc)
    calc.input_file = orca.input_file
    calc.save()

    with open(os.path.join(local_folder, 'calc.inp'), 'w') as out:
        out.write(orca.input_file)

    if not calc.local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/calc.inp".format(local_folder), os.path.join(folder, "calc.inp"), conn, lock)
        if calc.step.name == "Minimum Energy Path":
            sftp_put("{}/struct2.xyz".format(local_folder), os.path.join(folder, "struct2.xyz"), conn, lock)

        ret = system("$EBROOTORCA/orca calc.inp", 'calc.out', software="ORCA", calc_id=calc.id)
    else:
        os.chdir(local_folder)
        ret = system("{}/orca calc.inp".format(EBROOTORCA), 'calc.out', software="ORCA", calc_id=calc.id)

    if ret != 0:
        return ret

    if not calc.local:
        for f in files:
            a = sftp_get("{}/{}".format(folder, f), os.path.join(CALCUS_SCR_HOME, str(calc.id), f), conn, lock)
            if a == -1:
                return -1
        if calc.parameters.software == 'xtb':
            a = sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)
            if a != -1:
                return -1

    for f in files:
        if not os.path.isfile("{}/{}".format(local_folder, f)):
            return -1


    return 0

def orca_mo_gen(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out', 'in-HOMO.cube', 'in-LUMO.cube', 'in-LUMOA.cube', 'in-LUMOB.cube'])

    if ret != 0:
        return ret

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    save_to_results("{}/in-HOMO.cube".format(local_folder), calc)
    save_to_results("{}/in-LUMO.cube".format(local_folder), calc)
    save_to_results("{}/in-LUMOA.cube".format(local_folder), calc)
    save_to_results("{}/in-LUMOB.cube".format(local_folder), calc)

    prop = get_or_create(calc.parameters, calc.structure)
    prop.mo = calc.id
    prop.energy = E
    prop.save()

    return 0

def orca_opt(in_file, calc):
    lines = [i + '\n' for i in clean_xyz(calc.structure.xyz_structure).split('\n')[2:] if i != '' ]

    if len(lines) == 1:#Single atom
        s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=calc.structure.xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
        s.save()
        calc.structure = s
        calc.step = BasicStep.objects.get(name="Single-Point Energy")
        calc.save()
        return orca_sp(in_file, calc)

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc.xyz'])

    if ret != 0:
        return ret

    with open("{}/calc.xyz".format(local_folder)) as f:
        lines = f.readlines()

    xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    return 0

def orca_sp(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out'])

    if ret != 0:
        return ret

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = E
    prop.save()

    return 0

def orca_ts(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc.xyz'])

    if ret != 0:
        return ret

    with open("{}/calc.xyz".format(local_folder)) as f:
        lines = f.readlines()
    xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))
    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    return 0

def orca_freq(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out'])

    if ret != 0:
        return ret

    with open("{}/calc.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

    while lines[ind].find("Final Gibbs free energy") == -1:
        ind -= 1

    G = float(lines[ind].split()[5])

    while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
        ind -= 1

    E = float(lines[ind].split()[4])

    while lines[ind].find("IR SPECTRUM") == -1 and ind > 0:
        ind += 1

    assert ind > 0

    ind += 5

    nums = []
    vibs = []
    intensities = []

    while lines[ind].strip() != "":
        sline = lines[ind].strip().split()
        num = sline[0].replace(':', '')
        nums.append(num)

        vibs.append(float(sline[1]))
        intensities.append(float(sline[2]))

        ind += 1

    with open("{}/orcaspectrum".format(os.path.join(CALCUS_RESULTS_HOME, str(calc.id))), 'w') as out:
        for vib in vibs:
            out.write("{}\n".format(vib))

    x = np.arange(500, 4000, 1)#Wave number in cm^-1
    spectrum = plot_vibs(x, zip(vibs, intensities))

    with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "IR.csv"), 'w') as out:
        out.write("Wavenumber,Intensity\n")
        intensities = 1000*np.array(intensities)/max(intensities)
        for _x, i in sorted((zip(list(x), spectrum)), reverse=True):
            out.write("-{:.1f},{:.5f}\n".format(_x, i))

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = E
    prop.free_energy = G
    prop.freq = calc.id
    prop.save()

    raw_lines = calc.structure.xyz_structure.split('\n')
    xyz_lines = []
    for line in raw_lines:
        if line.strip() != '':
            xyz_lines.append(line)

    num_atoms = int(xyz_lines[0].strip())
    xyz_lines = xyz_lines[2:]
    struct = []

    for line in xyz_lines:
        if line.strip() != '':
            a, x, y, z = line.strip().split()
            struct.append([a, float(x), float(y), float(z)])

    while lines[ind].find("NORMAL MODES") == -1 and ind > 0:
        ind -= 1

    assert ind > 0

    ind += 7
    start_num = int(nums[0])
    end_num = int(nums[-1])

    vibs = []
    while lines[ind].strip() != "":
        num_line = len(lines[ind].strip().split())
        ind += 1

        vib = []
        for i in range(num_line):
            vib.append([])

        for i in range(end_num+1):
            sline = lines[ind].split()
            for i in range(num_line):
                coord = float(sline[1+i])
                vib[i].append(coord)
            ind += 1

        def is_all_null(arr):
            for el in arr:
                if float(el) != 0:
                    return False
            return True

        for v in vib:
            if not is_all_null(v):
                vibs += [v]

    for ind in range(len(vibs)):
        with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "freq_{}.xyz".format(ind)), 'w') as out:
            out.write("{}\n".format(num_atoms))
            assert len(struct) == num_atoms
            out.write("CalcUS\n")
            for ind2, (a, x, y, z) in enumerate(struct):
                out.write("{} {:.4f} {:.4f} {:.4f} {} {} {}\n".format(a, x, y, z, *vibs[ind][3*ind2:3*ind2+3]))

    return 0

def orca_scan(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    preparse = OrcaCalculation(calc)
    if preparse.has_scan:
        ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc.relaxscanact.dat', 'calc.allxyz'])
    else:
        ret = launch_orca_calc(in_file, calc, ['calc.out', 'calc.xyz'])

    if ret != 0:
        return ret

    if preparse.has_scan:
        energies = []
        with open(os.path.join(local_folder, 'calc.relaxscanact.dat')) as f:
            lines = f.readlines()
            for line in lines:
                energies.append(float(line.split()[1]))
        with open(os.path.join(local_folder, 'calc.allxyz')) as f:
            lines = f.readlines()
            num_atoms = lines[0]
            inds = []
            ind = 0
            while ind < len(lines)-1:
                if lines[ind] == num_atoms:
                    inds.append(ind)
                ind += 1
            inds.append(len(lines))

            min_E = 0
            for metaind, mol in enumerate(inds[:-1]):
                E = energies[metaind]
                struct = clean_xyz(''.join([i.strip() + '\n' for i in lines[inds[metaind]:inds[metaind+1]-1]]))

                r = Structure.objects.create(number=metaind+1, degeneracy=1)
                prop = get_or_create(calc.parameters, r)
                prop.energy = E
                prop.geom = True
                prop.save()
                r.xyz_structure = struct
                r.save()
                if E < min_E:
                    min_E = E

                calc.result_ensemble.structure_set.add(r)
    else:
        with open(os.path.join(local_folder, 'calc.xyz')) as f:
            lines = f.readlines()
            r = Structure.objects.create(number=calc.structure.number)
            r.xyz_structure = clean_xyz(''.join([i.strip() + '\n' for i in lines]))

        with open(os.path.join(local_folder, "calc.out")) as f:
            lines = f.readlines()
            ind = len(lines)-1
            while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
                ind -= 1
            E = float(lines[ind].split()[4])

            prop = get_or_create(calc.parameters, r)
            prop.energy = E
            r.save()
            prop.save()
            calc.result_ensemble.structure_set.add(r)
            calc.result_ensemble.save()

    return 0

def orca_nmr(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_orca_calc(in_file, calc, ['calc.out'])

    if ret != 0:
        return ret

    with open(os.path.join(local_folder, 'calc.out')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("CHEMICAL SHIELDING SUMMARY (ppm)") == -1:
        ind -= 1

    nmr = ""
    ind += 6
    while lines[ind].strip() != "":
        n, a, iso, an = lines[ind].strip().split()
        nmr += "{} {} {}\n".format(int(n)+1, a, iso)
        ind += 1

    prop = get_or_create(calc.parameters, calc.structure)
    prop.simple_nmr = nmr

    while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
        ind -= 1
    E = float(lines[ind].split()[4])
    prop.energy = E
    prop.save()
    return 0

def enso(in_file, calc):

    if solvent != "Vacuum":
        solvent_add = '-solv {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    a = system("enso.py {} --charge {}".format(solvent_add, calc.parameters.charge), 'enso_pre.out', calc_id=calc.id)

    if a != 0:
        return a, 'e'

    a = system("enso.py -run", 'enso.out', calc_id=calc.id)

    return a, calc.ensemble

def anmr(in_file, calc):
    a = system("anmr", 'anmr.out', calc_id=calc.id)

    if a != 0:
        return a, 'e'

    folder = '/'.join(in_file.split('/')[:-1])

    with open("{}/anmr.dat".format(folder)) as f:
        lines = f.readlines()
        with open("{}/nmr.csv".format(os.path.join(CALCUS_RESULTS_HOME, str(calc.id))), 'w') as out:
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

    return 0, calc.ensemble

def save_to_results(f, calc_obj, multiple=False, out_name=""):
    s = f.split('.')
    fname = f.split('/')[-1]
    if out_name == "":
        out_name = fname
    if len(s) == 2:
        name, ext = s
        if ext == 'xyz':
            if multiple:
                a = system("babel -ixyz {}/{} -oxyz {}/conf.xyz -m".format(os.path.join(CALCUS_SCR_HOME, str(calc_obj.id)), f, os.path.join(CALCUS_RESULTS_HOME, str(calc_obj.id))), force_local=True)
            else:
                copyfile(os.path.join(CALCUS_SCR_HOME, str(calc_obj.id), fname), os.path.join(CALCUS_RESULTS_HOME, str(calc_obj.id), out_name))
        else:
            copyfile(f, os.path.join(CALCUS_RESULTS_HOME, str(calc_obj.id), out_name))
    elif len(s) == 1:
        name = s
        copyfile(f, os.path.join(CALCUS_RESULTS_HOME, str(calc_obj.id), out_name))
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


def xtb_stda(in_file, calc):

    ww = []
    TT = []
    PP = []

    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    os.chdir(local_folder)
    ret1 = system("xtb4stda {} -chrg {} {}".format(in_file, calc.parameters.charge, solvent_add), 'calc.out', calc_id=calc.id)

    if ret1 != 0:
        return ret1

    ret2 = system("stda -xtb -e 12".format(in_file, calc.parameters.charge, solvent_add), 'calc2.out', calc_id=calc.id)

    if ret2 != 0:
        return ret2

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        a = sftp_get("{}/tda.dat".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "tda.dat"), conn, lock)
        b = sftp_get("{}/calc.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc.out"), conn, lock)
        c = sftp_get("{}/calc2.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc2.out"), conn, lock)

        if a == -1 or b == -1 or c == -1:
            return -1

    f_x = np.arange(120.0, 1200.0, 1.0)

    if not os.path.isfile("{}/tda.dat".format(local_folder)):
        return 1

    with open("{}/tda.dat".format(local_folder)) as f:
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


    with open("{}/uvvis.csv".format(os.path.join(CALCUS_RESULTS_HOME, str(calc.id))), 'w') as out:
        out.write("Wavelength (nm), Absorbance\n")
        for ind, x in enumerate(f_x):
            out.write("{},{:.8f}\n".format(x, yy[ind]))

    prop = get_or_create(calc.parameters, calc.structure)
    prop.uvvis = calc.id
    prop.save()

    return 0

def launch_gaussian_calc(in_file, calc, files):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    folder = '/'.join(in_file.split('/')[:-1])

    gaussian = GaussianCalculation(calc)
    calc.input_file = gaussian.input_file
    calc.save()

    with open(os.path.join(local_folder, 'calc.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not calc.local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/calc.com".format(local_folder), os.path.join(folder, "calc.com"), conn, lock)
        ret = system("g16 calc.com", software="Gaussian", calc_id=calc.id)
    else:
        os.chdir(local_folder)
        ret = system("g16 calc.com", software="Gaussian", calc_id=calc.id)

    if ret != 0:
        return ret

    if not calc.local:
        for f in files:
            a = sftp_get("{}/{}".format(folder, f), os.path.join(local_folder, f), conn, lock)
            if a == -1:
                return -1

    for f in files:
        if not os.path.isfile("{}/{}".format(local_folder, f)):
            return -1

    with open(os.path.join(local_folder, 'calc.log')) as f:
        lines = f.readlines()
        if lines[-1].find("Normal termination") == -1:
            return -1

    return 0

def parse_gaussian_charges(calc, s):
    parse_default_gaussian_charges(calc, s)

    for spec in calc.parameters.specifications.split(';'):
        if spec.strip() == '':
            continue
        if spec.find('(') != -1:
            key, option = spec.split('(')
            option = option.replace(')', '')
            if key == 'pop':
                if option == 'nbo' or option == 'npa':
                    parse_NPA_gaussian_charges(calc, s)
                elif option == 'hirshfeld':
                    parse_Hirshfeld_gaussian_charges(calc, s)
                elif option == 'esp':
                    parse_ESP_gaussian_charges(calc, s)
                elif option == 'hly':
                    parse_HLY_gaussian_charges(calc, s)

def parse_default_gaussian_charges(calc, s):
    prop = get_or_create(calc.parameters, s)

    with open(os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    try:
        while lines[ind].find("Mulliken charges:") == -1:
            ind -= 1
    except IndexError:#Monoatomic systems may not have charges
        return
    ind += 2
    charges = []
    while lines[ind].find("Sum of Mulliken charges") == -1:
        n, a, chrg = lines[ind].split()
        charges.append("{:.2f}".format(float(chrg)))
        ind += 1

    prop.charges += "Mulliken:{};".format(','.join(charges))

    try:
        while lines[ind].find("APT charges:") == -1:
            ind += 1
    except IndexError:
        pass
    else:
        ind += 2
        charges = []
        while lines[ind].find("Sum of APT charges") == -1:
            n, a, chrg = lines[ind].split()
            charges.append("{:.2f}".format(float(chrg)))
            ind += 1
        prop.charges += "APT:{};".format(','.join(charges))

    prop.save()

def parse_ESP_gaussian_charges(calc, s):
    prop = get_or_create(calc.parameters, s)

    with open(os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("ESP charges:") == -1:
        ind -= 1
    ind += 2
    charges = []
    while lines[ind].find("Sum of ESP charges") == -1:
        a, n, chrg, *_ = lines[ind].split()
        charges.append("{:.2f}".format(float(chrg)))
        ind += 1

    prop.charges += "ESP:{};".format(','.join(charges))
    prop.save()

def parse_HLY_gaussian_charges(calc, s):
    prop = get_or_create(calc.parameters, s)

    with open(os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("Generate Potential Derived Charges using the Hu-Lu-Yang model:") == -1:
        ind -= 1

    while lines[ind].find("ESP charges:") == -1:
        ind += 1

    ind += 2
    charges = []
    while lines[ind].find("Sum of ESP charges") == -1:
        a, n, chrg, *_ = lines[ind].split()
        charges.append("{:.2f}".format(float(chrg)))
        ind += 1

    prop.charges += "HLY:{};".format(','.join(charges))
    prop.save()


def parse_NPA_gaussian_charges(calc, s):
    prop = get_or_create(calc.parameters, s)

    with open(os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("Summary of Natural Population Analysis:") == -1:
        ind -= 1
    ind += 6
    charges = []
    while lines[ind].find("===========") == -1:
        a, n, chrg, *_ = lines[ind].split()
        charges.append("{:.2f}".format(float(chrg)))
        ind += 1

    prop.charges += "NBO:{};".format(','.join(charges))
    prop.save()

def parse_Hirshfeld_gaussian_charges(calc, s):
    prop = get_or_create(calc.parameters, s)

    with open(os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("Hirshfeld charges, spin densities, dipoles, and CM5 charges") == -1:
        ind -= 1
    ind += 2
    charges_hirshfeld = []
    charges_CM5 = []
    while lines[ind].find("Tot") == -1:
        a, n, hirshfeld, _, _, _, _, CM5 = lines[ind].split()
        charges_hirshfeld.append("{:.2f}".format(float(hirshfeld)))
        charges_CM5.append("{:.2f}".format(float(CM5)))
        ind += 1

    prop.charges += "Hirshfeld:{};".format(','.join(charges_hirshfeld))
    prop.charges += "CM5:{};".format(','.join(charges_CM5))
    prop.save()


def gaussian_sp(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    if ret != 0:
        return ret

    with open("{}/calc.log".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    parse_gaussian_charges(calc, calc.structure)

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = E
    prop.save()

    return 0

def gaussian_opt(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    if ret != 0:
        return ret

    with open("{}/calc.log".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])
        while lines[ind].find("Center     Atomic      Atomic             Coordinates (Angstroms)") == -1:
            ind += 1
        ind += 3

        xyz = []
        while lines[ind].find("----") == -1:
            n, a, t, x, y, z = lines[ind].strip().split()
            xyz.append([ATOMIC_SYMBOL[int(a)], x, y, z])
            ind += 1

        xyz_structure = "{}\nCalcUS\n".format(len(xyz))
        for el in xyz:
            xyz_structure += "{} {} {} {}\n".format(*el)

        xyz_structure = clean_xyz(xyz_structure)


    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    parse_gaussian_charges(calc, s)
    return 0

def gaussian_freq(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    if ret != 0:
        return ret

    with open("{}/calc.log".format(local_folder)) as f:
        outlines = f.readlines()
        ind = len(outlines)-1

    while outlines[ind].find('Zero-point correction') == -1:
        ind -= 1

    ZPE = outlines[ind].split()[-2]
    H = outlines[ind+2].split()[-1]
    G = outlines[ind+3].split()[-1]

    while outlines[ind].find('SCF Done') == -1:
        ind -= 1

    SCF = outlines[ind].split()[4]

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = SCF
    prop.free_energy = float(0.0030119 + float(G) + float(SCF))
    prop.freq = calc.id
    prop.save()

    try:
        while outlines[ind].find("Standard orientation:") == -1:
            ind -= 1
        ind += 5

    except IndexError:#"Standard orientation" is not in all Gaussian output files, apparently
        ind = 0

        raw_lines = calc.structure.xyz_structure.split('\n')
        xyz_lines = []
        for line in raw_lines:
            if line.strip() != '':
                xyz_lines.append(line)

        num_atoms = int(xyz_lines[0].strip())
        xyz_lines = xyz_lines[2:]
        struct = []
        for line in xyz_lines:
            if line.strip() != '':
                a, x, y, z = line.strip().split()
                struct.append([a, float(x), float(y), float(z)])
    else:
        struct = []
        while outlines[ind].find("-----------") == -1:
            _, n, _, x, y, z = outlines[ind].split()
            a = ATOMIC_SYMBOL[int(n)]
            struct.append([a, float(x), float(y), float(z)])
            ind += 1
        num_atoms = len(struct)

    while outlines[ind].find("and normal coordinates:") == -1:
        ind += 1
    ind += 3

    if outlines[ind].find("Thermochemistry") != -1:#No vibration
        return 0

    vibs = []
    wavenumbers = []
    intensities = []
    while ind < len(outlines) - 1:
        vib = []
        intensity = []
        sline = outlines[ind].split()
        num_vibs = int((len(sline)-2))

        for i in range(num_vibs):
            wavenumbers.append(float(sline[2+i]))
            intensities.append(float(outlines[ind+3].split()[3+i]))
            vib.append([])

        while outlines[ind].find("Atom  AN") == -1:
            ind += 1

        ind += 1

        while ind < len(outlines) and len(outlines[ind].split()) > 3:
            sline = outlines[ind].split()
            n = sline[0].strip()
            Z = sline[1].strip()
            for i in range(num_vibs):
                x, y, z = sline[2+3*i:5+3*i]
                vib[i].append([x, y, z])
            ind += 1
        for i in range(num_vibs):
            vibs.append(vib[i])
        while ind < len(outlines)-1 and outlines[ind].find("Frequencies --") == -1:
            ind += 1

    for ind in range(len(vibs)):
        with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "freq_{}.xyz".format(ind)), 'w') as out:
            out.write("{}\n".format(num_atoms))
            #assert len(struct) == num_atoms
            out.write("CalcUS\n")
            for ind2, (a, x, y, z) in enumerate(struct):
                out.write("{} {:.4f} {:.4f} {:.4f} {} {} {}\n".format(a, x, y, z, *vibs[ind][ind2]))

    with open("{}/orcaspectrum".format(os.path.join(CALCUS_RESULTS_HOME, str(calc.id))), 'w') as out:
        for vib in wavenumbers:
            out.write("{:.1f}\n".format(vib))

    x = np.arange(500, 4000, 1)#Wave number in cm^-1
    spectrum = plot_vibs(x, zip(wavenumbers, intensities))

    with open(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "IR.csv"), 'w') as out:
        out.write("Wavenumber,Intensity\n")
        intensities = 1000*np.array(intensities)/max(intensities)
        for _x, i in sorted((zip(list(x), spectrum)), reverse=True):
            out.write("-{:.1f},{:.5f}\n".format(_x, i))

    parse_gaussian_charges(calc, calc.structure)
    return 0

def gaussian_ts(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    if ret != 0:
        return ret

    with open("{}/calc.log".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])
        while lines[ind].find("Center     Atomic      Atomic             Coordinates (Angstroms)") == -1:
            ind += 1
        ind += 3

        xyz = []
        while lines[ind].find("----") == -1:
            n, a, t, x, y, z = lines[ind].strip().split()
            xyz.append([ATOMIC_SYMBOL[int(a)], x, y, z])
            ind += 1

        xyz_structure = "{}\nCalcUS\n".format(len(xyz))
        for el in xyz:
            xyz_structure += "{} {} {} {}\n".format(*el)

        xyz_structure = clean_xyz(xyz_structure)

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    parse_gaussian_charges(calc, s)
    return 0

def gaussian_scan(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    preparse = GaussianCalculation(calc)
    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    failed = False
    if ret != 0:
        if preparse.has_scan:
            failed = True
        else:
            return ret

    with open(os.path.join(local_folder, 'calc.log')) as f:
        lines = f.readlines()

    if preparse.has_scan:
        s_ind = 1
        ind = 0
        done = False
        while not done:
            while ind < len(lines) - 1 and lines[ind].find("Optimization completed.") == -1:
                ind += 1

            if ind == len(lines) - 1:
                done = True
                break

            ind2 = ind

            while lines[ind].find("Input orientation:") == -1 and lines[ind].find("Standard orientation:") == -1:
                ind += 1
            ind += 5

            xyz = []
            while lines[ind].find("----") == -1:
                n, a, t, x, y, z = lines[ind].strip().split()
                xyz.append([ATOMIC_SYMBOL[int(a)], x, y, z])
                ind += 1

            xyz_structure = "{}\nCalcUS\n".format(len(xyz))
            for el in xyz:
                xyz_structure += "{} {} {} {}\n".format(*el)

            xyz_structure = clean_xyz(xyz_structure)

            while lines[ind2].find("SCF Done") == -1:
                ind2 -= 1

            E = float(lines[ind2].split()[4])

            s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=s_ind, degeneracy=1)
            prop = get_or_create(calc.parameters, s)
            prop.energy = E
            prop.geom = True
            s.save()
            prop.save()

            s_ind += 1
    else:
        ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])
        while lines[ind].find("Center     Atomic      Atomic             Coordinates (Angstroms)") == -1:
            ind += 1
        ind += 3

        xyz = []
        while lines[ind].find("----") == -1:
            n, a, t, x, y, z = lines[ind].strip().split()
            xyz.append([ATOMIC_SYMBOL[int(a)], x, y, z])
            ind += 1

        xyz_structure = "{}\nCalcUS\n".format(len(xyz))
        for el in xyz:
            xyz_structure += "{} {} {} {}\n".format(*el)

        xyz_structure = clean_xyz(xyz_structure)

        s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
        prop = get_or_create(calc.parameters, s)
        prop.energy = E
        prop.geom = True
        s.save()
        prop.save()

    parse_gaussian_charges(calc, calc.result_ensemble.structure_set.latest('id'))

    if failed:
        return -1
    else:
        return 0

def gaussian_nmr(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    ret = launch_gaussian_calc(in_file, calc, ['calc.log'])

    if ret != 0:
        return ret

    with open(os.path.join(local_folder, 'calc.log')) as f:
        lines = f.readlines()
    ind = len(lines)-1
    while lines[ind].find("SCF GIAO Magnetic shielding tensor (ppm):") == -1:
        ind -= 1

    nmr = ""
    ind += 1
    while lines[ind].find("End of Minotr") == -1:
        sline = lines[ind].strip().split()
        nmr += "{} {} {}\n".format(int(sline[0]), sline[1], sline[4])
        ind += 5

    while lines[ind].find("SCF Done") == -1:
        ind -= 1
    E = float(lines[ind].split()[4])

    prop = get_or_create(calc.parameters, calc.structure)
    prop.simple_nmr = nmr
    prop.energy = E
    prop.save()

    parse_gaussian_charges(calc, calc.structure)
    return 0

def dist(a, b):
    return math.sqrt((a[1] - b[1])**2 + (a[2] - b[2])**2 + (a[3] - b[3])**2)

COV_THRESHOLD = 1.1
def find_bonds(xyz):
    bonds = []
    def bond_unique(ind1, ind2):
        for bond in bonds:
            if bond[0] == ind1 and bond[1] == ind2:
                return False
            if bond[0] == ind2 and bond[1] == ind1:
                return False
        return True
    doubles = {'CC': 1.34, 'CN': 1.29, 'CO': 1.20, 'CS': 1.60, 'NC': 1.29, 'OC': 1.20, 'SC': 1.60, 'NN': 1.25,
               'NO': 1.22, 'ON': 1.22, 'SO': 1.44, 'OS': 1.44}
    d_exist = list(doubles.keys())
    for ind1, i in enumerate(xyz):
        for ind2, j in enumerate(xyz):
            if ind1 > ind2:
                d = dist(i, j)
                btype = '{}{}'.format(i[0], j[0])
                cov = (periodictable.elements[ATOMIC_NUMBER[i[0]]].covalent_radius +periodictable.elements[ATOMIC_NUMBER[j[0]]].covalent_radius)
                if d_exist.count(btype):
                    factor = (cov - doubles[btype])
                    b_order = ((cov - d)/factor)+1
                    if b_order > 2.2:
                        bond_type = 3
                    elif b_order > 1.8:
                        bond_type = 2
                    elif b_order > 1.6:
                        bond_type = 4
                    else:
                        bond_type = 1
                else:
                    bond_type = 1
                corr_ratio = d / cov
                if corr_ratio < COV_THRESHOLD and bond_unique(ind1, ind2):
                    #btag = '%1s_%1s' % (self.atoms[i].label, self.atoms[j].label)
                    bonds.append([ind1, ind2, bond_type])
    return bonds


def write_mol(xyz):

    bonds = find_bonds(xyz)
    content = []
    content.append('Molfile\n')
    content.append('  CalcUS\n')
    content.append('empty\n')
    content.append('%3d%3d%3d%3d%3d%3d%3d%3d%3d%6s V2000 \n' % (len(xyz), len(bonds),
                                                                         0, 0, 0, 0, 0, 0, 0, '0999'))
    for atom in xyz:
        content.append('%10.4f%10.4f%10.4f %-3s 0  0  0  0  0  0  0  0  0  0  0  0\n'
                       % (atom[1], atom[2], atom[3], atom[0]))
    for bond in bonds:
        content.append('%3d%3d%3d  0  0  0  0\n' %(1+bond[0], 1+bond[1], bond[2]))
    content.append('M  END\n')
    return content

def gen_fingerprint(structure):
    if structure.xyz_structure == '':
        print("No xyz structure!")
        return -1

    raw_xyz = structure.xyz_structure

    xyz = []
    for line in raw_xyz.split('\n')[2:]:
        if line.strip() != "":
            a, x, y, z = line.strip().split()
            xyz.append([a, float(x), float(y), float(z)])

    mol = write_mol(xyz)
    t = "{}_{}".format(time(), structure.id)
    mol_file = "/tmp/{}.mol".format(t)
    with open(mol_file, 'w') as out:
        for line in mol:
            out.write(line)
    a = os.system("inchi-1 {}".format(mol_file))
    try:
        with open(mol_file + '.txt') as f:
            lines = f.readlines()
        inchi = lines[2][6:]
    except IndexError:
        inchi = str(time())
    return inchi

def analyse_opt(calc_id):
    funcs = {
                "Gaussian": analyse_opt_Gaussian,
                "ORCA": analyse_opt_ORCA,
                "xtb": analyse_opt_xtb,
                }
    calc = Calculation.objects.get(pk=calc_id)

    software = calc.parameters.software

    return funcs[software](calc)

def analyse_opt_ORCA(calc):
    prepath = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    RMSDs = [0]

    if not os.path.isfile(os.path.join(prepath, "calc.out")):
        return

    if not os.path.isfile(os.path.join(prepath, "calc_trj.xyz")):
        return

    with open(os.path.join(prepath, "calc.out")) as f:
        lines = f.readlines()
    ind = 0
    flag = False
    while not flag:
        while lines[ind].find("RMS step") == -1:
            ind += 1
            if ind > len(lines) - 2:
                flag = True
                break
        if not flag:
            rms = float(lines[ind].split()[2])
            RMSDs.append(rms)
            ind += 1

    with open(os.path.join(prepath, "calc_trj.xyz")) as f:
        lines = f.readlines()

    num = int(lines[0])
    nstructs = int(len(lines)/(num+2))

    #assert nstructs == len(RMSDs)

    for i in range(1, nstructs):
        xyz = ''.join(lines[(num+2)*i:(num+2)*(i+1)])
        try:
            f = calc.calculationframe_set.get(number=i)
        except CalculationFrame.DoesNotExist:
            f = CalculationFrame.objects.create(number=i, xyz_structure=xyz, parent_calculation=calc, RMSD=RMSDs[i])
        else:
            f.xyz_structure = xyz
            f.RMSD = RMSDs[i]
        f.save()

def analyse_opt_xtb(calc):
    if calc.status in [2, 3]:
        path = os.path.join(CALCUS_RESULTS_HOME, str(calc.id), 'xtbopt.out')
    else:
        path = os.path.join(CALCUS_SCR_HOME, str(calc.id), 'xtbopt.log')

    if not os.path.isfile(path):
        return

    with open(path) as f:
        lines = f.readlines()

    xyz = ''.join(lines)
    natoms = int(lines[0])
    nn = int(len(lines)/(natoms+2))
    RMSD = "Frame,RMS Displacement\n"
    for n in range(nn):
        xyz = ''.join(lines[(natoms+2)*n:(natoms+2)*(n+1)])
        rms = lines[n*(natoms+2)+1].split()[3]
        try:
            f = calc.calculationframe_set.get(number=n+1)
        except CalculationFrame.DoesNotExist:
            f = CalculationFrame.objects.create(parent_calculation=calc, number=n+1, RMSD=rms, xyz_structure=xyz)
        else:
            f.xyz_structure = xyz

        f.save()
    return


def analyse_opt_Gaussian(calc):
    if calc.status in [2, 3]:
        calc_path = os.path.join(CALCUS_RESULTS_HOME, str(calc.id), 'calc.out')
    elif calc.status == 1:
        calc_path = os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')
    else:
        return None

    if not os.path.isfile(calc_path):
        return

    with open(calc_path) as f:
        lines = f.readlines()

    if not calc.step.creates_ensemble:
        return

    orientation_str = ""
    for line in lines:
        if line.find("Standard orientation") != -1:
            orientation_str = "Standard orientation"
            break

    if orientation_str == "":
        orientation_str = "Input orientation"

    ind = 0
    s_ind = 0
    try:
        while lines[ind].find("Symbolic Z-matrix:") == -1:
            ind += 1
    except IndexError:
        print("Could not parse Gaussian log for calc {}".format(calc.id))
        return
    ind += 2

    start_ind = ind

    while lines[ind].strip() != "":
        ind += 1
    num_atoms = ind - start_ind

    xyz = ""

    while ind < len(lines) - 2:
        while lines[ind].find(orientation_str) == -1 and lines[ind].find("RMS     Displacement") == -1:
            ind += 1
            if ind > len(lines) - 3:
                calc.save()
                return
        if lines[ind].find(orientation_str) != -1:
            s_ind += 1
            xyz += "{}\n\n".format(num_atoms)
            ind += 5
            while lines[ind].find("---------") == -1:
                n, z, T, X, Y, Z = lines[ind].strip().split()
                A = ATOMIC_SYMBOL[int(z)]
                xyz += "{} {} {} {}\n".format(A, X, Y, Z)
                ind += 1
        elif lines[ind].find("RMS     Displacement") != -1:
            rms = float(lines[ind].split()[2])
            try:
                f = calc.calculationframe_set.get(number=s_ind)
            except CalculationFrame.DoesNotExist:
                f = CalculationFrame.objects.create(number=s_ind, xyz_structure=xyz, parent_calculation=calc, RMSD=rms)
            else:
                f.xyz_structure = xyz
            f.save()
            xyz = ""
            ind += 1
        else:
            print("Error")
            calc.save()
            return
    calc.save()

def get_Gaussian_xyz(text):
    lines = text.split('\n')
    ind = len(lines) -1
    while lines[ind].find("Coordinates (Angstroms)") == -1:
        ind -= 1

    ind += 3
    s = []
    while lines[ind].find("----------") == -1:
        if lines[ind].strip() != '':
            _, n, _, x, y, z = lines[ind].split()
            s.append((ATOMIC_SYMBOL[int(n)], x, y, z))
        ind += 1
    xyz = "{}\n\n".format(len(s))
    for l in s:
        xyz += "{} {} {} {}\n".format(*l)
    return clean_xyz(xyz)

def verify_charge_mult(xyz, charge, mult):
    electrons = 0
    for line in xyz.split('\n')[2:]:
        if line.strip() == "":
            continue
        el = line.split()[0]
        electrons += ATOMIC_NUMBER[el]

    electrons -= charge
    odd_e = electrons % 2
    odd_m = mult % 2

    if odd_e == odd_m:
        return -1
    return 0


SPECIAL_FUNCTIONALS = ['HF-3c', 'PBEh-3c']
BASICSTEP_TABLE = {
        'xtb':
            {
                'Geometrical Optimisation': xtb_opt,
                'Conformational Search': crest,
                'Constrained Optimisation': xtb_scan,
                'Frequency Calculation': xtb_freq,
                'TS Optimisation': xtb_ts,
                'UV-Vis Calculation': xtb_stda,
                #'Crest Pre NMR': crest_pre_nmr,
                #'Enso': enso,
                #'Anmr': anmr,
                'Single-Point Energy': xtb_sp,
                'Minimum Energy Path': xtb_mep,
                'Constrained Conformational Search': crest,
            },
        'ORCA':
            {
                'NMR Prediction': orca_nmr,
                'Geometrical Optimisation': orca_opt,
                'TS Optimisation': orca_ts,
                'MO Calculation': orca_mo_gen,
                'Frequency Calculation': orca_freq,
                'Constrained Optimisation': orca_scan,
                'Single-Point Energy': orca_sp,
            },
        'Gaussian':
            {
                'NMR Prediction': gaussian_nmr,
                'Geometrical Optimisation': gaussian_opt,
                'TS Optimisation': gaussian_ts,
                'Frequency Calculation': gaussian_freq,
                'Constrained Optimisation': gaussian_scan,
                'Single-Point Energy': gaussian_sp,
            }

        }

time_dict = {}

def filter(order, input_structures):
    if order.filter == None:
        return input_structures

    structures = []

    if order.filter.type == "By Boltzmann Weight":
        for s in input_structures:
            if s.parent_ensemble.weight(s, order.filter.parameters) > order.filter.value:
                structures.append(s)
    elif order.filter.type == "By Relative Energy":
        for s in input_structures:
            val = s.parent_ensemble.relative_energy(s, order.filter.parameters)
            if order.author.pref_units == 0:
                E = val*HARTREE_FVAL
            elif order.author.pref_units == 1:
                E = val*HARTREE_TO_KCAL_F
            elif order.author.pref_units == 2:
                E = val
            if E < order.filter.value:
                structures.append(s)

    return structures

@app.task(base=AbortableTask)
def dispatcher(drawing, order_id):
    order = CalculationOrder.objects.get(pk=order_id)
    ensemble = order.ensemble

    local = True
    if order.resource is not None:
        local = False

    step = order.step

    mode = "e"#Mode for input structure (Ensemble/Structure)
    input_structures = None
    created_molecule = False
    if order.structure != None:
        mode = "s"
        generate_xyz_structure(drawing, order.structure)
        molecule = order.structure.parent_ensemble.parent_molecule
        if order.project == molecule.project:
            ensemble = order.structure.parent_ensemble
            input_structures = [order.structure]
        else:
            molecule = Molecule.objects.create(name=molecule.name, inchi=molecule.inchi, project=order.project)
            ensemble = Ensemble.objects.create(name=order.structure.parent_ensemble.name, parent_molecule=molecule)
            structure = Structure.objects.create(parent_ensemble=ensemble, xyz_structure=order.structure.xyz_structure, number=1)
            order.structure = structure
            molecule.save()
            ensemble.save()
            structure.save()
            order.save()
            input_structures = [structure]
    elif order.ensemble != None:
        for s in ensemble.structure_set.all():
            if s.xyz_structure == "":
                generate_xyz_structure(drawing, s)

        ensemble.save()

        if ensemble.parent_molecule is None:
            fingerprint = ""
            for s in ensemble.structure_set.all():
                generate_xyz_structure(drawing, s)
                fing = gen_fingerprint(s)
                if fingerprint == "":
                    fingerprint = fing
                else:
                    if fingerprint != fing:#####
                        pass
            try:
                molecule = Molecule.objects.get(inchi=fingerprint, project=order.project)
            except Molecule.DoesNotExist:
                molecule = Molecule.objects.create(name=order.name, inchi=fingerprint, project=order.project)
                created_molecule = True
                molecule.save()
            ensemble.parent_molecule = molecule
            ensemble.save()
            input_structures = ensemble.structure_set.all()
        else:
            if ensemble.parent_molecule.project == order.project:
                molecule = ensemble.parent_molecule
                input_structures = ensemble.structure_set.all()
            else:
                molecule = Molecule.objects.create(name=ensemble.parent_molecule.name, inchi=ensemble.parent_molecule.inchi, project=order.project)
                ensemble = Ensemble.objects.create(name=ensemble.name, parent_molecule=molecule)
                for s in order.ensemble.structure_set.all():
                    _s = Structure.objects.create(parent_ensemble=ensemble, xyz_structure=s.xyz_structure, number=s.number, degeneracy=s.degeneracy)
                    _s.save()
                order.ensemble = ensemble
                order.save()
                ensemble.save()
                molecule.save()
                input_structures = ensemble.structure_set.all()
    elif order.start_calc != None:
        calc = order.start_calc
        fid = order.start_calc_frame
        mode = 'c'
        if calc.status in [2, 3]:
            calc_path = os.path.join(CALCUS_RESULTS_HOME, str(calc.id), 'calc.out')
        else:
            calc_path = os.path.join(CALCUS_SCR_HOME, str(calc.id), 'calc.log')

        molecule = calc.result_ensemble.parent_molecule
        ensemble = Ensemble.objects.create(parent_molecule=molecule, origin=calc.result_ensemble, name="Extracted frame {}".format(fid))
        f = calc.calculationframe_set.get(number=fid)
        s = Structure.objects.create(parent_ensemble=ensemble, xyz_structure=f.xyz_structure, number=order.start_calc.structure.number, degeneracy=1)
        ensemble.save()
        s.save()
        input_structures = [s]
    else:
        print("Invalid calculation order: {}".format(order.id))
        return

    group_order = []
    calculations = []

    input_structures = filter(order, input_structures)
    if step.creates_ensemble:
        if order.name.strip() == "" or created_molecule:
            e = Ensemble.objects.create(name="{} Result".format(order.step.name), origin=ensemble)
        else:
            e = Ensemble.objects.create(name=order.name, origin=ensemble)
        order.result_ensemble = e
        order.save()
        molecule.ensemble_set.add(e)
        molecule.save()
        e.save()

        for s in input_structures:
            c = Calculation.objects.create(structure=s, order=order, date_submitted=timezone.now(), step=step, parameters=order.parameters, result_ensemble=e, constraints=order.constraints, aux_structure=order.aux_structure)
            c.save()
            if local:
                calculations.append(c)
                if not is_test:
                    group_order.append(run_calc.s(c.id).set(queue='comp'))
                else:
                    group_order.append(run_calc.s(c.id))
            else:
                calculations.append(c)
                c.local = False
                c.save()
                cmd = "launch\n{}\n".format(c.id)
                send_cluster_command(cmd)

    else:
        if mode == 'c':
            order.result_ensemble = ensemble
            order.save()
        for s in input_structures:
            c = Calculation.objects.create(structure=s, order=order, date_submitted=timezone.now(), parameters=order.parameters, step=step, constraints=order.constraints, aux_structure=order.aux_structure)
            c.save()
            if local:
                calculations.append(c)
                if not is_test:
                    group_order.append(run_calc.s(c.id).set(queue='comp'))
                else:
                    group_order.append(run_calc.s(c.id))
            else:
                c.local = False
                c.save()

                cmd = "launch\n{}\n".format(c.id)
                send_cluster_command(cmd)

    for task, c in zip(group_order, calculations):
        res = task.apply_async()
        c.task_id = res
        c.save()

@app.task(base=AbortableTask)
def run_calc(calc_id):
    print("Processing calc {}".format(calc_id))
    calc = Calculation.objects.get(pk=calc_id)

    f = BASICSTEP_TABLE[calc.parameters.software][calc.step.name]

    res_dir = os.path.join(CALCUS_RESULTS_HOME, str(calc.id))
    workdir = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    if calc.status == 3:#Already revoked:
        return

    ret = verify_charge_mult(calc.structure.xyz_structure, calc.parameters.charge, calc.parameters.multiplicity)
    if ret != 0:
        calc.error_message = "Impossible charge/multiplicity"
        calc.status = 3
        calc.save()
        return

    if calc.status == 0:
        try:
            os.mkdir(res_dir)
        except OSError:
            print("Directory already exists: {}".format(res_dir))
        try:
            os.mkdir(workdir)
        except OSError:
            print("Directory already exists: {}".format(res_dir))
        in_file = os.path.join(workdir, 'in.xyz')

        with open(in_file, 'w') as out:
            out.write(clean_xyz(calc.structure.xyz_structure))

    if not calc.local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        if calc.status == 0:
            direct_command("mkdir -p {}".format(remote_dir), conn, lock)
            sftp_put(in_file, os.path.join(remote_dir, "in.xyz"), conn, lock)

        in_file = os.path.join(remote_dir, "in.xyz")

    try:
        ret = f(in_file, calc)
    except:
        ret = 1
        traceback.print_exc()

    if ret == 7:#Manually disconnected from cluster
        return

    calc = Calculation.objects.get(pk=calc_id)
    calc.date_finished = timezone.now()
    if ret == -2:
        calc.status = 3
        calc.error_message = "Job cancelled"
        calc.save()
        print("Job {} cancelled".format(calc.id))
        return

    if ret != 0:
        calc.status = 3
        calc.error_message = "Incorrect termination"#TODO: error analysis
        calc.save()
    else:
        calc.status = 2
        calc.save()



    #just calc.out/calc.log?
    for f in glob.glob("{}/*.out".format(workdir)):
        fname = f.split('/')[-1]
        copyfile(f, "{}/{}".format(res_dir, fname))

    for f in glob.glob("{}/*.log".format(workdir)):
        fname = f.split('/')[-1].replace('.log', '.out')
        copyfile(f, "{}/{}".format(res_dir, fname))

    return ret

@app.task
def del_project(proj_id):
    _del_project(proj_id)

@app.task
def del_molecule(mol_id):
    _del_molecule(mol_id)

@app.task
def del_ensemble(ensemble_id):
    _del_ensemble(ensemble_id)

def _del_project(id):
    proj = Project.objects.get(pk=id)
    proj.author = None
    proj.save()
    for m in proj.molecule_set.all():
        _del_molecule(m.id)
    proj.delete()

def _del_molecule(id):
    mol = Molecule.objects.get(pk=id)
    for e in mol.ensemble_set.all():
        _del_ensemble(e.id)
    mol.delete()

def _del_ensemble(id):
    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return

    for s in e.structure_set.all():
        _del_structure(s)

    for c in e.calculation_set.all():
        if c.status == 1 or c.status == 2:
            kill_calc(c)

        c.delete()
        try:
            rmtree(os.path.join(CALCUS_SCR_HOME, str(c.id)))
        except OSError:
            pass
        try:
            rmtree(os.path.join(CALCUS_RESULTS_HOME, str(c.id)))
        except OSError:
            pass
    e.delete()

def _del_structure(s):
    calcs = s.calculation_set.all()
    for c in calcs:
        if c.status == 1 or c.status == 2:
            kill_calc(c)

        c.delete()
        try:
            rmtree(os.path.join(CALCUS_SCR_HOME, str(c.id)))
        except OSError:
            pass
        try:
            rmtree(os.path.join(CALCUS_RESULTS_HOME, str(c.id)))
        except OSError:
            pass

    s.delete()

def send_cluster_command(cmd):
    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    chan = conn.channel()

    chan.queue_declare(queue='cluster')
    chan.basic_publish(exchange='', routing_key='cluster', body=cmd)
    conn.close()

@app.task
def cancel(calc_id):
    print("Cancelling calc {}".format(calc_id))
    calc = Calculation.objects.get(pk=calc_id)
    kill_calc(calc)

def kill_calc(calc):
    if calc.local:
        if calc.task_id != '':
            if calc.status == 1:
                res = AbortableAsyncResult(calc.task_id)
                res.abort()
            else:
                revoke(calc.task_id)
                calc.status = 3
                calc.error_message = "Job cancelled"
                calc.save()
        else:
            print("Cannot cancel calculation without task id")
    else:
        cmd = "kill\n{}\n".format(calc.id)
        send_cluster_command(cmd)
        calc.status = 3
        calc.error_message = "Job cancelled"
        calc.save()


@app.task(name='celery.ping')
def ping():
    return 'pong'

@app.task
def ping_home():
    requests.post("http://minotaurr.org/calcus")

