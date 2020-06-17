from __future__ import absolute_import, unicode_literals

from calcus.celery import app
import string

from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure
from django.utils import timezone

from django.db.utils import IntegrityError
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult

import os
import numpy as np
import decimal
import math
from datetime import datetime
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
from .calculation_helper import *

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False


import traceback
import periodictable

ATOMIC_NUMBER = {}
ATOMIC_SYMBOL = {}
LOWERCASE_ATOMIC_SYMBOLS = {}

for el in periodictable.elements:
    ATOMIC_NUMBER[el.symbol] = el.number
    ATOMIC_SYMBOL[el.number] = el.symbol
    LOWERCASE_ATOMIC_SYMBOLS[el.symbol.lower()] = el.symbol

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
        return -1
    except ssh2.exceptions.Timeout:
        print("Timeout")
        lock.release()
        return sftp_get(src, dst, conn)
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
    DELAY = [5, 30, 60, 180, 300, 300, 300, 300]
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

def wait_until_done(job_id, conn, lock):
    print("Waiting for job {} to finish".format(job_id))
    DELAY = [5, 10, 15, 20, 60, 200, 400]
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

        if pid in kill_sig:
            direct_command("scancel {}".format(job_id), conn, lock)
            kill_sig.remove(pid)
            return -2

def system(command, log_file="", force_local=False, software="xtb", calc_id=-1, stage=-1):
    if REMOTE and not force_local:
        assert calc_id != -1
        assert stage != -1

        calc = Calculation.objects.get(pk=calc_id)

        pid = int(threading.get_ident())
        #Get the variables based on thread ID
        #These are already set by cluster_daemon when running
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        if calc.stage > stage:
            return 0
        elif calc.stage == stage:
            ret = wait_until_done(calc.remote_id, conn, lock)
            return ret
        else:
            assert calc.stage + 1 == stage
            print("Stage changing from {} to {}".format(calc.stage, stage))
            calc.stage = stage
            calc.save()

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
                            time.sleep(1)
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
                                ret = wait_until_done(job_id, conn, lock)
                                return ret
                        else:
                            job_id = output[-2].replace('Submitted batch job', '').strip()

                            calc.remote_id = int(job_id)
                            calc.save()
                            ret = wait_until_done(job_id, conn, lock)
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
                    ret = wait_until_done(job_id, conn, lock)
                    return ret
                else:
                    return 1
    else:
        if calc_id != -1:
            calc = Calculation.objects.get(pk=calc_id)
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
                    t.terminate()
                    t.kill()
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


def xtb_opt(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    os.chdir(local_folder)
    a = system("xtb {} --opt -o vtight -a 0.05 --chrg {} {} ".format(in_file, calc.parameters.charge, solvent_add), 'xtb_opt.out', calc_id=calc.id, stage=1)
    if a != 0:
        return a

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        a = sftp_get("{}/xtb_opt.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtb_opt.out"), conn, lock)
        b = sftp_get("{}/xtbopt.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtbopt.xyz"), conn, lock)

        if a == -1 or b == -1:
            return -1

        sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)

    if not os.path.isfile("{}/xtbopt.xyz".format(local_folder)):
        return 1

    if not os.path.isfile("{}/xtb_opt.out".format(local_folder)):
        return 1

    if os.path.isfile("{}/NOT_CONVERGED".format(local_folder)):
        return 1

    with open("{}/xtbopt.xyz".format(local_folder)) as f:
        lines = f.readlines()

    xyz_structure = clean_xyz(''.join(lines))

    with open("{}/xtb_opt.out".format(local_folder)) as f:
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

