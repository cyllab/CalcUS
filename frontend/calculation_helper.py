from .constants import *
import string

def get_abs_method(method):
    for m in SYN_METHODS.keys():
        if method.lower() in SYN_METHODS[m] or method.lower() == m:
            return m
    return -1

def get_abs_basis_set(basis_set):
    for bs in SYN_BASIS_SETS.keys():
        if basis_set.lower() in SYN_BASIS_SETS[bs] or basis_set.lower() == bs:
            return bs
    return -1

def get_method(method, software):
    abs_method = get_abs_method(method)
    if abs_method == -1:
        print("Method not found: {}".format(method))
        return method
    return SOFTWARE_METHODS[software][abs_method]

def get_basis_set(basis_set, software):
    abs_basis_set = get_abs_basis_set(basis_set)
    if abs_basis_set == -1:
        print("Basis set not found: {}".format(basis_set))
        return basis_set
    return SOFTWARE_BASIS_SETS[software][abs_basis_set]

def clean_xyz(xyz):
    return ''.join([x if x in string.printable else ' ' for x in xyz])

