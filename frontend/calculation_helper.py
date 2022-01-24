'''
This file of part of CalcUS.

Copyright (C) 2020-2021 Raphaël Robidas

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
'''

from .constants import *
import string


def clean_xyz(xyz):
    return ''.join([x if x in string.printable else ' ' for x in xyz])

def get_xyz_from_Gaussian_input(txt):
    lines = txt.split('\n')
    xyz_lines = []
    ind = 0
    while lines[ind].find("#") == -1:
        ind += 1
    ind += 5

    while ind != len(lines) and lines[ind].strip() != '':
        xyz_lines.append(lines[ind].strip())
        ind += 1

    xyz = "{}\n\n".format(len(xyz_lines))
    xyz += '\n'.join(xyz_lines)
    return xyz
