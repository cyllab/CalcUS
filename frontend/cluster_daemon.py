"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import django
import sys
import os
import time
import subprocess
import shlex
import redis

from fabric import Connection

import paramiko

import threading
from threading import Lock

from django.utils import timezone
from django.db import close_old_connections

import logging

MAX_RESUME_CALC_ATTEMPT_COUNT = 3

logger = logging.getLogger("cluster_daemon")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(module)s: %(message)s")


class ConnectionCodes:
    SUCCESS = 0
    ALREADY_CONNECTED = 1
    INVALID_CLUSTER_ACCESS = 2
    INVALID_HOST = 3
    COULD_NOT_CONNECT = 4
    NO_CALCUS_FOLDER = 5
    INVALID_KEY_PASSWORD = 6
    SOCKET_RECEIVE_ERROR = 7


CONNECTION_MESSAGES = {
    ConnectionCodes.SUCCESS: "Connected",
    ConnectionCodes.ALREADY_CONNECTED: "Already connected",
    ConnectionCodes.INVALID_CLUSTER_ACCESS: "Invalid cluster access",
    ConnectionCodes.INVALID_HOST: "Invalid host",
    ConnectionCodes.COULD_NOT_CONNECT: "Could not connect to the server",
    ConnectionCodes.NO_CALCUS_FOLDER: "No calcus folder found",
    ConnectionCodes.INVALID_KEY_PASSWORD: "Invalid key password",
    ConnectionCodes.SOCKET_RECEIVE_ERROR: "Unknown connection error",
}
try:
    IS_TEST = os.environ["CALCUS_TEST"]
    if IS_TEST.lower() == "false":
        IS_TEST = False
    else:
        IS_TEST = True
