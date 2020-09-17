from django import template
from frontend.models import *

register = template.Library()

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

