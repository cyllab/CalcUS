from __future__ import absolute_import, unicode_literals

from labsandbox.celery import app

from celery.signals import task_prerun, task_postrun
from .models import Calculation, Structure
from django.utils import timezone

import os
import numpy as np
import decimal
import math
from datetime import datetime
from time import time, sleep

import subprocess
import shlex
from shutil import copyfile
import glob
import ssh2
from threading import Lock
import threading

from celery import group

from .models import *
from ssh2.sftp import LIBSSH2_FXF_READ, LIBSSH2_SFTP_S_IWGRP, LIBSSH2_SFTP_S_IRWXU
from ssh2.sftp import LIBSSH2_FXF_CREAT, LIBSSH2_FXF_WRITE, \
    LIBSSH2_SFTP_S_IRUSR, LIBSSH2_SFTP_S_IRGRP, LIBSSH2_SFTP_S_IWUSR, \
    LIBSSH2_SFTP_S_IROTH

try:
    is_test = os.environ['LAB_TEST']
except:
    is_test = False
import periodictable
import mendeleev
from .constants import *

ATOMIC_NUMBER = {
        }
for el in periodictable.elements:
    ATOMIC_NUMBER[el.symbol] = el.number

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
        #Get the variables based on thread ID
        #These are already set by cluster_daemon when running
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

def generate_xyz_structure(drawing, structure):

    if drawing:
        SCALE = 1
        #SCALE = 20
    else:
        SCALE = 1

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
                    structure.xyz_structure = ''.join(lines)
                    structure.save()
                    return 0
            else:
                to_print = []
                for line in structure.mol_structure.split('\n')[4:]:
                    sline = line.split()
                    try:
                        a = int(sline[3])
                    except ValueError:
                        to_print.append("{} {} {} {}\n".format(sline[3], float(sline[0])*SCALE, float(sline[1])*SCALE, float(sline[2])*SCALE))
                    else:
                        break
                num = len(to_print)
                in_struct.xyz_structure = "{}\n".format(num)
                in_struct.xyz_structure += "CalcUS\n"
                for line in to_print:
                    in_struct.xyz_structure += line
                in_struct.save()
                return 0
        elif in_struct.sdf_structure != '':#unimplemented
            with open("{}/initial.sdf".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))), 'w') as out:
                out.write(in_struct.sdf_structure)
            a = system("obabel {}/initial.sdf -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
            a = system("obabel {}/initial.sdf -O {}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)

            with open(os.path.join("{}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))))) as f:
                lines = f.readlines()
            in_struct.xyz_structure = '\n'.join([i.strip() for i in lines])
            in_struct.save()
            return 0
        else:
            print("Unimplemented")
            return -1
    else:
        return 0

def handle_input_file(drawing, calc_obj):
    #if os.path.isfile("{}/initial_2D.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)))):
    #    a = system("obabel {}/initial_2D.mol -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
    #    return system("obabel {}/initial_2D.mol -O {}/initial.xyz -h --gen3D".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)

    if drawing:
        SCALE = 1
        #SCALE = 20
    else:
        SCALE = 1

    if len(calc_obj.ensemble.structure_set.all()) == 1:#TODO: expend to multiple structures?
        in_struct = calc_obj.ensemble.structure_set.all()[0]
        if in_struct.xyz_structure == "":
            if in_struct.mol_structure != '':
                with open("{}/initial.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))), 'w') as out:
                    out.write(in_struct.mol_structure)
                if drawing:
                    a = system("obabel {}/initial.mol -O {}/initial_H.mol -h --gen3D".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)
                    a = system("mv {}/initial_H.mol {}/initial.mol ".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)

                a = system("obabel {}/initial.mol -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)

                with open(os.path.join("{}/initial.mol".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))))) as f:
                    lines = f.readlines()[4:]

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
                in_struct.xyz_structure = "{}\n".format(num)
                in_struct.xyz_structure += "CalcUS\n"
                for line in to_print:
                    in_struct.xyz_structure += line
                in_struct.save()
                return 0
            elif in_struct.sdf_structure != '':
                with open("{}/initial.sdf".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))), 'w') as out:
                    out.write(in_struct.sdf_structure)
                a = system("obabel {}/initial.sdf -O {}/icon.svg -d --title '' -xb none".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
                a = system("obabel {}/initial.sdf -O {}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), os.path.join(LAB_SCR_HOME, str(calc_obj.id))), force_local=True)

                with open(os.path.join("{}/initial.xyz".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id))))) as f:
                    lines = f.readlines()
                in_struct.xyz_structure = '\n'.join([i.strip() for i in lines])
                in_struct.save()
                return 0
            else:
                print("Unimplemented")
                return -1
        else:
            return 0



