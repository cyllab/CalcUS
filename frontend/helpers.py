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

from .constants import *
import string
import secrets
from django.conf import settings

from xkcdpass import xkcd_password as xp

full_alphabet = string.ascii_letters + string.digits


def clean_xyz(xyz):
    return "".join([x if x in string.printable else " " for x in xyz])


def get_xyz_from_Gaussian_input(txt):
    lines = txt.split("\n")
    xyz_lines = []
    ind = 0
    while lines[ind].find("#") == -1:
        ind += 1
    ind += 5

    while ind != len(lines) and lines[ind].strip() != "":
        xyz_lines.append(lines[ind].strip())
        ind += 1

    xyz = f"{len(xyz_lines)}\n\n"
    xyz += "\n".join(xyz_lines)
    return xyz


def get_xyz_from_cube(cube):
    lines = cube.split("\n")
    ind = 1
    sline = lines[ind].strip().split()
    xyz = ""
    while len(sline) != 5:
        ind += 1
        sline = lines[ind].strip().split()
    start_ind = ind

    while len(sline) == 5:
        xyz += f"{ATOMIC_SYMBOL[int(sline[0])]} {float(sline[2])*BOHR_VAL} {float(sline[3])*BOHR_VAL} {float(sline[4])*BOHR_VAL}\n"
        ind += 1
        sline = lines[ind].strip().split()

    xyz = f"{ind-start_ind}\n\n{xyz}"
    return xyz


def get_random_string(n=16):
    return "".join(secrets.choice(full_alphabet) for i in range(n))


def get_random_readable_code(n=5):
    wordfile = xp.locate_wordfile()
    words = xp.generate_wordlist(wordfile=wordfile, min_length=n, max_length=n + 2)
    return xp.generate_xkcdpassword(words)


def job_triage(calc):
    if calc.step.name in ["Conformational Search", "Constrained Conformational Search"]:
        nproc = 8
    else:
        natoms = calc.structure.xyz_structure.count("\n") - 2
        if natoms > 100:
            nproc = 4
        else:
            nproc = 1

    user_type = calc.order.author.user_type

    return (
        min(settings.RESOURCE_LIMITS[user_type]["nproc"], nproc),
        settings.RESOURCE_LIMITS[user_type]["time"] * 60,
    )