def xtb_sp(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    os.chdir(local_folder)
    a = system("xtb {} --chrg {} {} ".format(in_file, calc.parameters.charge, solvent_add), 'xtb_sp.out', calc_id=calc.id, stage=1)
    if a != 0:
        return a

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        a = sftp_get("{}/xtb_sp.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtb_sp.out"), conn, lock)
        if a == -1:
            return -1

        sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)

    if os.path.isfile("{}/NOT_CONVERGED".format(local_folder)):
        return 1

    if not os.path.isfile("{}/xtb_sp.out".format(local_folder)):
        return 1

    with open("{}/xtb_sp.out".format(local_folder)) as f:
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

    folder = '/'.join(in_file.split('/')[:-1])

    ORCA_TEMPLATE = """!xtb OPTTS
    %pal
    nprocs {}
    end
    {}
    *xyz {} {}
    {}
    *"""

    if calc.parameters.solvent == "Vacuum":
        solvent_add = ""
    else:
        solvent_add = '''%cpcm
        smd true
        SMDsolvent "{}"
        end'''.format(calc.parameters.solvent)

    lines = [i + '\n' for i in calc.structure.xyz_structure.split('\n')[2:]]

    with open(os.path.join(local_folder, 'ts.inp'), 'w') as out:
        out.write(ORCA_TEMPLATE.format(PAL, solvent_add, calc.parameters.charge, calc.parameters.multiplicity, ''.join(lines)))
    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        sftp_put(os.path.join(local_folder, 'ts.inp'), os.path.join(folder, 'ts.inp'), conn, lock)
        a = system("$EBROOTORCA/orca ts.inp", 'xtb_ts.out', software="ORCA", calc_id=calc.id, stage=1)

    else:
        os.chdir(local_folder)
        a = system("{}/orca ts.inp".format(EBROOTORCA), 'xtb_ts.out', software="ORCA", calc_id=calc.id, stage=1)
        if a != 0:
            print("Orca failed")
            return a

    if not local:
        a = sftp_get("{}/xtb_ts.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtb_ts.out"), conn, lock)
        b = sftp_get("{}/ts.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "ts.xyz"), conn, lock)

        if a == -1 or b == -1:
            return -1

        sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)

    if not os.path.isfile("{}/ts.xyz".format(local_folder)):
        return 1

    if not os.path.isfile("{}/xtb_ts.out".format(local_folder)):
        return 1

    if os.path.isfile("{}/NOT_CONVERGED".format(local_folder)):
        return 1

    with open(os.path.join(folder, "ts.xyz")) as f:
        lines = f.readlines()

    with open(os.path.join(folder, "xtb_ts.out")) as f:
        olines= f.readlines()
        ind = len(olines)-1
        while olines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(olines[ind].split()[4])

        while olines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(olines[ind].split()[3])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=clean_xyz(''.join(lines)), number=1)
    prop = get_or_create(calc.parameters, s)
    prop.homo_lumo_gap = hl_gap
    prop.energy = E
    prop.geom = True

    s.xyz_structure = '\n'.join([i.strip() for i in lines])

    s.save()
    prop.save()
    return 0


def xtb_scan(in_file, calc):
    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local
    folder = '/'.join(in_file.split('/')[:-1])

    constraints = calc.constraints.split(';')[:-1]
    if constraints == "":
        print("No constraints!")
        return -1, 'e'

    with open("{}/scan".format(local_folder), 'w') as out:
        out.write("$constrain\n")
        out.write("force constant=20\n")
        has_scan = False
        for cmd in constraints:
            _cmd, ids = cmd.split('-')
            _cmd = _cmd.split('_')
            ids = ids.split('_')
            type = len(ids)
            if type == 2:
                out.write("distance: {}, {}, auto\n".format(*ids))
            if type == 3:
                out.write("angle: {}, {}, {}, auto\n".format(*ids))
            if type == 4:
                out.write("dihedral: {}, {}, {}, {}, auto\n".format(*ids))
            if _cmd[0] == "Scan":
                has_scan = True
        if has_scan:
            calc.save()
            out.write("$scan\n")
            counter = 1
            for cmd in constraints:
                _cmd, ids = cmd.split('-')
                _cmd = _cmd.split('_')
                if _cmd[0] == "Scan":
                    out.write("{}: {}, {}, {}\n".format(counter, *_cmd[1:]))
                    counter += 1
        out.write("$end")

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/scan".format(local_folder), os.path.join(folder, 'scan'), conn, lock)

    os.chdir(local_folder)
    a = system("xtb {} --input scan --chrg {} {} --opt".format(in_file, calc.parameters.charge, solvent_add), 'xtb_scan.out', calc_id=calc.id, stage=1)
    if a != 0:
        return a

    if not local:
        a = sftp_get("{}/xtb_scan.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtb_scan.out"), conn, lock)
        if has_scan:
            b = sftp_get("{}/xtbscan.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtbscan.log"), conn, lock)
        else:
            b = sftp_get("{}/xtbopt.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtbopt.xyz"), conn, lock)
        if a == -1 or b == -1:
            return -1

        sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)


    if not os.path.isfile("{}/xtb_scan.out".format(local_folder)):
        return 1

    if os.path.isfile("{}/NOT_CONVERGED".format(local_folder)):
        return 1

    with open("{}/xtb_scan.out".format(local_folder)) as f:
        lines = f.readlines()
        for line in lines:
            if line.find("[WARNING] Runtime exception occurred") != -1:
                return 1

    if has_scan:
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
            for s in calc.result_ensemble.structure_set.all():
                s.properties.get(parameters=calc.parameters).rel_energy = (s.properties.get(parameters=calc.parameters).energy - min_E)*float(HARTREE_VAL)
                s.properties.get(parameters=calc.parameters).save()

    else:
        if not os.path.isfile("{}/xtbopt.xyz".format(local_folder)):
            return 1

        with open(os.path.join(local_folder, 'xtbopt.xyz')) as f:
            lines = f.readlines()
            r = Structure.objects.create(number=1)
            r.xyz_structure = clean_xyz(''.join(lines))

        with open(os.path.join(local_folder, "xtb_scan.out")) as f:
            lines = f.readlines()
            ind = len(lines)-1

            while lines[ind].find("HOMO-LUMO GAP") == -1:
                ind -= 1
            hl_gap = float(lines[ind].split()[3])
            E = float(lines[ind-2].split()[3])
            prop = get_or_create(calc.parameters, r)
            prop.energy = E
            prop.homo_lumo_gap = hl_gap
            #assert E == Eb

            r.homo_lumo_gap = hl_gap
            r.save()
            prop.save()
            calc.result_ensemble.structure_set.add(r)
            calc.result_ensemble.save()

    return 0

