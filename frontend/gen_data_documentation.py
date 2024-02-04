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

from constants import *

TABLE_TEMPLATE = """
<table class="table">
    <thead>
        <tr>
            <th>{}</th>
            {}
        </tr>
    </thead>
    <tbody>
        {}
    </tbody>
</table>"""


def basis_sets():
    softwares = SOFTWARE_BASIS_SETS.keys()
    basis_sets = []
    header = ""
    for software in softwares:
        header += f"<th>{software}</th>"
        for bs in SOFTWARE_BASIS_SETS[software].keys():
            if bs not in basis_sets:
                basis_sets.append(bs)
    body = ""
    for bs in sorted(basis_sets):
        availabilities = ""
        name = ""
        for software in softwares:
            if bs in SOFTWARE_BASIS_SETS[software].keys():
                if name == "":
                    name = SOFTWARE_BASIS_SETS[software][bs]
                availabilities += "<td>X</td>\n"
            else:
                availabilities += "<td></td>\n"

        body += f"""
            <tr>
                <td>{name}</td>
                {availabilities}
            </tr>"""

    print(TABLE_TEMPLATE.format("Basis Set", header, body))


def functionals():
    softwares = SOFTWARE_METHODS.keys()
    functionals = []
    header = ""
    for software in softwares:
        header += f"<th>{software}</th>"
        for f in SOFTWARE_METHODS[software].keys():
            if f not in functionals:
                functionals.append(f)
    body = ""
    for f in sorted(functionals):
        availabilities = ""
        name = ""
        for software in softwares:
            if f in SOFTWARE_METHODS[software].keys():
                if name == "":
                    name = SOFTWARE_METHODS[software][f]
                availabilities += "<td>X</td>\n"
            else:
                availabilities += "<td></td>\n"

        body += f"""
            <tr>
                <td>{name}</td>
                {availabilities}
            </tr>"""

    print(TABLE_TEMPLATE.format("Functionals", header, body))


if __name__ == "__main__":
    basis_sets()
    # functionals()
