import numpy as np
import periodictable
from .constants import *

#Structure of xyz:
#[<EL>, [x, y, z]]
#Atom indices are given starting at 1
#Angles in degrees

def get_distance(xyz, a, b):
    return np.linalg.norm(xyz[a-1][1] - xyz[b-1][1])

def get_angle(xyz, a, b, c):
    v1 = xyz[a-1][1] - xyz[b-1][1]
    v2 = xyz[c-1][1] - xyz[b-1][1]

    return np.arccos(v1.dot(v2)/(np.linalg.norm(v1)*np.linalg.norm(v2)))*180/np.pi

def get_dihedral(xyz, a, b, c, d):
    v1 = xyz[b-1][1] - xyz[a-1][1]
    v2 = xyz[c-1][1] - xyz[b-1][1]
    v3 = xyz[d-1][1] - xyz[c-1][1]

    n1 = np.cross(v1, v2)
    n1 = n1/np.linalg.norm(n1)

    n2 = np.cross(v2, v3)
    n2 = n2/np.linalg.norm(n2)

    m1 = np.cross(n1, v2/np.linalg.norm(v2))
    x = n1.dot(n2)
    y = m1.dot(n2)

    return np.arctan2(y, x)*180/np.pi

def parse_xyz_from_text(raw_xyz):
    xyz = []

    for line in raw_xyz.split('\n')[2:]:
        if line.strip() == '':
            continue
        a, x, y, z = line.split()
        xyz.append([a, np.array([float(x), float(y), float(z)])])

    return xyz

def parse_xyz_from_file(f):
    """ Parses a standard .xyz file into a suitable structure for calculations """
    with open(f) as ff:
        lines = ff.readlines()[2:]
    xyz = []

    for line in lines:
        a, x, y, z = line.split()
        xyz.append([a, np.array([float(x), float(y), float(z)])])

    return xyz

def get_connectivity(xyz):
    """ Returns a list of pairs of bonded atoms """
    TOLERANCE = 1.1
    bonds = []
    def bond_unique(ind1, ind2):
        for bond in bonds:
            if bond[0] == ind1 and bond[1] == ind2:
                return False
            if bond[0] == ind2 and bond[1] == ind1:
                return False
        return True

    for ind1, i in enumerate(xyz):
        for ind2, j in enumerate(xyz):
            if ind1 > ind2:
                d = get_distance(xyz, ind1+1, ind2+1)
                cov = (periodictable.elements[ATOMIC_NUMBER[i[0]]].covalent_radius + periodictable.elements[ATOMIC_NUMBER[j[0]]].covalent_radius)

                if d < cov*TOLERANCE and bond_unique(ind1, ind2):
                    bonds.append([ind1, ind2])
    return bonds

def get_neighbors_lists(xyz):
    """ Returns a list neighbors (bonded atoms) for each atom """
    bonds = get_connectivity(xyz)
    neighbors = [[] for i in range(len(xyz))]

    for bond in bonds:
        a, b = bond
        neighbors[a].append(b)
        neighbors[b].append(a)

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

def equivalent_atoms(xyz, algorithm="morgan"):
    equivalent = []
    if algorithm == "morgan":
        indices = morgan_numbering(xyz)
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

def reorder_xyz(ref, xyz):
    """ Reorders the atoms in xyz to correspond to the order in ref """

    new_order = {i: -1 for i in range(len(xyz))}

    elements = {i: e[0] for i, e in enumerate(ref)}


