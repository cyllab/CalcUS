from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_molecule_summary(molecules):
    num = {}
    completed = {}
    queued = {}
    running = {}
    if len(molecules) == 0:
        return None

    for mol in molecules:
        num[mol.id] = 0
        completed[mol.id] = 0
        queued[mol.id] = 0
        running[mol.id] = 0

    for o in molecules[0].project.calculationorder_set.all():
        if o.ensemble != None:
            #if o.ensemble.parent_molecule == mol:
            mol = o.ensemble.parent_molecule
            num[mol.id] += o.calculation_set.count()
            for c in o.calculation_set.all():
                s = c.status
                if s == 0:
                    queued[mol.id] += 1
                elif s == 1:
                    running[mol.id] += 1
                else:
                    completed[mol.id] += 1
        elif o.structure != None:
            mol = o.structure.parent_ensemble.parent_molecule
            num[mol.id] += o.calculation_set.count()
            for c in o.calculation_set.all():
                s = c.status
                if s == 0:
                    queued[mol.id] += 1
                elif s == 1:
                    running[mol.id] += 1
                else:
                    completed[mol.id] += 1

    pack = []
    for mol in molecules:
        pack.append([mol, [num[mol.id], queued[mol.id], running[mol.id], completed[mol.id]]])

    return pack
    #return [num, queued, running, completed]

