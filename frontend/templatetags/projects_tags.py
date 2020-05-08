from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_project_summary(proj):
    num = 0
    completed = 0
    queued = 0
    running = 0
    for o in proj.calculationorder_set.all():
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

