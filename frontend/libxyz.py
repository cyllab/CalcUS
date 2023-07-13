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


import json
import numpy as np
import periodictable
import copy
from .constants import *

from hashlib import md5

# Structure of xyz:
# [<EL>, [x, y, z]]
# Atom indices are given starting at 1
# Angles in degrees


def get_distance(xyz, a, b):
    return np.linalg.norm(xyz[a - 1][1] - xyz[b - 1][1])


def get_angle(xyz, a, b, c):
    v1 = xyz[a - 1][1] - xyz[b - 1][1]
    v2 = xyz[c - 1][1] - xyz[b - 1][1]

    return (
        np.arccos(v1.dot(v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))) * 180 / np.pi
    )


def get_dihedral(xyz, a, b, c, d):
    v1 = xyz[b - 1][1] - xyz[a - 1][1]
    v2 = xyz[c - 1][1] - xyz[b - 1][1]
    v3 = xyz[d - 1][1] - xyz[c - 1][1]

    n1 = np.cross(v1, v2)
    n1 = n1 / np.linalg.norm(n1)

    n2 = np.cross(v2, v3)
    n2 = n2 / np.linalg.norm(n2)

    m1 = np.cross(n1, v2 / np.linalg.norm(v2))
    x = n1.dot(n2)
    y = m1.dot(n2)

    return np.arctan2(y, x) * 180 / np.pi


def parse_xyz_from_text(raw_xyz):
    xyz = []

    for line in raw_xyz.split("\n")[2:]:
        if line.strip() == "":
            continue
        a, x, y, z = line.split()
        xyz.append([a, np.array([float(x), float(y), float(z)])])

    return xyz


def parse_xyz_from_file(f):
    """Parses a standard .xyz file into a suitable structure for calculations"""
    with open(f) as ff:
        lines = ff.readlines()[2:]
    xyz = []

    for line in lines:
        a, x, y, z = line.split()
        xyz.append([a, np.array([float(x), float(y), float(z)])])

    return xyz


def parse_multixyz_from_file(f, ind=0):
    """Parses a multixyz file into a suitable structure for calculations"""
    with open(f) as ff:
        lines = ff.readlines()
    multixyz = []
    energies = []

    natoms = int(lines[0])

    assert len(lines) % (natoms + 2) == 0

    nstructs = int(len(lines) / (natoms + 2))
    for i in range(nstructs):
        xyz = []
        for line in lines[i * (natoms + 2) + 2 : (i + 1) * (natoms + 2)]:
            a, x, y, z = line.split()
            xyz.append([a, np.array([float(x), float(y), float(z)])])

        E_split = lines[i * (natoms + 2) + 1].strip().split()
        if len(E_split) == 0:
            # print("No energy in file {}".format(f))
            E = 0
        else:
            try:
                E_txt = E_split[ind]
                E = float(E_txt)
            except (IndexError, ValueError):
                E = 0
        multixyz.append(xyz)
        energies.append(E)

    return multixyz, energies


def get_connectivity(xyz, tolerance=1.15, He_radius=0.28):
    """Returns a list of pairs of bonded atoms (one-indexed)"""
    bonds = []

    def bond_unique(ind1, ind2):
        for bond in bonds:
            if bond[0] == ind1 + 1 and bond[1] == ind2 + 1:
                return False
            if bond[0] == ind2 + 1 and bond[1] == ind1 + 1:
                return False
        return True

    for ind1, i in enumerate(xyz):
        for ind2, j in enumerate(xyz):
            if ind1 > ind2:
                d = get_distance(xyz, ind1 + 1, ind2 + 1)
                cov = get_cov_radius(i[0], He_radius) + get_cov_radius(j[0], He_radius)

                if d < cov * tolerance and bond_unique(ind1, ind2):
                    bonds.append([ind2 + 1, ind1 + 1])
    return bonds


def get_cov_bond_length(xyz, a, b):
    ela = xyz[a - 1][0]
    elb = xyz[b - 1][0]

    cova = getattr(periodictable.elements, ela).covalent_radius
    covb = getattr(periodictable.elements, elb).covalent_radius
    return 1.1 * (cova + covb)


def get_cov_radius(element, He_radius=0.28):
    if element == "He":
        return He_radius
    else:
        return periodictable.elements[ATOMIC_NUMBER[element]].covalent_radius


def get_neighbors_lists(xyz, tolerance=1.1, He_radius=0.28):
    """Returns a list neighbors (bonded atoms) for each atom, zero-indexed"""
    bonds = get_connectivity(xyz, tolerance=tolerance, He_radius=He_radius)
    neighbors = [[] for i in range(len(xyz))]

    for bond in bonds:
        a, b = bond
        neighbors[a - 1].append(b - 1)
        neighbors[b - 1].append(a - 1)

    return neighbors


def morgan_numbering(xyz):
    indices = np.zeros(len(xyz)) + 1
    neighbors = get_neighbors_lists(xyz)
    num = len(xyz)

    num_unique_indices = 1
    while True:
        new_indices = indices.copy()
        for i in range(num):
            bonded = neighbors[i]
            for b in bonded:
                new_indices[i] += indices[b]

        new_num_unique_indices = len(set(new_indices))
        if new_num_unique_indices == num_unique_indices:
            break

        indices = new_indices
        num_unique_indices = new_num_unique_indices

    return indices


def morgan_hashz_numbering(xyz):
    neighbors = get_neighbors_lists(xyz)

    indices = np.array([str(ATOMIC_NUMBER[i[0]]) for i in xyz], dtype=np.dtype("<U32"))
    num = len(xyz)
    num_unique_indices = 1

    while True:
        new_indices = indices.copy()
        for i in range(num):
            bonded = neighbors[i]
            txt = [new_indices[i]]
            for b in bonded:
                txt.append(indices[b])
            new_indices[i] = md5("".join(sorted(txt)).encode()).hexdigest()

        new_num_unique_indices = len(set(new_indices))
        if new_num_unique_indices == num_unique_indices:
            break

        indices = new_indices
        num_unique_indices = new_num_unique_indices

    return indices