except:
    IS_TEST = False

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
        if id in self.connections:
            return ConnectionCodes.ALREADY_CONNECTED

        try:
            conn = ClusterAccess.objects.get(pk=id)
        except ClusterAccess.DoesNotExist:
            return ConnectionCodes.INVALID_CLUSTER_ACCESS

        return self.setup_connection(conn, password)

    def check_binaries(self, conn):
        lock = self.locks[conn[0].id]
        ls_home = tasks.direct_command("ls ~", conn, lock)
        if isinstance(ls_home, ErrorCodes):
            logger.warning(
                f"Could not check the presence of a remote calcus folder: {ls_home}"
            )
        else:
            if "calcus" not in ls_home:
                return ConnectionCodes.NO_CALCUS_FOLDER

        return ""

    def system(self, command):
        return subprocess.run(shlex.split(command)).returncode

    def setup_connection(self, conn, password):
        addr = conn.cluster_address
        keypath = os.path.join(CALCUS_KEY_HOME, str(conn.id))
        username = conn.cluster_username

        try:
            _conn = Connection(
                addr,
                user=username,
                port=22,
                connect_kwargs={"key_filename": keypath, "passphrase": password},
            )
        except paramiko.ssh_exception.AuthenticationException:
            logger.warning(
                f"Could not connect to cluster {addr} with username {username}"
            )
            return ConnectionCodes.COULD_NOT_CONNECT
        except Exception as e:
            logger.warning(
                "Could not connect to cluster {} with username {}: exception {}".format(
                    addr, username, e
                )
            )
            return ConnectionCodes.COULD_NOT_CONNECT

        self.locks[conn.id] = Lock()

        try:
            b = self.check_binaries([conn, _conn])
        except paramiko.ssh_exception.SSHException:
            logger.warning(
                f"Could not connect to cluster {addr} with username {username}: invalid password"
            )
            del self.locks[conn.id]
            return ConnectionCodes.INVALID_KEY_PASSWORD

        if b == ConnectionCodes.NO_CALCUS_FOLDER:
            del self.locks[conn.id]
            return b

        return [conn, _conn]

    def delete_access(self, access_id):
        try:
            conn = self.connections[access_id]
        except KeyError:
            logger.warning(f"Cannot delete connection {access_id}: no such connection")
            return

        conn = self.connections[access_id][0]
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id) + ".pub"))
        os.remove(os.path.join(CALCUS_KEY_HOME, str(conn.id)))

        try:
            del self.connections[access_id]
        except KeyError:
            logger.warning(f"No connection with id {access_id} in memory")
        try:
            del self.locks[access_id]
        except KeyError:
            logger.warning(f"No lock for connection with id {access_id} in memory")

    def job(self, calc):
        access_id = calc.order.resource.id
        tasks.connections[threading.get_ident()] = self.connections[access_id]
        tasks.locks[threading.get_ident()] = self.locks[access_id]
        tasks.remote_dirs[threading.get_ident()] = "/home/{}/scratch/calcus/{}".format(
            self.connections[access_id][0].cluster_username, calc.id
        )

        return tasks.run_calc(calc.id)

    def connect(self, access_id, password):
        logger.info(f"Connecting ({access_id})")

        c = self.access_test(access_id, password)

        try:
            access = ClusterAccess.objects.get(pk=access_id)
        except ClusterAccess.DoesNotExist:
            access = None

        if not isinstance(c, int):
            if not access:
                logger.warning(f"ClusterAccess with id {access_id} does not exist")
                return
            self.connections[access_id] = c
            self.locks[access_id] = Lock()
            logger.info(f"Connected to cluster access {access_id}")

            access.last_connected = timezone.now()
            access.status = "Connected"
            access.save()

            profile = access.owner

            for c in (
                Calculation.objects.filter(
                    local=False, order__resource=access, order__author=profile
                )
                .exclude(status=3)
                .exclude(status=2)
            ):
                t = threading.Thread(target=self.resume_calc, args=(c,))
                t.start()
        else:
            logger.warning(
                f"Error with cluster access {access_id}: {CONNECTION_MESSAGES[c]}"
            )
            if access:
                access.status = CONNECTION_MESSAGES[c]
                access.save()

    def disconnect(self, access_id):
        logger.info(f"Disconnecting cluster access {access_id}")
        if access_id in self.connections:
            del self.connections[access_id]
        if access_id in self.locks:
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

        logger.info(f"Disconnected cluster access {access_id}")
        close_old_connections()

    def resume_calc(self, c, attempt_count=1):
        pid = threading.get_ident()
        tasks.connections[pid] = self.connections
        self.calculations[c.id] = pid
        try:
            retval = self.job(c)
        except AttributeError:
            if attempt_count >= MAX_RESUME_CALC_ATTEMPT_COUNT:
                logger.warning("Maximum number of resume attempts reached!")
                return
            else:
                time.sleep(1)
                return self.resume_calc(c, attempt_count + 1)

        if c.id in self.calculations:
            del self.calculations[c.id]

        try:
            del tasks.connections[pid]
            del tasks.locks[pid]
        except KeyError:  # already deleted when disconnnected from cluster
            pass

        close_old_connections()

    def process_command(self, body):
        lines = body.decode("UTF-8").split("&")

        if lines[0].strip() == "stop":
            logger.info("Stopping the daemon")
            if not IS_TEST:
                for conn_id in list(self.connections.keys()):
                    self.disconnect(conn_id)

            self.stopped = True
            return

        t = threading.Thread(target=self._process_command, args=(lines,))
        t.start()

    def _process_command(self, lines):
        cmd = lines[0].strip()

        if cmd == "connect":
            access_id = lines[1]
            password = lines[2]
            r = self.connect(access_id, password)
            if r in [1, 2, 3, 4, 5]:
                logger.warning(
                    f"Error with connection {access_id}: {CONNECTION_MESSAGES[r]}"
                )
            else:
                logger.info(f"Connection successful ({access_id})")
        elif cmd == "disconnect":
            access_id = lines[1]
            self.disconnect(access_id)
        elif cmd == "delete_access":
            access_id = lines[1]
            logger.info(f"Deleting connection {access_id}")
            self.delete_access(access_id)
        else:
            calc_id = lines[1].strip()

            try:
                calc = Calculation.objects.get(pk=calc_id)
            except Calculation.DoesNotExist:
                logger.warning(f"Could not find calculation {calc_id}")
                return

            if cmd == "kill":
                logger.info(f"Killing calculation {calc.id}")
                if calc.order.resource is not None:
                    if calc.id in self.calculations:
                        pid = self.calculations[calc.id]
                        if pid not in tasks.kill_sig:
                            tasks.kill_sig.append(pid)
                    else:
                        self.cancelled.append(calc.id)
                else:
                    # Special case where the resource has been deleted.
                    # As such, no thread will ever process the kill signal.
                    logger.info(
                        f"Resource is null for calculation {calc.id}, cancelling directly"
                    )
                    calc.status = 3
                    calc.error_message = "Job cancelled"
                    calc.save()
                return

            access = calc.order.resource

            if access is None:
                logger.warning(
                    f"Cannot load log: resource is null for calculation {calc.id}"
                )
                return

            if access.id not in self.connections:
                logger.warning(
                    f"Cannot execute command: access {access.id} not connected"
                )
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

                if pid in tasks.connections:
                    del tasks.connections[pid]
            elif cmd == "load_log":
                if calc.id in self.calculations:
                    try:
                        remote_conn = self.connections[access.id]
                    except KeyError:
                        logger.warning("Cannot load log: invalid access")

                    if calc.parameters.software == "Gaussian":
                        files = ["calc.log"]
                    elif calc.parameters.software == "ORCA":
                        files = ["calc.out", "calc_trj.xyz"]
                    elif calc.parameters.software == "xtb":
                        files = ["calc.out", "xtbopt.log"]
                    else:
                        raise Exception(f"Unknown software: {calc.parameters.software}")

                    for f in files:
                        tasks.sftp_get(
                            f"/home/{access.cluster_username}/scratch/calcus/{calc.id}/{f}",
                            os.path.join(CALCUS_SCR_HOME, str(calc.id), f),
                            remote_conn,
                            self.locks[access.id],
                        )

                else:
                    logger.warning("Cannot load log: unknown calculation")
                    logger.debug(f"Known calculations: \n {self.calculations}")
                    return
            else:
                logger.warning(f"Unknown command: {cmd}")
                return

    def ping_daemon(self):
        logger.info("Starting the ping daemon")
        while True:
            for i in range(300):
                if self.stopped:
                    return
                time.sleep(1)

            for conn_name in list(self.connections.keys()):
                access, conn = self.connections[conn_name]

                access.refresh_from_db()
                if access.last_connected - timezone.now() > timezone.timedelta(
                    minutes=15
                ):
                    logger.warning(
                        f"Access {access.id} has not pinged the remote server in 15 minutes, automatically disconnecting..."
                    )
                    self.disconnect(access.id)
                    continue

                access.last_connected = timezone.now()
                access.status = "Connected"
                access.save()

    def __init__(self):
        tasks.REMOTE = True

        if not IS_TEST:
            t = threading.Thread(target=self.ping_daemon)
            t.start()

        connection = redis.Redis(host="redis", port=6379, db=2)

        logger.info("Starting to listen to cluster commands")
        while not self.stopped:
            msg = connection.blpop("cluster", 30)
            if msg:
                if isinstance(msg[1], int):
                    continue
                self.process_command(msg[1])

        logger.info("Daemon closed")


if __name__ == "__main__":
    a = ClusterDaemon()
