from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_molecule_summary(mol):
    num = 0
    completed = 0
    queued = 0
    running = 0
    for o in mol.project.calculationorder_set.all():
        if o.ensemble != None:
            if o.ensemble.parent_molecule == mol:
                num += o.calculation_set.count()
                for c in o.calculation_set.all():
                    s = c.status
                    if s == 0:
                        queued += 1
                    elif s == 1:
                        running += 1
                    else:
                        completed += 1
        else:
            if o.structure.parent_ensemble.parent_molecule == mol:
                num += o.calculation_set.count()
                for c in o.calculation_set.all():
                    s = c.status
                    if s == 0:
                        queued += 1
                    elif s == 1:
                        running += 1
                    else:
                        completed += 1

    return [num, queued, running, completed]

