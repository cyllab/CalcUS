import django
import sys
import os
import time
import glob
import subprocess
import shlex
from shutil import copyfile


LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']
LAB_KEY_HOME = os.environ['LAB_KEY_HOME']
LAB_CLUSTER_HOME = os.environ['LAB_CLUSTER_HOME']

GRIMME_SUITE = ['xtb', 'crest', 'xtb4stda', 'stda', 'enso.py', 'anmr']

CONNECTION_CODE = {
            1: "Invalid cluster access",
            2: "Invalid host",
            3: "Could not connect to the server",
            4: "No calcus folder found",

        }

sys.path.append("/home/raphael/LabSandbox")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labsandbox.settings")
django.setup()

import ssh2
from ssh2.session import Session
from ssh2.utils import wait_socket
import socket
from threading import Lock

from frontend.models import *
from frontend import tasks

tasks.REMOTE = True

class ClusterDaemon:

    connections = {}
    locks = {}

    def access_test(self, id):
        for conn in self.connections:
            if conn[0].id == int(id):
                return 0

        try:
            conn = ClusterAccess.objects.get(pk=id)
        except ClusterAccess.DoesNotExist:
            return 1

        a = self.setup_connection(conn)

        if a in [2, 3]:
            return a

        self.locks[a[0].id] = Lock()

        b = self.check_binaries(a)

        if b != 4:
            self.connections[a[0].id] = a
            #self.upload_tasks(a)
            return a
        return b

    def check_binaries(self, conn):
        lock = self.locks[conn[0].id]
        ls_home = tasks.direct_command("ls ~", conn, lock)

        if "calcus" not in ls_home:
            return 4

        ls_calcus = tasks.direct_command("ls ~/calcus", conn, lock)
        for bin in GRIMME_SUITE:
            if bin not in ls_calcus:
                return 4

        _ = tasks.direct_command("mkdir -p ~/calcus/jobs/done", conn, lock)
        return 0

    def system(self, command):
        return subprocess.run(shlex.split(command)).returncode

    def output(self, id, msg):
        with open(os.path.join(LAB_CLUSTER_HOME, 'done', str(id)), 'w') as out:
            out.write(msg)

    def setup_connection(self, conn):
        addr = conn.cluster_address
        keypath = os.path.join(LAB_KEY_HOME, conn.private_key_path)
        username = conn.cluster_username

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((addr, 22))
        except socket.gaierror:
            print("Invalid host")
            return 2

        password = None
        session = Session()
        session.handshake(sock)
        session.set_timeout(5*1000)

        try:
            session.userauth_publickey_fromfile(username, keypath, passphrase="")
        except ssh2.exceptions.AuthenticationError:
            print("Could not connect to cluster {} with username {}".format(addr, username))
            return 3

        sftp = session.sftp_init()
        return [conn, sock, session, sftp]

    def xtb_job(self, calc_id, access_id, calc_obj, args):

        tasks.connections[os.getpid()] = self.connections[int(access_id)]
        tasks.locks[os.getpid()] = self.locks[int(access_id)]

        type, charge, solvent, drawing = args

        type = int(type)

        if type == 0:
            return tasks.geom_opt(calc_id, drawing, charge, solvent, calc_obj=calc_obj)
        elif type == 1:
            return tasks.conf_search(calc_id, drawing, charge, solvent, calc_obj=calc_obj)
        elif type == 2:
            return tasks.uvvis_simple(calc_id, drawing, charge, solvent, calc_obj=calc_obj)
        elif type == 3:
            return tasks.nmr_enso(calc_id, drawing, charge, solvent, calc_obj=calc_obj)
        else:
            print("Unknown type: {}".format(type))
            return 3

    def process_commands(self):
        todo = glob.glob(os.path.join(LAB_CLUSTER_HOME, 'todo/*'))
        for c in todo:
            with open(c) as f:
                lines = f.readlines()
            os.remove(c)
            cmd = lines[0].strip()
            id = int(c.split('/')[-1])

            if cmd == "access_test":
                access_id = int(lines[1])
                r = self.access_test(access_id)
                if r in [1, 2, 3, 4]:
                    self.output(id, "Error: {}".format(CONNECTION_CODE[r]))
                else:
                    self.output(id, "Connection successful")
            else:
                calc_id = lines[1].strip()
                access_id = lines[2].strip()

                calc_obj = Calculation.objects.get(pk=calc_id)
                if cmd == "launch":
                    tasks.connections[os.getpid()] = self.connections
                    retval = self.xtb_job(calc_id, access_id, calc_obj, [i.strip() for i in lines[3:]])
                else:
                    print("Unknown command: {} (command id {})".format(cmd, c.id))
                    continue

                for f in glob.glob(os.path.join(LAB_SCR_HOME, str(calc_id)) + '/*.out'):
                    fname = f.split('/')[-1]
                    copyfile(f, os.path.join(LAB_RESULTS_HOME, str(calc_id)) + '/' + fname)

                if retval == 0:
                    calc_obj.status = 2
                else:
                    calc_obj.status = 3
                    calc_obj.error_message = "Unknown error"

                calc_obj.save()

    def __init__(self):
        for conn in ClusterAccess.objects.all():
            c = self.access_test(conn.id)
            if c not in [1, 2, 3, 4]:
                self.connections[c[0].id] = c
                self.locks[c[0].id] = Lock()
                print("Added cluster access {}".format(c[0].id))
            else:
                print("Error with cluster access: {}".format(CONNECTION_CODE[c]))
        while True:
            self.process_commands()
            print("Still there")
            time.sleep(5)

if __name__ == "__main__":
    a = ClusterDaemon()
