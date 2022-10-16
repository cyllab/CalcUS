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


import os
import unittest
from threading import Thread
import time

from django.test import TransactionTestCase, Client
from django.db import close_old_connections, connection

from .models import *


def redeem(obj, user, stall=0):
    obj.redeem(user, stall=stall)
    connection.close()


class ResourceAllocationTests(TransactionTestCase):
    def testDown(self):
        close_old_connections()

    def test_base_redeem(self):
        u1 = User.objects.create_user(email="U1@test.com", password="1234")
        u2 = User.objects.create_user(email="U2@test.com", password="1234")

        alloc = ResourceAllocation.objects.create(code="AAAA", allocation_seconds=10)

        self.assertEqual(alloc.redeemer, None)

        alloc.redeem(u1)

        alloc.refresh_from_db()
        self.assertEqual(alloc.redeemer, u1)

    def test_threaded_redeem(self):
        u1 = User.objects.create_user(email="U1@test.com", password="1234")
        u2 = User.objects.create_user(email="U2@test.com", password="1234")

        alloc = ResourceAllocation.objects.create(code="AAAA", allocation_seconds=10)

        self.assertEqual(u1.allocated_seconds, 0)
        self.assertEqual(alloc.redeemer, None)

        t = Thread(target=redeem, args=(alloc, u1, 1))
        t.start()
        t.join()

        alloc.refresh_from_db()
        u1.refresh_from_db()
        u2.refresh_from_db()
        self.assertEqual(alloc.redeemer, u1)
        self.assertEqual(u1.allocated_seconds, 10)
        self.assertEqual(u2.allocated_seconds, 0)

    def test_double_redeem(self):
        u1 = User.objects.create_user(email="U1@test.com", password="1234")
        u2 = User.objects.create_user(email="U2@test.com", password="1234")

        alloc = ResourceAllocation.objects.create(code="AAAA", allocation_seconds=10)

        self.assertEqual(alloc.redeemer, None)

        t = Thread(target=redeem, args=(alloc, u1, 0.5))
        t.start()

        time.sleep(0.01)  # Give time to lock the object

        # This should do nothing, since u1 is redeeming the resource already.
        # This call will finish after the past one. Without locking, the redeemer would be u2.
        alloc.redeem(u2, stall=1)
        t.join()

        alloc.refresh_from_db()
        u1.refresh_from_db()
        u2.refresh_from_db()
        self.assertEqual(alloc.redeemer, u1)
        self.assertEqual(u1.allocated_seconds, 10)
        self.assertEqual(u2.allocated_seconds, 0)
