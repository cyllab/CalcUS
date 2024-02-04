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

import periodictable

pos = {
    1: [1, 1],
    2: [18, 1],
    3: [1, 2],
    4: [2, 2],
    5: [13, 2],
    6: [14, 2],
    7: [15, 2],
    8: [16, 2],
    9: [17, 2],
    10: [18, 2],
    11: [1, 3],
    12: [2, 3],
    13: [13, 3],
    14: [14, 3],
    15: [15, 3],
    16: [16, 3],
    17: [17, 3],
    18: [18, 3],
    19: [1, 4],
    20: [2, 4],
    21: [3, 4],
    22: [4, 4],
    23: [5, 4],
    24: [6, 4],
    25: [7, 4],
    26: [8, 4],
    27: [9, 4],
    28: [10, 4],
    29: [11, 4],
    30: [12, 4],
    31: [13, 4],
    32: [14, 4],
    33: [15, 4],
    34: [16, 4],
    35: [17, 4],
    36: [18, 4],
    37: [1, 5],
    38: [2, 5],
    39: [3, 5],
    40: [4, 5],
    41: [5, 5],
    42: [6, 5],
    43: [7, 5],
    44: [8, 5],
    45: [9, 5],
    46: [10, 5],
    47: [11, 5],
    48: [12, 5],
    49: [13, 5],
    50: [14, 5],
    51: [15, 5],
    52: [16, 5],
    53: [17, 5],
    54: [18, 5],
    55: [1, 6],
    56: [2, 6],
    57: [3, 9],
    58: [4, 9],
    59: [5, 9],
    60: [6, 9],
    61: [7, 9],
    62: [8, 9],
    63: [9, 9],
    64: [10, 9],
    65: [11, 9],
    66: [12, 9],
    67: [13, 9],
    68: [14, 9],
    69: [15, 9],
    70: [16, 9],
    71: [17, 9],
    72: [4, 6],
    73: [5, 6],
    74: [6, 6],
    75: [7, 6],
    76: [8, 6],
    77: [9, 6],
    78: [10, 6],
    79: [11, 6],
    80: [12, 6],
    81: [13, 6],
    82: [14, 6],
    83: [15, 6],
    84: [16, 6],
    85: [17, 6],
    86: [18, 6],
    87: [1, 7],
    88: [2, 7],
    89: [3, 10],
    90: [4, 10],
    91: [5, 10],
    92: [6, 10],
    93: [7, 10],
    94: [8, 10],
    95: [9, 10],
    96: [10, 10],
    97: [11, 10],
    98: [12, 10],
    99: [13, 10],
    100: [14, 10],
    101: [15, 10],
    102: [16, 10],
    103: [17, 10],
    104: [4, 7],
    105: [5, 7],
    106: [6, 7],
    107: [7, 7],
    108: [8, 7],
    109: [9, 7],
    110: [10, 7],
    111: [11, 7],
    112: [12, 7],
    113: [13, 7],
    114: [14, 7],
    115: [15, 7],
    116: [16, 7],
    117: [17, 7],
    118: [18, 7],
}


output_css = ""
output_html = ""
for el in periodictable.elements:
    if el.number == 0:
        continue
    output_css += """
#element-{} {{
grid-column-start: {};
grid-row-start: {};
}}""".format(
        el.number, *pos[el.number]
    )
    output_html += """<div class="element button" id="element-{}" onclick="toggle_element({})">{}<span class="badge" title="Badge top right" id="badge_{}"></span></div>
""".format(
        el.number, el.number, el.symbol, el.number
    )


print(output_css)
print(output_html)
