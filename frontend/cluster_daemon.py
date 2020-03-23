import django
import sys
import os
import time
import glob

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']
LAB_KEY_HOME = os.environ['LAB_KEY_HOME']
LAB_CLUSTER_HOME = os.environ['LAB_CLUSTER_HOME']

GRIMME_SUITE = ['xtb', 'crest', 'xtb4stda', 'stda', 'enso.py', 'anmr']

sys.path.append("/home/raphael/LabSandbox")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "labsandbox.settings")
django.setup()

import ssh2
from ssh2.session import Session
from ssh2.utils import wait_socket
import socket

from frontend.models import *

class ClusterDaemon:

    connections = []

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

        return a
        #self.check_binaries(a)

    #def check_binaries(self, conn):


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

        return [conn, sock, session]

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
                if r in [1, 2, 3]:
                    self.output(id, "Error: {}".format(CONNECTION_CODE[r]))
                else:
                    self.output(id, "Connection successful")
                    #self.connections.append(r)


    def __init__(self):

        for conn in ClusterAccess.objects.all():
            c = self.setup_connection(conn)
            if c not in [2, 3]:
                self.connections.append(c)

        while True:
            self.process_commands()
            print("Still there")
            time.sleep(5)

if __name__ == "__main__":
    a = ClusterDaemon()
