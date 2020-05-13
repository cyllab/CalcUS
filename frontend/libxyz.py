import numpy as np

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