def xtb_opt(in_file, calc):
    solvent = calc.parameters.solvent
    charge = calc.parameters.charge
    folder = '/'.join(in_file.split('/')[:-1])

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(folder)
    a = system("xtb {} --opt -o vtight -a 0.05 --chrg {} {} ".format(in_file, charge, solvent_add), 'xtb_opt.out')

    if a == 0:
        with open("xtbopt.xyz") as f:
            lines = f.readlines()
        xyz_structure = ''.join(lines)
        with open("xtb_opt.out") as f:
            lines = f.readlines()
            ind = len(lines)-1

            while lines[ind].find("HOMO-LUMO GAP") == -1:
                ind -= 1
            hl_gap = float(lines[ind].split()[3])
            E = float(lines[ind-2].split()[3])

        s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=xyz_structure, number=1, degeneracy=1)
        prop = get_or_create(calc.parameters, s)
        prop.homo_lumo_gap = hl_gap
        prop.energy = E
        prop.geom = True
        s.save()
        prop.save()
        return 0
    else:
        return a

def get_or_create(params, struct):
    for p in struct.properties.all():
        if p.parameters == params:
            return p
    return Property.objects.create(parameters=params, parent_structure=struct)

def xtb_ts(in_file, calc):
    solvent = calc.parameters.solvent
    charge = calc.parameters.charge
    multiplicity = calc.parameters.multiplicity

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    folder = '/'.join(in_file.split('/')[:-1])

    ORCA_TEMPLATE = """!xtb OPTTS
    %pal
    nprocs {}
    end
    {}
    *xyz {} {}
    {}
    *"""

    if solvent == "Vacuum":
        solvent_add = ""
    else:
        solvent_add = '''%cpcm
        smd true
        SMDsolvent "{}"
        end'''.format(solvent)

    with open(in_file) as f:
        lines = f.readlines()[2:]

    with open(os.path.join(folder, 'ts.inp'), 'w') as out:
        out.write(ORCA_TEMPLATE.format(PAL, solvent_add, charge, multiplicity, ''.join(lines)))

    os.chdir(folder)
    a = system("{}/orca ts.inp".format(ORCAPATH), 'xtb_ts.out')
    if a != 0:
        print("Orca failed")
        return a
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

    s = Structure.objects.create(parent_ensemble=calc.result_ensemble, xyz_structure=''.join(lines), number=1)
    prop = get_or_create(calc.parameters, s)
    prop.homo_lumo_gap = hl_gap
    prop.energy = E
    prop.geom = True

    s.xyz_structure = '\n'.join([i.strip() for i in lines])

    s.save()
    prop.save()
    return 0


