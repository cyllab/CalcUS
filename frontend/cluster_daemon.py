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

from django.conf import settings

RABBITMQ_USERNAME = os.environ["CALCUS_RABBITMQ_USERNAME"]
RABBITMQ_PASSWORD = os.environ["CALCUS_RABBITMQ_PASSWORD"]

import code, traceback, signal, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]  %(module)s: %(message)s")
logger = logging.getLogger(__name__)

GRIMME_SUITE = ['xtb', 'crest', 'xtb4stda', 'stda', 'enso.py', 'anmr']

CONNECTION_CODE = {
            0: "Already connected",
            1: "Invalid cluster access",
            2: "Invalid host",
            3: "Could not connect to the server",
            4: "No calcus folder found",
            5: "Invalid key password",
        }
try:
    is_test = os.environ['CALCUS_TEST']
    if is_test.lower() == "false":
        is_test = False
    else:
        is_test = True
except:
    is_test = False

if not is_test:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calcus.settings")
    django.setup()


from frontend.models import *
from frontend.environment_variables import *
from frontend import tasks


class ClusterDaemon:

    connections = {}
    locks = {}
    calculations = {}
    cancelled = []
    stopped = False

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

    def setup_connection(self, conn, password):
        addr = conn.cluster_address
        keypath = os.path.join(CALCUS_KEY_HOME, str(conn.id))
        username = conn.cluster_username

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((addr, 22))
        except socket.gaierror:
            logger.warning("Invalid host")
            return 2

        session = Session()
        session.handshake(sock)
        session.set_timeout(20*1000)
        session.keepalive_config(True, 60)

        try:
            session.userauth_publickey_fromfile(username, keypath, passphrase=password)
        except ssh2.exceptions.AuthenticationError:
            logger.warning("Could not connect to cluster {} with username {}".format(addr, username))
            return 3
        except ssh2.exceptions.FileError:
            logger.warning("Invalid password for cluster {} with username {}".format(addr, username))
            return 5

        sftp = session.sftp_init()
        return [conn, sock, session, sftp]

    def delete_access(self, access_id):
        try:
            conn = self.connections[access_id]
        except KeyError:
            logger.warning("Cannot delete connection {}: no such connection".format(access_id))
            return

        conn = self.connections[access_id][0]
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id) + '.pub'))
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id)))

        try:
            del self.connections[access_id]
        except KeyError:
            logger.warning("No connection with id {} in memory".format(access_id))
        try:
            del self.locks[access_id]
        except KeyError:
            logger.warning("No lock for connection with id {} in memory".format(access_id))

    def job(self, calc):
        access_id = calc.order.resource.id
        tasks.connections[threading.get_ident()] = self.connections[access_id]
        tasks.locks[threading.get_ident()] = self.locks[access_id]
        tasks.remote_dirs[threading.get_ident()] = "/home/{}/scratch/calcus/{}".format(self.connections[access_id][0].cluster_username, calc.id)

        return tasks.run_calc(calc.id)

    def connect(self, access_id, password):
        logger.info("Connecting ({})".format(access_id))

        c = self.access_test(access_id, password)

        access = ClusterAccess.objects.get(pk=access_id)
        if not isinstance(c, int):
            self.connections[access_id] = c
            self.locks[access_id] = Lock()
            logger.info("Connected to cluster access {}".format(access_id))

            access.last_connected = timezone.now()
            access.status = "Connected"

            profile = access.owner

            for c in Calculation.objects.filter(local=False,order__resource=access,order__author=profile).exclude(status=3).exclude(status=2):
                t = threading.Thread(target=self.resume_calc, args=(c,))
                t.start()
        else:
            logger.warning("Error with cluster access {}: {}".format(access_id, CONNECTION_CODE[c]))
            access.status = CONNECTION_CODE[c]

        access.save()

    def disconnect(self, access_id):
        logger.info("Disconnecting cluster access {}".format(access_id))
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

        logger.info("Disconnected cluster access {}".format(access_id))

    def resume_calc(self, c):

        pid = threading.get_ident()
        tasks.connections[pid] = self.connections
        self.calculations[c.id] = pid
        retval = self.job(c)

        if c.id in self.calculations:
            del self.calculations[c.id]

        try:
            del tasks.connections[pid]
            del tasks.locks[pid]
        except KeyError:#already deleted when disconnnected from cluster
            pass

    def process_command(self, ch, method, properties, body):
        lines = body.decode('UTF-8').split('\n')

        if lines[0].strip() == "stop":
            logger.info("Stopping the daemon")
            for conn_id in list(self.connections.keys()):
                self.disconnect(conn_id)

            ch.stop_consuming()
            return
        t = threading.Thread(target=self._process_command, args=(lines,))
        t.start()

    def _process_command(self, lines):
        cmd = lines[0].strip()

        if cmd == "connect":
            access_id = int(lines[1])
            password = lines[2]
            r = self.connect(access_id, password)
            if r in [1, 2, 3, 4, 5]:
                logger.warning("Error with connection {}: {}".format(access_id, CONNECTION_CODE[r]))
            else:
                logger.info("Connection successful ({})".format(access_id))
        elif cmd == "disconnect":
            access_id = int(lines[1])
            self.disconnect(access_id)
        elif cmd == "delete_access":
            access_id = int(lines[1])
            logger.info("Deleting connection {}".format(access_id))
            self.delete_access(access_id)
        else:
            calc_id = int(lines[1].strip())

            try:
                calc = Calculation.objects.get(pk=calc_id)
            except Calculation.DoesNotExist:
                logger.warning("Could not find calculation {}".format(calc_id))
                return

            access = calc.order.resource

            if access is None:
                logger.warning("Cannot load log: resource is null for calculation {}".format(calc.id))
                return

            if access.id not in self.connections.keys():
                logger.warning("Cannot execute command: access {} not connected".format(access.id))
                return

            if cmd == "launch":
                if calc.id in self.cancelled:
                    self.cancelled.remove(calc.id)
                    calc.status = 3
                    calc.save()
                    return
                pid = threading.get_ident()
                tasks.connections[pid] = self.connections
                self.calculations[calc.id] = pid
                retval = self.job(calc)

                del self.calculations[calc.id]

                if pid in tasks.connections.keys():
                    del tasks.connections[pid]
            elif cmd == "kill":
                logger.info("Killing calculation {}".format(calc.id))
                if calc.id in self.calculations.keys():
                    pid = self.calculations[calc.id]
                    if pid not in tasks.kill_sig:
                        tasks.kill_sig.append(pid)
                else:
                    self.cancelled.append(calc.id)
            elif cmd == "load_log":
                if calc.id in self.calculations:
                    try:
                        remote_conn = self.connections[access.id]
                    except KeyError:
                        logger.warning("Cannot load log: invalid access")

                    tasks.sftp_get("/home/{}/scratch/calcus/{}/calc.log".format(access.cluster_username, calc.id), os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc.log"), remote_conn, self.locks[access.id])

                else:
                    logger.warning("Cannot load log: unknown calculation")
                    logger.debug("Known calculations: \n {}".format(self.calculations))
                    return
            else:
                logger.warning("Unknown command: {}".format(cmd))
                return

    def keep_alive(self):
        logger.info("Starting the keepalive daemon")
        while True:
            for i in range(60):
                if self.stopped:
                    return
                time.sleep(1)

            for conn_name in list(self.connections.keys()):
                access, sock, session, sftp = self.connections[conn_name]
                success = False
                for i in range(5):
                    try:
                        session.keepalive_send()
                    except ssh2.exceptions.SocketSendError:
                        logger.info("Could not send keepalive signal, trying again")
                        time.sleep(1)
                    else:
                        success = True
                        break

                if not success:
                    logger.warning("Could not keep connection {} alive".format(conn_name))
                    tasks.send_cluster_command("disconnect\n{}\n".format(access.id))
                else:
                    access.last_connected = timezone.now()
                    access.status = "Connected"
                    access.save()


    def __init__(self):
        if not is_test:
            t = threading.Thread(target=self.keep_alive)
            t.start()

        tasks.REMOTE = True

        if docker:
            if not is_test:
                time.sleep(10)
            credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbit', credentials=credentials))
        else:
            connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        chan = connection.channel()
        chan.queue_declare(queue='cluster')
        chan.basic_consume(queue='cluster', auto_ack=True, on_message_callback=self.process_command)
        logger.info("Starting to listen to cluster commands")
        chan.start_consuming()
        chan.cancel()
        chan.close()
        connection.close()
        self.stopped = True
        logger.info("Daemon closed")

if __name__ == "__main__":
    a = ClusterDaemon()