def xtb_freq(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    os.chdir(local_folder)
    system("xtb {} --uhf 1 --chrg {} {} --hess".format(in_file, calc.parameters.charge, solvent_add), 'xtb_freq.out', calc_id=calc.id, stage=1)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        a = sftp_get("{}/xtb_freq.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "xtb_freq.out"), conn, lock)
        b = sftp_get("{}/vibspectrum".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "vibspectrum"), conn, lock)
        c = sftp_get("{}/g98.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "g98.out"), conn, lock)

        if a == -1 or b == -1 or c == -1:
            return -1

        sftp_get("{}/NOT_CONVERGED".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "NOT_CONVERGED"), conn, lock)


    a = save_to_results(os.path.join(local_folder, "vibspectrum"), calc)
    if a != 0:
        return a

    if os.path.isfile("{}/NOT_CONVERGED".format(local_folder)):
        return 1

    if not os.path.isfile("{}/xtb_freq.out".format(local_folder)):
        return 1

    if not os.path.isfile("{}/g98.out".format(local_folder)):
        return 1

    with open("{}/xtb_freq.out".format(local_folder)) as f:
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

def crest_generic(in_file, calc, mode):
    local = calc.local

    if calc.parameters.solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[calc.parameters.solvent])
    else:
        solvent_add = ''

    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    os.chdir(local_folder)

    if calc.parameters.method == "GFN-FF":
        cmd_add = "-gff"
    elif calc.parameters.method == "GFN2-xTB//GFN-FF":
        cmd_add = "-gfn2//gfnff"
    else:
        cmd_add = ""

    if mode == "Final":#Restrict the number of conformers
        a = system("crest {} --chrg {} {} -rthr 0.5 -ewin 6 {}".format(in_file, calc.parameters.charge, solvent_add, cmd_add), 'crest.out', calc_id=calc.id, stage=1)
    elif mode == "NMR":#No restriction, as it will be done by enso
        a = system("crest {} --chrg {} {} -nmr {}".format(in_file, calc.parameters.charge, solvent_add, cmd_add), 'crest.out', calc_id=calc.id, stage=1)
    else:
        print("Invalid crest mode selected!")
        return -1

    if a != 0:
        return a

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        a = sftp_get("{}/crest.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "crest.out"), conn, lock)
        b = sftp_get("{}/crest_conformers.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "crest_conformers.xyz"), conn, lock)
        if a == -1 or b == -1:
            return -1

    if not os.path.isfile("{}/crest.out".format(local_folder)):
        return 1

    if not os.path.isfile("{}/crest_conformers.xyz".format(local_folder)):
        return 1

    with open(os.path.join(local_folder, "crest.out")) as f:
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
                r = Structure.objects.create(number=number, degeneracy=degeneracy)
                prop = get_or_create(calc.parameters, r)
                prop.energy = energy
                prop.boltzmann_weight = weight
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
            #assert r.energy == E
            r.xyz_structure = struct
            r.save()

    return 0

def clean_struct_line(line):
    a, x, y, z = line.split()
    return "{} {} {} {}\n".format(LOWERCASE_ATOMIC_SYMBOLS[a.lower()], x, y, z)

def crest(in_file, calc):
    return crest_generic(in_file, calc, "Final")

def crest_pre_nmr(in_file, calc):
    return crest_generic(in_file, calc, "NMR")


def orca_mo_gen(in_file, calc):
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    fname = in_file.split('/')[-1]
    folder = '/'.join(in_file.split('/')[:-1])

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'mo.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/mo.inp".format(local_folder), os.path.join(folder, "mo.inp"), conn, lock)
        a = system("$EBROOTORCA/orca mo.inp", 'orca_mo.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca mo.inp".format(EBROOTORCA), 'orca_mo.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        return a

    if not local:
        a = sftp_get("{}/orca_mo.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_mo.out"), conn, lock)
        b = sftp_get("{}/in-HOMO.cube".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "in-HOMO.cube"), conn, lock)
        c = sftp_get("{}/in-LUMO.cube".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "in-LUMO.cube"), conn, lock)
        d = sftp_get("{}/in-LUMOA.cube".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "in-LUMOA.cube"), conn, lock)
        e = sftp_get("{}/in-LUMOB.cube".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "in-LUMOB.cube"), conn, lock)
        if a == -1 or b == -1 or c == -1 or d == -1 or e == -1:
            return -1

    if not os.path.isfile("{}/orca_mo.out".format(local_folder)):
        return 1

    with open("{}/orca_mo.out".format(local_folder)) as f:
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
    folder = '/'.join(in_file.split('/')[:-1])

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    lines = [i + '\n' for i in clean_xyz(calc.structure.xyz_structure).split('\n')[2:] if i != '' ]

    if len(lines) == 1:#Single atom
        s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=calc.structure.xyz_structure, number=calc.structure.number, degeneracy=calc.structure.degeneracy)
        s.save()
        calc.structure = s
        calc.step = BasicStep.objects.get(name="Single-Point Energy")
        calc.save()
        return orca_sp(in_file, calc)

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'opt.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/opt.inp".format(local_folder), os.path.join(folder, "opt.inp"), conn, lock)
        a = system("$EBROOTORCA/orca opt.inp", 'orca_opt.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca opt.inp".format(EBROOTORCA), 'orca_opt.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        a = sftp_get("{}/opt.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "opt.xyz"), conn, lock)
        b = sftp_get("{}/orca_opt.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_opt.out"), conn, lock)
        if a == -1 or b == -1:
            return -1

    if not os.path.isfile("{}/opt.xyz".format(local_folder)):
        return 1

    if not os.path.isfile("{}/orca_opt.out".format(local_folder)):
        return 1

    with open("{}/opt.xyz".format(local_folder)) as f:
        lines = f.readlines()

    xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))

    with open("{}/orca_opt.out".format(local_folder)) as f:
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
    folder = '/'.join(in_file.split('/')[:-1])

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'sp.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/sp.inp".format(local_folder), os.path.join(folder, "sp.inp"), conn, lock)
        a = system("$EBROOTORCA/orca sp.inp", 'orca_sp.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca sp.inp".format(EBROOTORCA), 'orca_sp.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        b = sftp_get("{}/orca_sp.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_sp.out"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/orca_sp.out".format(local_folder)):
        return 1

    with open("{}/orca_sp.out".format(local_folder)) as f:
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
    local = calc.local
    folder = '/'.join(in_file.split('/')[:-1])

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'ts.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/ts.inp".format(local_folder), os.path.join(folder, "ts.inp"), conn, lock)
        a = system("$EBROOTORCA/orca ts.inp".format(EBROOTORCA), 'orca_ts.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca ts.inp".format(EBROOTORCA), 'orca_ts.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        a = sftp_get("{}/ts.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "ts.xyz"), conn, lock)
        b = sftp_get("{}/orca_ts.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_ts.out"), conn, lock)
        if a == -1 or b == -1:
            return -1

    if not os.path.isfile("{}/ts.xyz".format(local_folder)):
        return 1

    if not os.path.isfile("{}/orca_ts.out".format(local_folder)):
        return 1

    with open("{}/ts.xyz".format(local_folder)) as f:
        lines = f.readlines()
    xyz_structure = clean_xyz('\n'.join([i.strip() for i in lines]))
    with open("{}/orca_ts.out".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("FINAL SINGLE POINT ENERGY") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=1, degeneracy=1)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    return 0

def orca_freq(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'freq.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/freq.inp".format(local_folder), os.path.join(folder, "freq.inp"), conn, lock)

        a = system("$EBROOTORCA/orca freq.inp", 'orca_freq.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca freq.inp".format(EBROOTORCA), 'orca_freq.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        a = sftp_get("{}/orca_freq.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_freq.out"), conn, lock)
        if a == -1:
            return -1

    if not os.path.isfile("{}/orca_freq.out".format(local_folder)):
        return 1

    with open("{}/orca_freq.out".format(local_folder)) as f:
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
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'scan.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/scan.inp".format(local_folder), os.path.join(folder, "scan.inp"), conn, lock)
        a = system("$EBROOTORCA/orca scan.inp", 'orca_scan.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca scan.inp".format(EBROOTORCA), 'orca_scan.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        a = sftp_get("{}/orca_scan.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_scan.out"), conn, lock)
        if a == -1:
            return -1

        if orca.has_scan:
            a = sftp_get("{}/scan.relaxscanact.dat".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "scan.relaxscanact.dat"), conn, lock)
            b = sftp_get("{}/scan.allxyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "scan.allxyz"), conn, lock)
            if a == -1 or b == -1:
                return -1
        else:
            a = sftp_get("{}/scan.xyz".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "scan.xyz"), conn, lock)
            if a == -1:
                return -1

    if orca.has_scan:
        if not os.path.isfile("{}/scan.relaxscanact.dat".format(local_folder)):
            return 1

        if not os.path.isfile("{}/scan.allxyz".format(local_folder)):
            return 1

        energies = []
        with open(os.path.join(local_folder, 'scan.relaxscanact.dat')) as f:
            lines = f.readlines()
            for line in lines:
                energies.append(float(line.split()[1]))
        with open(os.path.join(local_folder, 'scan.allxyz')) as f:
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
        if not os.path.isfile("{}/scan.xyz".format(local_folder)):
            return 1

        if not os.path.isfile("{}/orca_scan.out".format(local_folder)):
            return 1

        with open(os.path.join(local_folder, 'scan.xyz')) as f:
            lines = f.readlines()
            r = Structure.objects.create(number=1)
            r.xyz_structure = clean_xyz(''.join([i.strip() + '\n' for i in lines]))

        with open(os.path.join(folder, "orca_scan.out")) as f:
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
    a = system("xtb4stda {} -chrg {} {}".format(in_file, calc.parameters.charge, solvent_add), 'xtb4stda.out', calc_id=calc.id, stage=1)
    if a != 0:
        return a

    os.chdir(local_folder)
    a = system("stda -xtb -e 12", 'stda.out', calc_id=calc.id, stage=2)
    if a != 0:
        return a

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        sftp_get("{}/tda.dat".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "tda.dat"), conn, lock)

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

def orca_nmr(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    orca = OrcaCalculation(calc)

    with open(os.path.join(local_folder, 'nmr.inp'), 'w') as out:
        out.write(orca.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/nmr.inp".format(local_folder), os.path.join(folder, "nmr.inp"), conn, lock)
        a = system("$EBROOTORCA/orca nmr.inp", 'orca_nmr.out', software="ORCA", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("{}/orca nmr.inp".format(EBROOTORCA), 'orca_nmr.out', software="ORCA", calc_id=calc.id, stage=1)

    if a != 0:
        print("Orca failed")
        return a

    if not local:
        a = sftp_get("{}/orca_nmr.out".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "orca_nmr.out"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/orca_nmr.out".format(local_folder)):
        return 1

    with open(os.path.join(local_folder, 'orca_nmr.out')) as f:
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

def gaussian_sp(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'sp.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/sp.com".format(local_folder), os.path.join(folder, "sp.com"), conn, lock)
        a = system("g16 sp.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 sp.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        print("Gaussian failed")
        return a

    if not local:
        b = sftp_get("{}/sp.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "sp.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/sp.log".format(local_folder)):
        return 1

    with open("{}/sp.log".format(local_folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("SCF Done") == -1:
            ind -= 1
        E = float(lines[ind].split()[4])

    prop = get_or_create(calc.parameters, calc.structure)
    prop.energy = E
    prop.save()

    return 0

def gaussian_opt(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'opt.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/opt.com".format(local_folder), os.path.join(folder, "opt.com"), conn, lock)
        a = system("g16 opt.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 opt.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        print("Gaussian failed")
        return a

    if not local:
        b = sftp_get("{}/opt.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "opt.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/opt.log".format(local_folder)):
        return 1

    with open("{}/opt.log".format(local_folder)) as f:
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

    return 0

def gaussian_freq(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'freq.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/freq.com".format(local_folder), os.path.join(folder, "freq.com"), conn, lock)

        a = system("g16 freq.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 freq.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        print("Gaussian failed")
        return a

    if not local:
        a = sftp_get("{}/freq.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "freq.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/freq.log".format(local_folder)):
        return 1

    lines = [i + '\n' for i in clean_xyz(calc.structure.xyz_structure).split('\n')[2:] if i.strip() != '']

    with open("{}/freq.log".format(local_folder)) as f:
        outlines = f.readlines()
        ind = len(lines)-1

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


    if len(lines) > 1:
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

        ind = 0
        while outlines[ind].find("and normal coordinates:") == -1:
            ind += 1
        ind += 3

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
                assert len(struct) == num_atoms
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

    return 0

def gaussian_ts(in_file, calc):

    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local
    folder = '/'.join(in_file.split('/')[:-1])

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'ts.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/ts.com".format(local_folder), os.path.join(folder, "ts.com"), conn, lock)
        a = system("g16 ts.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 ts.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        print("Gaussian failed")
        return a

    if not local:
        b = sftp_get("{}/ts.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "ts.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/ts.log".format(local_folder)):
        return 1

    with open("{}/ts.log".format(local_folder)) as f:
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

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=1, degeneracy=1)
    prop = get_or_create(calc.parameters, s)
    prop.energy = E
    prop.geom = True
    s.save()
    prop.save()

    return 0

def gaussian_scan(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local
    failed = False

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'scan.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/scan.com".format(local_folder), os.path.join(folder, "scan.com"), conn, lock)
        a = system("g16 scan.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 scan.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        if gaussian.has_scan:
            failed = True
        else:
            return a

    if not local:
        a = sftp_get("{}/scan.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "scan.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/scan.log".format(local_folder)):
        return 1

    with open(os.path.join(local_folder, 'scan.log')) as f:
        lines = f.readlines()

    if gaussian.has_scan:
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

            while lines[ind].find("Input orientation:") == -1:
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

    if failed:
        return -1
    else:
        return 0

def gaussian_nmr(in_file, calc):
    folder = '/'.join(in_file.split('/')[:-1])
    local_folder = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    local = calc.local

    gaussian = GaussianCalculation(calc)

    with open(os.path.join(local_folder, 'nmr.com'), 'w') as out:
        out.write(gaussian.input_file)

    if not local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]
        sftp_put("{}/nmr.com".format(local_folder), os.path.join(folder, "nmr.com"), conn, lock)
        a = system("g16 nmr.com", software="Gaussian", calc_id=calc.id, stage=1)
    else:
        os.chdir(local_folder)
        a = system("g16 nmr.com", software="Gaussian", calc_id=calc.id, stage=1)

    if a != 0:
        print("Gaussian failed")
        return a

    if not local:
        a = sftp_get("{}/nmr.log".format(folder), os.path.join(CALCUS_SCR_HOME, str(calc.id), "nmr.log"), conn, lock)
        if a != 0:
            return a

    if not os.path.isfile("{}/nmr.log".format(local_folder)):
        return 1

    with open(os.path.join(local_folder, 'nmr.log')) as f:
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
            if s.parent_ensemble.relative_energy(s, order.filter.parameters) < order.filter.value:
                structures.append(s)

    return structures

@app.task(base=AbortableTask)
def dispatcher(drawing, order_id):
    if is_test:
        print("TEST MODE DISPATCHER")

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
    else:
        for s in ensemble.structure_set.all():
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
                    assert fingerprint == fing
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

    group_order = []
    calculations = []

    input_structures = filter(order, input_structures)

    if step.creates_ensemble:
        if order.name.strip() == "" or created_molecule:
            e = Ensemble.objects.create(name="{} Result".format(order.step.name), origin=ensemble)
        else:
            e = Ensemble.objects.create(name=order.name, origin=ensemble)
        print("creating ensemble {}".format(e.id))
        order.result_ensemble = e
        order.save()
        molecule.ensemble_set.add(e)
        molecule.save()
        e.save()

        for s in input_structures:
            c = Calculation.objects.create(structure=s, order=order, date=datetime.now(), step=step, parameters=order.parameters, result_ensemble=e, constraints=order.constraints)
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
                cmd = ClusterCommand.objects.create(issuer=order.author)
                cmd.save()
                with open(os.path.join(CALCUS_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
                    out.write("launch\n")
                    out.write("{}\n".format(c.id))
                    out.write("{}\n".format(order.resource.id))

    else:
        for s in input_structures:
            c = Calculation.objects.create(structure=s, order=order, date=datetime.now(), parameters=order.parameters, step=step, constraints=order.constraints)
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
                cmd = ClusterCommand.objects.create(issuer=order.author)
                cmd.save()
                with open(os.path.join(CALCUS_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
                    out.write("launch\n")
                    out.write("{}\n".format(c.id))
                    out.write("{}\n".format(order.resource.id))

    for task, c in zip(group_order, calculations):
        res = task.apply_async()
        c.task_id = res
        c.save()

@app.task(base=AbortableTask)
def run_calc(calc_id):
    print("Processing calc {}".format(calc_id))
    calc = Calculation.objects.get(pk=calc_id)

    if calc.status == 3:#Already revoked:
        return

    calc.status = 1
    calc.save()
    f = BASICSTEP_TABLE[calc.parameters.software][calc.step.name]

    res_dir = os.path.join(CALCUS_RESULTS_HOME, str(calc.id))
    workdir = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    if calc.stage == 0:
        os.mkdir(res_dir)
        os.mkdir(workdir)
        in_file = os.path.join(workdir, 'in.xyz')

        with open(in_file, 'w') as out:
            out.write(clean_xyz(calc.structure.xyz_structure))

    if not calc.local:
        pid = int(threading.get_ident())
        conn = connections[pid]
        lock = locks[pid]
        remote_dir = remote_dirs[pid]

        if calc.stage == 0:
            direct_command("mkdir -p {}".format(remote_dir), conn, lock)
            sftp_put(in_file, os.path.join(remote_dir, "in.xyz"), conn, lock)

        in_file = os.path.join(remote_dir, "in.xyz")


    ti = time()
    try:
        ret = f(in_file, calc)
    except:
        ret = 1
        traceback.print_exc()

    if ret == -2:
        calc.status = 3
        calc.save()
        print("Job {} cancelled".format(calc.id))
        return

    tf = time()
    calc.execution_time = int((tf-ti)*int(PAL))

    if ret != 0:
        calc.status = 3
        calc.save()
    else:
        calc.status = 2
        calc.save()
    for f in glob.glob("{}/*.out".format(workdir)):
        fname = f.split('/')[-1]
        copyfile(f, "{}/{}".format(res_dir, fname))

    for f in glob.glob("{}/*.log".format(workdir)):
        fname = f.split('/')[-1].replace('.log', '.out')
        if fname == "xtbscan.out" or fname == "xtbopt.out":
            continue
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
                calc.save()
        else:
            print("Cannot cancel calculation without task id")
    else:
        cmd = ClusterCommand.objects.create(issuer=calc.order.author)
        cmd.save()
        calc.status = 3
        calc.save()

        with open(os.path.join(CALCUS_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
            out.write("kill\n")
            out.write("{}\n".format(calc.id))
            out.write("{}\n".format(calc.order.resource.id))#####


@app.task(name='celery.ping')
def ping():
    return 'pong'

