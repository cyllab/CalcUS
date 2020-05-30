import django
import sys
import os
import time
import glob
import subprocess
import shlex
from shutil import copyfile

import ssh2
from ssh2.session import Session
import socket
import threading
from threading import Lock

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False

if is_test:
    CALCUS_SCR_HOME = os.environ['CALCUS_TEST_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_TEST_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_TEST_KEY_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_TEST_CLUSTER_HOME']
else:
    CALCUS_SCR_HOME = os.environ['CALCUS_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_KEY_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_CLUSTER_HOME']

GRIMME_SUITE = ['xtb', 'crest', 'xtb4stda', 'stda', 'enso.py', 'anmr']

CONNECTION_CODE = {
            1: "Invalid cluster access",
            2: "Invalid host",
            3: "Could not connect to the server",
            4: "No calcus folder found",

        }
if is_test:
    pass
else:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calcus.settings")
    django.setup()

from frontend.models import *
from frontend import tasks

tasks.REMOTE = True

class ClusterDaemon:

    connections = {}
    locks = {}
    calculations = {}

    def access_test(self, id):
        for conn in self.connections:
            if self.connections[conn][0].id == int(id):
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
        with open(os.path.join(CALCUS_CLUSTER_HOME, 'done', str(id)), 'w') as out:
            out.write(msg)

    def setup_connection(self, conn):
        addr = conn.cluster_address
        keypath = os.path.join(CALCUS_KEY_HOME, conn.private_key_path)
        username = conn.cluster_username

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((addr, 22))
        except socket.gaierror:
            print("Invalid host")
            return 2

        session = Session()
        session.handshake(sock)
        session.set_timeout(20*1000)
        session.keepalive_config(True, 60)

        try:
            session.userauth_publickey_fromfile(username, keypath, passphrase="")
        except ssh2.exceptions.AuthenticationError:
            print("Could not connect to cluster {} with username {}".format(addr, username))
            return 3

        with open(os.path.join(CALCUS_CLUSTER_HOME, 'connections', str(conn.id)), 'w') as out:
            out.write("Connected\n{}\n".format(int(time.time())))

        sftp = session.sftp_init()
        return [conn, sock, session, sftp]

    def delete_access(self, access_id):
        try:
            conn = self.connections[int(access_id)]
        except KeyError:
            print("Cannot delete connection {}: no such connection".format(access_id))
            return
        conn = self.connections[int(access_id)][0]
        os.remove(os.path.join(CALCUS_KEY_HOME, conn.public_key_path))
        os.remove(os.path.join(CALCUS_KEY_HOME, conn.private_key_path))

        del self.connections[int(access_id)]
        del self.locks[int(access_id)]

    def job(self, calc_id, access_id):

        tasks.connections[threading.get_ident()] = self.connections[int(access_id)]
        tasks.locks[threading.get_ident()] = self.locks[int(access_id)]
        tasks.remote_dirs[threading.get_ident()] = "/home/{}/scratch/calcus/{}".format(self.connections[int(access_id)][0].cluster_username, calc_id)

        return tasks.run_calc(calc_id)

    def test_connection(self, conn_name):
        print("Testing connection {}".format(conn_name))
        conn, sock, session, sftp = self.connections[conn_name]
        lock = self.locks[conn_name]
        output = tasks.direct_command("ls", self.connections[conn_name], lock)
        if isinstance(output, int):
            print("Detected connection failure with {}".format(conn_name))
            a = self.setup_connection(conn)
            if a in [2, 3]:
                print("Failed to reconnect with {}".format(conn_name))
            else:
                print("Connection established with {}".format(conn_name))
                self.connections[conn_name] = a
        else:
            print("Connection normal for {}".format(conn_name))

    def process_command(self, c):
        with open(c) as f:
            lines = f.readlines()
        os.remove(c)
        cmd = lines[0].strip()
        id = int(c.split('/')[-1])

        if cmd == "access_test":
            access_id = int(lines[1])
            print("Testing connection {}".format(access_id))
            r = self.access_test(access_id)
            if r in [1, 2, 3, 4]:
                self.output(id, "Error: {}".format(CONNECTION_CODE[r]))
            else:
                self.output(id, "Connection successful")
        elif cmd == "delete_access":
            access_id = int(lines[1])
            print("Deleting connection {}".format(access_id))
            self.delete_access(access_id)
        else:
            calc_id = lines[1].strip()
            access_id = lines[2].strip()

            if cmd == "launch":
                pid = threading.get_ident()
                tasks.connections[pid] = self.connections
                self.calculations[calc_id] = pid
                retval = self.job(calc_id, access_id)
            elif cmd == "kill":
                pid = self.calculations[calc_id]
                tasks.kill_sig.append(pid)
            else:
                print("Unknown command: {} (command id {})".format(cmd, c.id))
                return

    def __init__(self):
        for conn in ClusterAccess.objects.all():
            print("Trying to add access {}".format(conn.id))
            c = self.access_test(conn.id)
            if c not in [0, 1, 2, 3, 4]:
                self.connections[c[0].id] = c
                self.locks[c[0].id] = Lock()
                print("Added cluster access {}".format(c[0].id))
            elif c == 0:
                pass
            else:
                print("Error with cluster access: {}".format(CONNECTION_CODE[c]))
        ind = 1
        print("Startup complete")
        while True:
            todo = glob.glob(os.path.join(CALCUS_CLUSTER_HOME, 'todo/*'))
            for c in todo:
                t = threading.Thread(target=self.process_command, args=(c,))
                t.start()
            time.sleep(5)

            ind += 1

            if ind % 12 == 0:
                for conn_name in self.connections.keys():
                    conn, sock, session, sftp = self.connections[conn_name]
                    session.keepalive_send()

            if ind % 60 == 0:
                ind = 1
                for conn_name in self.connections.keys():
                    conn, sock, session, sftp = self.connections[conn_name]
                    with open(os.path.join(CALCUS_CLUSTER_HOME, 'connections', str(conn.id)), 'w') as out:
                        out.write("Connected\n{}\n".format(int(time.time())))

if __name__ == "__main__":
    a = ClusterDaemon()
