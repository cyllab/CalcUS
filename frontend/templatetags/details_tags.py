from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_structure_energy(struct, param):
    try:
        prop = struct.properties.get(parameters=param)
    except Property.DoesNotExist:
        return ''
    return prop.energy

@register.simple_tag
def get_structure_relative_energy(struct, param, ensemble):
    return ensemble.relative_energy(struct, param)

@register.simple_tag
def get_structure_weight(struct, param, ensemble):
    return ensemble.weight(struct, param)

@register.simple_tag
def get_geom_flag(ensemble, param):
    s = ensemble.structure_set.all()[0]
    try:
        p = s.properties.get(parameters=param)
    except Property.DoesNotExist:
        return ''

    if p.geom:
        return ' (GEOMETRY)'
    else:
        return ''

@register.simple_tag
def get_ensemble_weighted_energy(param, ensemble):
    ret = ensemble.weighted_energy(param)
    return ret

@register.simple_tag
def get_ensemble_weighted_free_energy(param, ensemble):
    ret = ensemble.weighted_free_energy(param)
    return ret

@register.simple_tag
def get_simple_nmr_shifts_ensemble(param, ensemble):
    structures = ensemble.structure_set.all()
    shifts = []
    for s in structures:
        try:
            p = s.properties.get(parameters=param)
        except Property.DoesNotExist:
            return ''

        if p.simple_nmr == '':
            return ''


        for ind, shift in enumerate(p.simple_nmr.split('\n')):
            if shift.strip() == '':
                continue
            if ind >= len(shifts):
                shifts.append(['', '', 0.])

            ss = shift.strip().split()
            w = ensemble.weight(s, param)
            if w == '':
                return ''
            shifts[ind][2] += w*float(ss[2])
            if shifts[ind][0] == '':
                shifts[ind][0] = ss[0]
            else:
                assert shifts[ind][0] == ss[0]

            if shifts[ind][1] == '':
                shifts[ind][1] = ss[1]
            else:
                assert shifts[ind][1] == ss[1]

    return shifts

@register.simple_tag
def get_simple_nmr_shifts_structure(prop):

    nmr = prop.simple_nmr
    if nmr == '':
        return ''
    ret = []
    for shift in nmr.split('\n'):
        ret.append(shift.split())
    return ret

