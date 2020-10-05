import django
import sys
import os
import time
import glob
import subprocess
import shlex
import pika
from shutil import copyfile

import ssh2
from ssh2.session import Session
import socket
import threading
from threading import Lock

from django.utils.timezone import now

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
            5: "Invalid key password",
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
    cancelled = []

    def log(self, msg):
        print("{} - {}".format(now(), msg), flush=True)

    def access_test(self, id, password):
        if id in self.connections.keys():
            return 0

        try:
            conn = ClusterAccess.objects.get(pk=id)
        except ClusterAccess.DoesNotExist:
            return 1

        a = self.setup_connection(conn, password)

        if isinstance(a, int):
            return a

        self.locks[a[0].id] = Lock()

        b = self.check_binaries(a)

        if not isinstance(b, int):
            self.connections[a[0].id] = a
            return a
        return b

    def check_binaries(self, conn):
        lock = self.locks[conn[0].id]
        ls_home = tasks.direct_command("ls ~", conn, lock)

        if "calcus" not in ls_home:
            return 4

        return ""

    def system(self, command):
        return subprocess.run(shlex.split(command)).returncode

    def output(self, id, msg):
        with open(os.path.join(CALCUS_CLUSTER_HOME, 'done', str(id)), 'w') as out:
            out.write(msg)

    def setup_connection(self, conn, password):
        addr = conn.cluster_address
        keypath = os.path.join(CALCUS_KEY_HOME, str(conn.id))
        username = conn.cluster_username

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((addr, 22))
        except socket.gaierror:
            self.log("Invalid host")
            return 2

        session = Session()
        session.handshake(sock)
        session.set_timeout(20*1000)
        session.keepalive_config(True, 60)

        try:
            session.userauth_publickey_fromfile(username, keypath, passphrase=password)
        except ssh2.exceptions.AuthenticationError:
            self.log("Could not connect to cluster {} with username {}".format(addr, username))
            return 3
        except ssh2.exceptions.FileError:
            self.log("Invalid password for cluster {} with username {}".format(addr, username))
            return 5

        sftp = session.sftp_init()
        return [conn, sock, session, sftp]

    def delete_access(self, access_id):
        try:
            conn = self.connections[access_id]
        except KeyError:
            self.log("Cannot delete connection {}: no such connection".format(access_id))
            return
        conn = self.connections[access_id][0]
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id) + '.pub'))
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id)))

        try:
            del self.connections[access_id]
        except KeyError:
            self.log("No connection with id {} in memory".format(access_id))
        try:
            del self.locks[access_id]
        except KeyError:
            self.log("No lock for connection with id {} in memory".format(access_id))

    def job(self, calc_id, access_id):
        tasks.connections[threading.get_ident()] = self.connections[access_id]
        tasks.locks[threading.get_ident()] = self.locks[access_id]
        tasks.remote_dirs[threading.get_ident()] = "/home/{}/scratch/calcus/{}".format(self.connections[access_id][0].cluster_username, calc_id)

        return tasks.run_calc(calc_id)

    def connect(self, access_id, password):
        self.log("Connecting ({})".format(access_id))

        c = self.access_test(access_id, password)

        access = ClusterAccess.objects.get(pk=access_id)
        if not isinstance(c, int):
            self.connections[access_id] = c
            self.locks[access_id] = Lock()
            self.log("Connected to cluster access {}".format(access_id))

            access.last_connected = timezone.now()
            access.status = "Connected"

            profile = access.owner

            for c in Calculation.objects.filter(local=False,order__resource=access,order__author=profile).exclude(status=3).exclude(status=2):
                t = threading.Thread(target=self.resume_calc, args=(c,))
                t.start()
        else:
            self.log("Error with cluster access {}: {}".format(access_id, CONNECTION_CODE[c]))
            access.status = CONNECTION_CODE[c]

        access.save()

    def disconnect(self, access_id):
        self.log("Disconnecting cluster access {}".format(access_id))
        if access_id in self.connections.keys():
            del self.connections[access_id]
        if access_id in self.locks.keys():
            del self.locks[access_id]

        pid_to_remove = []
        for pid, obj in tasks.connections.items():
            if obj[0].id == access_id:
                pid_to_remove.append(pid)

        for pid in pid_to_remove:
            del tasks.connections[pid]
            del tasks.locks[pid]

        access = ClusterAccess.objects.get(pk=access_id)
        access.last_connected = timezone.now() - timezone.timedelta(1)
        access.status = ""
        access.save()

        self.log("Disconnected cluster access {}".format(access_id))

    def resume_calc(self, c):
        pid = threading.get_ident()
        tasks.connections[pid] = self.connections
        self.calculations[c.id] = pid
        retval = self.job(c.id, c.order.resource.id)

        del self.calculations[c.id]

        try:
            del tasks.connections[pid]
            del tasks.locks[pid]
        except KeyError:#already deleted when disconnnected from cluster
            pass

    def process_command(self, ch, method, properties, body):
        lines = body.decode('UTF-8').split('\n')
        t = threading.Thread(target=self._process_command, args=(lines,))
        t.start()


    def _process_command(self, lines):
        cmd = lines[0].strip()

        if cmd == "connect":
            access_id = int(lines[1])
            password = lines[2]
            r = self.connect(access_id, password)
            if r in [1, 2, 3, 4]:
                self.output(id, "Error: {}".format(CONNECTION_CODE[r]))
            else:
                self.output(id, "Connection successful")
        elif cmd == "disconnect":
            access_id = int(lines[1])
            self.disconnect(access_id)
        elif cmd == "delete_access":
            access_id = int(lines[1])
            self.log("Deleting connection {}".format(access_id))
            self.delete_access(access_id)
        else:
            calc_id = int(lines[1].strip())
            access_id = int(lines[2].strip())

            if access_id not in self.connections.keys():
                self.log("Cannot execute command: access {} not connected".format(access_id))
                return

            if cmd == "launch":
                if calc_id in self.cancelled:
                    self.cancelled.remove(calc_id)
                    calc = Calculation.objects.get(pk=calc_id)
                    calc.status = 3
                    calc.save()
                    return
                pid = threading.get_ident()
                tasks.connections[pid] = self.connections
                self.calculations[calc_id] = pid
                retval = self.job(calc_id, access_id)
                del self.calculations[calc_id]
                del tasks.connections[pid]
            elif cmd == "kill":
                self.log("Killing calculation {}".format(calc_id))
                if calc_id in self.calculations.keys():
                    pid = self.calculations[calc_id]
                    tasks.kill_sig.append(pid)
                else:
                    self.cancelled.append(calc_id)
            elif cmd == "load_log":
                if calc_id in self.calculations:
                    try:
                        calc = Calculation.objects.get(pk=calc_id)
                    except Calculation.DoesNotExist:
                        self.log("Cannot load log: invalid calculation")

                    try:
                        access = ClusterAccess.objects.get(pk=access_id)
                    except ClusterAccess.DoesNotExist:
                        self.log("Cannot load log: invalid access object")

                    try:
                        remote_conn = self.connections[access_id]
                    except KeyError:
                        self.log("Cannot load log: invalid access")

                    tasks.sftp_get("/scratch/{}/calcus/{}/calc.log".format(access.cluster_username, calc.id), os.path.join(CALCUS_SCR_HOME, str(calc_id), "calc.log"), remote_conn, self.locks[access_id])

                else:
                    self.log("Cannot load log: unknown calculation")
                    self.log("Known calculations:")
                    self.log(self.calculations)
                    return
            else:
                self.log("Unknown command: {}".format(cmd))
                return

    def keep_alive(self):
        ind = 0
        self.log("Starting the keepalive daemon")
        while True:
            time.sleep(5)
            ind += 1

            if ind % 12 == 0:
                for conn_name in self.connections.keys():
                    conn, sock, session, sftp = self.connections[conn_name]
                    success = False
                    for i in range(5):
                        try:
                            session.keepalive_send()
                        except ssh2.exceptions.SocketSendError:
                            self.log("Could not send keepalive signal, trying again")
                            time.sleep(1)
                        else:
                            success = True
                            break
                    if not success:
                        self.log("Could not keep connection {} alive".format(conn_name))

    def __init__(self):
        t = threading.Thread(target=self.keep_alive)
        t.start()

        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        chan = connection.channel()
        chan.queue_declare(queue='cluster')
        chan.basic_consume(queue='cluster', auto_ack=True, on_message_callback=self.process_command)
        self.log("Starting to listen to cluster commands")
        chan.start_consuming()

if __name__ == "__main__":
    a = ClusterDaemon()