def xtb_scan(in_file, calc):
    solvent = calc.parameters.solvent
    charge = calc.parameters.charge

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    folder = '/'.join(in_file.split('/')[:-1])

    constraints = calc.constraints.split(';')[:-1]
    if constraints == "":
        print("No constraints!")
        return -1, 'e'

    with open("{}/scan".format(folder), 'w') as out:
        out.write("$constrain\n")
        out.write("force constant=99\n")
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

    os.chdir(folder)
    a = system("xtb {} --input scan --chrg {} {} --opt".format(in_file, charge, solvent_add), 'xtb_scan.out')
    if a != 0:
        return a


    if has_scan:
        with open(os.path.join(folder, 'xtbscan.log')) as f:
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
                E = float(lines[inds[metaind]+1].split()[1])
                struct = ''.join([i.strip() + '\n' for i in lines[inds[metaind]:inds[metaind+1]]])

                r = Structure.objects.create(number=metaind+1)
                prop = get_or_create(calc.parameters, r)
                prop.energy = E
                prop.geom = True
                prop.save()
                r.xyz_structure = struct
                r.save()
                if E < min_E:
                    min_E = E

                calc.result_ensemble.structure_set.add(r)
            for s in calc.result_ensemble.structure_set.all():
                s.properties.get(parameters=calc.parameters).rel_energy = (s.properties.get(parameters=calc.parameters).energy - min_E)*float(HARTREE_VAL)
                s.properties.get(parameters=calc.parameters).save()

    else:
        with open(os.path.join(folder, 'xtbopt.xyz')) as f:
            lines = f.readlines()
            #E = float(lines[1])
            r = Structure.objects.create(number=1)
            r.xyz_structure = ''.join(lines)

        with open(os.path.join(folder, "xtb_scan.out")) as f:
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
    solvent = calc.parameters.solvent
    charge = calc.parameters.charge
    folder = '/'.join(in_file.split('/')[:-1])

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    os.chdir(folder)
    system("xtb {} --uhf 1 --chrg {} {} --hess".format(in_file, charge, solvent_add), 'xtb_freq.out')

    a = save_to_results(os.path.join(folder, "vibspectrum"), calc)
    if a != 0:
        return -1, 'e'

    with open("{}/xtb_freq.out".format(folder)) as f:
        lines = f.readlines()
        ind = len(lines)-1

        while lines[ind].find("HOMO-LUMO GAP") == -1:
            ind -= 1
        hl_gap = float(lines[ind].split()[3])
        E = float(lines[ind-4].split()[3])
        G = float(lines[ind-2].split()[4])

    vib_file = os.path.join(folder, "vibspectrum")

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
            x = np.arange(500, 4000, 1)#Wave number in cm^-1
            spectrum = plot_vibs(x, zip(vibs, intensities))
            with open(os.path.join(LAB_RESULTS_HOME, str(calc.id), "IR.csv"), 'w') as out:
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

    with open(os.path.join(folder, "hessian")) as f:
        lines = f.readlines()[1:]
        for line in lines:
            hess += [float(i) for i in line.strip().split()]

        num_freqs = len(hess)/(3*num_atoms)
        if not num_freqs.is_integer():
            print("Incorrect number of frequencies!")
            exit(0)

        num_freqs = int(num_freqs)

    '''
    def output_with_displacement(mol, out, hess):
        #Simple displacement based on the hessian
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

    '''
    for ind in range(num_freqs):
        _hess = hess[3*num_atoms*ind:3*num_atoms*(ind+1)]
        with open(os.path.join(LAB_RESULTS_HOME, str(calc.id), "freq_{}.xyz".format(ind)), 'w') as out:
            out.write("{}\n".format(num_atoms))
            assert len(struct) == num_atoms
            out.write("CalcUS\n")
            for ind2, (a, x, y, z) in enumerate(struct):
                out.write("{} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}\n".format(a, x, y, z, *_hess[3*ind2:3*ind2+3]))
            #output_with_displacement(struct, out, _hess)
    return 0