def equivalent_atoms(xyz, algorithm="morgan"):
    equivalent = []
    if algorithm == "morgan":
        indices = morgan_hashz_numbering(xyz)
        for val in set(indices):
            eqs = np.where(indices == val)[0]
            if len(eqs) > 1:
                equivalent.append(eqs)
    return equivalent


def get_networkx_graph_from_xyz(xyz):
    import networkx as nx

    bonds = get_connectivity(xyz)

    G = nx.Graph()
    elements = {}
    for ind, (el, pos) in enumerate(xyz):
        G.add_node(ind, element=el, position=pos)

    for b in bonds:
        G.add_edge(*b)

    return G


def npxyz2strxyz(xyz):
    return json.dumps([[a, list(l)] for a, l in xyz])


def strxyz2npxyz(xyz):
    return [[a, np.array(l)] for a, l in json.loads(xyz)]


def reorder_xyz(ref, xyz):
    """Reorders the atoms in xyz to correspond to the order in ref"""

    new_order = {i: -1 for i in range(len(xyz))}

    elements = {i: e[0] for i, e in enumerate(ref)}


def format_xyz(xyz):
    str_xyz = f"{len(xyz)}\n\n"
    for line in xyz:
        str_xyz += "{} {:.4f} {:.4f} {:.4f}\n".format(line[0], *line[1])
    return str_xyz


def rotation_matrix_from_vectors(vec1, vec2):
    """Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (
        vec2 / np.linalg.norm(vec2)
    ).reshape(3)
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s**2))
    return rotation_matrix


# https://stackoverflow.com/questions/6802577/rotation-of-3d-vector
def rotation_matrix_around_axis(axis, theta):
    return expm(cross(eye(3), axis / norm(axis) * theta))


def rotate_around_axis(xyz, full_xyz, axis, theta):
    pos_i = copy.deepcopy(xyz[13])
    M = rotation_matrix_around_axis(axis, theta)

    xyz = M.dot(xyz.T)

    delta = pos_i - xyz.T[13]
    final = []
    for l, ll in zip(full_xyz, xyz.T):
        final.append([l[0], ll + delta])
    return final


def rotate_around_axis_without_centering(xyz, axis, theta):
    M = rotation_matrix_around_axis(axis, theta)
    _xyz = copy.deepcopy([i[1] for i in xyz])
    _xyz = np.array(_xyz)

    _xyz = M.dot(_xyz.T)

    final = []
    for l, ll in zip(xyz, _xyz.T):
        final.append([l[0], ll])
    return final


def align_xyz(xyz, v1, v2):
    origin = xyz[0][1]
    # v1 = xyz[1][1] - xyz[0][1]
    R = rotation_matrix_from_vectors(v1, v2)

    _xyz = []
    for l in xyz:
        _xyz.append(l[1] - origin)
    _xyz = np.array(_xyz)
    _xyz = R.dot(_xyz.T)
    final = []
    for l, ll in zip(xyz, _xyz.T):
        final.append([l[0], ll])
    return final


def shift_xyz(xyz, vec):
    _xyz = []
    for l in xyz:
        _l = l
        _l[1] += vec
        _xyz.append(_l)
    return _xyz


def create_derivative(base_xyz, sub_xyz):
    """
    Takes in 1 XYZ with one or multiple He atoms representing the desired substitution points and
    a list of substituent names and XYZ representing the substituents in labeling order.
    """

    base_conn = get_neighbors_lists(base_xyz, He_radius=1.3)
    sub_pos = [i for i in range(len(base_xyz)) if base_xyz[i][0] == "He"]

    if len(sub_pos) > 1:
        print("Cannot do substitution at multiple sites for now")
        return

    pos = sub_pos[0]

    vecs = []

    # for ind, (pos, _sub_xyz, sub_name) in enumerate(zip(sub_pos, subs, sub_names)):
    if len(base_conn[pos]) != 1:
        print("Improper substitution on the substrate for atom {}".format(pos))
        exit(0)

    xyz = copy.deepcopy(base_xyz)

    neigh = base_conn[pos][0]
    vec = np.array(base_xyz[base_conn[pos][0]][1]) - np.array(base_xyz[pos][1])
    vec = vec / np.linalg.norm(vec)

    anchor = [i for i in range(len(sub_xyz)) if sub_xyz[i][0] == "He"]
    if len(anchor) != 1:
        print("Invalid substituent: {}".format(sub))
        return

    anchor = anchor[0]

    conn = get_neighbors_lists(sub_xyz, He_radius=1.4)
    anchor_neigh = conn[anchor]
    if len(anchor_neigh) != 1:
        print("Could not find proper substitution bond: {}".format(sub))
        return
    sub_neigh = anchor_neigh[0]

    sub_vec = np.array(sub_xyz[anchor_neigh[0]][1]) - np.array(sub_xyz[anchor][1])

    aligned_sub_xyz = align_xyz(sub_xyz, -sub_vec, vec)
    ideal_bond_length = get_cov_radius(sub_xyz[sub_neigh][0]) + get_cov_radius(
        xyz[neigh][0]
    )

    moved_sub_xyz = shift_xyz(
        aligned_sub_xyz,
        xyz[neigh][1] - aligned_sub_xyz[sub_neigh][1] - vec * ideal_bond_length,
    )

    xyz += moved_sub_xyz

    return [i for i in xyz if i[0] != "He"]
