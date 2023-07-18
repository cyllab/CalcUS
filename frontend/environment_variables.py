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

IS_TEST = "CALCUS_TEST" in os.environ
IS_COMPUTE = "CALCUS_COMPUTE" in os.environ

if IS_TEST:
    if "GITHUB_WORKSPACE" in os.environ:
        prefix = os.environ["GITHUB_WORKSPACE"]
        CALCUS_CACHE_HOME = os.path.join(prefix, "frontend", "tests", "cache")
    else:
        CALCUS_CACHE_HOME = "/calcus/cache"
        prefix = ""

    CALCUS_SCR_HOME = os.path.join(
        prefix, os.environ.get("CALCUS_TEST_SCR_HOME", "scratch/scr")
    )
    CALCUS_KEY_HOME = os.path.join(
        prefix, os.environ.get("CALCUS_TEST_KEY_HOME", "scratch/keys")
    )
else:
    CALCUS_KEY_HOME = os.getenv("CALCUS_KEY_HOME", "")

    if "CALCUS_CLOUD" in os.environ:
        CALCUS_SCR_HOME = os.getenv("CALCUS_SCR_HOME", "/tmp")
    elif IS_COMPUTE:
        CALCUS_SCR_HOME = os.getenv("CALCUS_SCR_HOME", "/calcus/")
    else:
        CALCUS_SCR_HOME = os.getenv("CALCUS_SCR_HOME", "")

PAL = int(os.getenv("NUM_CPU", "1"))

STACKSIZE = os.environ.get("OMP_STACKSIZE", "1G")

if STACKSIZE.find("G") != -1:
    STACKSIZE = int(STACKSIZE.replace("G", "")) * 1024
elif STACKSIZE.find("M") != -1:
    STACKSIZE = int(STACKSIZE.replace("M", ""))

MEM = int(PAL) * STACKSIZE
EBROOTORCA = os.environ.get("EBROOTORCA", "")
