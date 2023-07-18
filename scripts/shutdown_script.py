#!/usr/local/bin/python

import os

calc_id = os.getenv("CALC_ID", "")
if calc_id == "":
    print("Could not get the calculation ID to reschedule it!")
    exit(0)

os.system("/usr/local/bin/python manage.py reschedule_calc {calc_id}")