def crest_generic(in_file, calc, mode):

    solvent = calc.parameters.solvent
    charge = calc.parameters.charge

    if solvent != "Vacuum":
        solvent_add = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    folder = '/'.join(in_file.split('/')[:-1])
    os.chdir(folder)
    if mode == "Final":#Restrict the number of conformers
        a = system("crest {} --chrg {} {} -rthr 0.4 -ewin 4".format(in_file, charge, solvent_add), 'crest.out')
    elif mode == "NMR":#No restriction, as it will be done by enso
        a = system("crest {} --chrg {} {} -nmr".format(in_file, charge, solvent_add), 'crest.out')
    else:
        print("Invalid crest mode selected!")
        return -1

    if a != 0:
        return -1

    with open("{}/crest.out".format(folder)) as f:
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

    with open("{}/crest_conformers.xyz".format(folder)) as f:
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
            struct = ''.join([i.strip() + '\n' for i in lines[inds[metaind]:inds[metaind+1]]])
            r = calc.result_ensemble.structure_set.get(number=metaind+1)
            #assert r.energy == E
            r.xyz_structure = struct
            r.save()

    return 0

def crest(in_file, calc):
    return crest_generic(in_file, calc, "Final")

def crest_pre_nmr(in_file, calc):
    return crest_generic(in_file, calc, "NMR")


def mo_gen(in_file, calc):
    ORCA_TEMPLATE = """!HF-3c SP PAL8
%plots
dim1 45
dim2 45
dim3 45
min1 0
max1 0
min2 0
max2 0
min3 0
max3 0
Format Gaussian_Cube
MO("in-HOMO.cube",{},0);
MO("in-LUMO.cube",{},0);
MO("in-LUMOA.cube",{},0);
MO("in-LUMOB.cube",{},0);
end
*xyzfile {} {} {}
"""

    struct = calc.structure.xyz_structure
    electrons = 0
    for line in struct.split('\n')[2:]:
        if line.strip() == "":
            continue
        el = line.split()[0]
        electrons += ATOMIC_NUMBER[el]

    electrons -= calc.parameters.charge

    if calc.parameters.multiplicity != 1:
        print("Unimplemented multiplicity")
        return -1

    n_HOMO = int(electrons/2)-1
    n_LUMO = int(electrons/2)
    n_LUMO1 = int(electrons/2)+1
    n_LUMO2 = int(electrons/2)+2

    solvent = calc.parameters.solvent
    charge = calc.parameters.charge
    multiplicity = calc.parameters.multiplicity

    fname = in_file.split('/')[-1]
    folder = '/'.join(in_file.split('/')[:-1])

    with open("{}/mo.inp".format(folder), 'w') as out:
        out.write(ORCA_TEMPLATE.format(n_HOMO, n_LUMO, n_LUMO1, n_LUMO2, charge, multiplicity, fname))

    a = system("{}/orca mo.inp".format(ORCAPATH), 'orca_mo.out')
    if a != 0:
        return a, 'e'

    save_to_results("{}/in-HOMO.cube".format(folder), calc)
    save_to_results("{}/in-LUMO.cube".format(folder), calc)
    save_to_results("{}/in-LUMOA.cube".format(folder), calc)
    save_to_results("{}/in-LUMOB.cube".format(folder), calc)

    prop = get_or_create(calc.parameters, calc.structure)
    prop.mo = calc.id
    prop.save()

    return 0

def enso(in_file, calc):

    solvent = calc.parameters.solvent
    charge = calc.parameters.charge

    if solvent != "Vacuum":
        solvent_add = '-solv {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add = ''

    a = system("enso.py {} --charge {}".format(solvent_add, charge), 'enso_pre.out')

    if a != 0:
        return a, 'e'

    a = system("enso.py -run", 'enso.out')

    return a, calc.ensemble

