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


import decimal
import periodictable
from enum import IntEnum

KEY_SIZE = 32
MAX_FOLDER_DEPTH = 5

ATOMIC_NUMBER = {}
ATOMIC_SYMBOL = {}
LOWERCASE_ATOMIC_SYMBOLS = {}

for el in periodictable.elements:
    ATOMIC_NUMBER[el.symbol] = el.number
    ATOMIC_SYMBOL[el.number] = el.symbol
    LOWERCASE_ATOMIC_SYMBOLS[el.symbol.lower()] = el.symbol


decimal.getcontext().prec = 50

HARTREE_VAL = decimal.Decimal(2625.499638)
HARTREE_FVAL = 2625.499638
HARTREE_TO_KCAL_F = 627.509

E_VAL = decimal.Decimal(2.7182818284590452353602874713527)
R_CONSTANT = decimal.Decimal(8.31446261815324)
R_CONSTANT_HARTREE = decimal.Decimal(3.166811565240536e-06)
TEMP = decimal.Decimal(298)

MAX_SFTP_ATTEMPT_COUNT = 3
MAX_COMMAND_ATTEMPT_COUNT = 5
MAX_RESUME_CALC_ATTEMPT_COUNT = 3


class ErrorCodes(IntEnum):
    SUCCESS = 0
    UNKNOWN_TERMINATION = 1
    JOB_CANCELLED = 2
    FAILED_TO_CONVERGE = 3
    INVALID_CHARGE_MULTIPLICITY = 4
    INVALID_FILE = 5
    FAILED_TO_CREATE_INPUT = 6
    SERVER_DISCONNECTED = 7  # Not a fatal error (will not end the calculation)
    MISSING_FILE = 8
    CHANNEL_TIMED_OUT = 10
    INVALID_COMMAND = 11
    COULD_NOT_GET_REMOTE_FILE = 12
    NO_JOB_LOG = 13
    COMMAND_TIMED_OUT = 14
    FAILED_SUBMISSION = 15
    UNIMPLEMENTED = 16
    UNKNOWN_CALCULATION = 17
    FAILED_TO_UPLOAD_FILE = 18
    FAILED_TO_DOWNLOAD_FILE = 19
    FAILED_TO_EXECUTE_COMMAND = 20
    CONNECTION_ERROR = 21

    FAILED_TO_RUN_LOCAL_SOFTWARE = 30


# Software->Method/Functional->Basis set->Atom->[m, b, R2]
NMR_REGRESSIONS = {
    "ORCA": {
        "PBEh-3c": {
            "": {
                "H": [-1.0758, 32.4963, 0.9957],
                "C": [-1.0126, 198.0555, 0.9970],
            },
        },
    },
    "Gaussian": {},
}

# Structure:
#   {
#       step_name: {
#           spec_name: [num_params, [software1, software2]]
#       }
#   }