def anmr(in_file, calc):
    a = system("anmr", 'anmr.out')

    if a != 0:
        return a, 'e'

    folder = '/'.join(in_file.split('/')[:-1])

    with open("{}/anmr.dat".format(folder)) as f:
        lines = f.readlines()
        with open("{}/nmr.csv".format(os.path.join(LAB_RESULTS_HOME, str(calc.id))), 'w') as out:
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
                a = system("babel -ixyz {}/{} -oxyz {}/conf.xyz -m".format(os.path.join(LAB_SCR_HOME, str(calc_obj.id)), f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
            else:
                copyfile(os.path.join(LAB_SCR_HOME, str(calc_obj.id), fname), os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
        else:
            copyfile(f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
    elif len(s) == 1:
        name = s
        copyfile(f, os.path.join(LAB_RESULTS_HOME, str(calc_obj.id), out_name))
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

    solvent = calc.parameters.solvent
    charge = calc.parameters.charge

    if solvent != "Vacuum":
        solvent_add_xtb = '-g {}'.format(SOLVENT_TABLE[solvent])
    else:
        solvent_add_xtb = ''

    os.chdir(folder)
    a = system("xtb4stda {} -chrg {} {}".format(in_file, charge, solvent_add_xtb), 'xtb4stda.out')
    if a != 0:
        return a

    os.chdir(folder)
    a = system("stda -xtb -e 12", 'stda.out')
    if a != 0:
        return a

    f_x = np.arange(120.0, 1200.0, 1.0)
    with open("{}/tda.dat".format(folder)) as f:
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


    with open("{}/uvvis.csv".format(os.path.join(LAB_RESULTS_HOME, str(calc.id))), 'w') as out:
        out.write("Wavelength (nm), Absorbance\n")
        for ind, x in enumerate(f_x):
            out.write("{},{:.8f}\n".format(x, yy[ind]))

    prop = get_or_create(calc.parameters, calc.structure)
    prop.uvvis = calc.id
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


BASICSTEP_TABLE = {
            'Geometrical Optimisation': xtb_opt,
            'Crest': crest,
            'Constrained Optimisation': xtb_scan,
            'Frequency Calculation': xtb_freq,
            'TS Optimisation': xtb_ts,
            'UV-Vis Calculation': xtb_stda,
            'Crest Pre NMR': crest_pre_nmr,
            'Enso': enso,
            'Anmr': anmr,
            'MO Calculation': mo_gen,
        }

time_dict = {}

@app.task
def dispatcher(drawing, order_id):
    order = CalculationOrder.objects.get(pk=order_id)
    ensemble = order.ensemble

    step = order.step

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
            molecule.save()
        ensemble.parent_molecule = molecule
        ensemble.save()
    else:
        molecule = ensemble.parent_molecule

    group_order = []

    if step.creates_ensemble:
        e = Ensemble.objects.create(name="Result Ensemble")
        print("creating ensemble {}".format(e.id))
        molecule.ensemble_set.add(e)
        molecule.save()
        e.save()

        for s in ensemble.structure_set.all():
            c = Calculation.objects.create(structure=s, order=order, date=datetime.now(), step=step, parameters=order.parameters, result_ensemble=e, constraints=order.constraints)
            c.save()
            group_order.append(run_calc.s(c.id).set(queue='comp'))

    else:
        print("using ensemble {}".format(ensemble.id))
        for s in ensemble.structure_set.all():
            c = Calculation.objects.create(structure=s, order=order, date=datetime.now(), parameters=order.parameters, step=step, constraints=order.constraints)
            c.save()
            group_order.append(run_calc.s(c.id).set(queue='comp'))

    g = group(group_order)
    result = g.apply_async()


@app.task
def run_calc(calc_id):
    print("Processing calc {}".format(calc_id))
    calc = Calculation.objects.get(pk=calc_id)
    calc.status = 1
    calc.save()
    f = BASICSTEP_TABLE[calc.step.name]

    os.mkdir(os.path.join(LAB_RESULTS_HOME, str(calc.id)))
    workdir = os.path.join(LAB_SCR_HOME, str(calc.id))
    os.mkdir(workdir)
    in_file = os.path.join(workdir, 'in.xyz')

    with open(in_file, 'w') as out:
        out.write(calc.structure.xyz_structure)

    ret = f(in_file, calc)
    if ret != 0:
        calc.status = 3
        calc.save()
    else:
        calc.status = 2
        calc.save()
    return ret

@app.task
def run_procedure(drawing, calc_id):

    calc_obj = Calculation.objects.get(pk=calc_id)
    calc_obj.status = 1
    calc_obj.save()

    if len(calc_obj.ensemble.structure_set.all()) == 1:
        in_struct = calc_obj.ensemble.structure_set.all()[0]
    else:
        print("Not implemented")
        return -1


    a = system("mkdir -p {}".format(os.path.join(LAB_RESULTS_HOME, str(calc_obj.id))), force_local=True)
    if a != 0:
        calc_obj.status = 3
        calc_obj.error_message = "Failed to create the results directory"
        calc_obj.save()
        return

    if in_struct.xyz_structure == '':
        a = handle_input_file(drawing, calc_obj)

        id = str(calc_obj.id)
        if a != 0:
            calc_obj.status = 3
            calc_obj.error_message = "Failed to convert the input structure"
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

    procedure = calc_obj.procedure
    steps_to_do = list(procedure.initial_steps.all())
    calc_obj.num_steps = len(procedure.step_set.all())+1

    if not isinstance(steps_to_do, list):
        steps_to_do = [steps_to_do]

    in_ensemble = calc_obj.ensemble
    ind = 1
    step_ind = 1
    while len(steps_to_do) > 0:
        step = steps_to_do.pop()
        calc_obj.current_status = step.step_model.desc
        calc_obj.current_step = ind
        calc_obj.save()
        function = BASICSTEP_TABLE[step.step_model.name]

        if not step.same_dir:
            step_dir = os.path.join(LAB_SCR_HOME, str(calc_obj.id), "step{}".format(step_ind))
            a = system("mkdir -p {}".format(step_dir), force_local=True)

            in_file = os.path.join(LAB_SCR_HOME, str(calc_obj.id), "step{}".format(step_ind), "in.xyz")
            with open(in_file, 'w') as out:
                out.write(in_ensemble.structure_set.all()[0].xyz_structure)
        else:
            in_file = os.path.join(LAB_SCR_HOME, str(calc_obj.id), "step{}".format(step_ind), "in.xyz")
            step_ind -= 1


        os.chdir(step_dir)
        a, e = function(in_file, calc_obj)

        ind += 1
        step_ind += 1

        if a != 0:
            calc_obj.status = 3
            calc_obj.error_message = step.step_model.error_message
            calc_obj.save()
            return a
        else:
            calc_obj.result_ensemble = e
            calc_obj.save()

        next_steps = step.step_set.all()
        if len(next_steps) > 0:
            for ss in next_steps:
                steps_to_do.append(ss)

    calc_obj.current_step = calc_obj.num_steps
    calc_obj.status = 2
    calc_obj.save()

    if REMOTE:
        files = direct_command("ls {}".format(remote_dir), conn, lock)
        for f in files:
            if f.strip() != '':
                sftp_get(os.path.join(remote_dir, f), os.path.join(LAB_SCR_HOME, str(calc_obj.id), f), conn, lock)
    return 0

'''
@task_prerun.connect
def task_prerun_handler(signal, sender, task_id, task, args, kwargs, **extras):
    if task != ping:
        time_dict[task_id] = time()

        calc_obj = Calculation.objects.get(pk=args[1])

        calc_obj.status = 1
        calc_obj.save()


@task_postrun.connect
def task_postrun_handler(signal, sender, task_id, task, args, kwargs, retval, state, **extras):
    if task != ping:
        try:
            execution_time = time() - time_dict.pop(task_id)
        except KeyError:
            execution_time = -1

        job_id = args[1]
        calc_obj = Calculation.objects.get(pk=job_id)
        calc_obj.execution_time = int(execution_time)
        calc_obj.date_finished = timezone.now()

        for f in glob.glob(os.path.join(LAB_SCR_HOME, str(job_id)) + '/*/'):
            for ff in glob.glob("{}*.out".format(f)):
                fname = ff.split('/')[-1]
                copyfile(ff, os.path.join(LAB_RESULTS_HOME, str(job_id)) + '/' + fname)

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
'''
@app.task(name='celery.ping')
def ping():
    return 'pong'


