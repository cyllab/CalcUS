'''
This file of part of CalcUS.

Copyright (C) 2020-2021 Raphaël Robidas

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
'''


from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_geom_flag(ensemble, param):
    if verify_geom(ensemble, param):
        return ' (GEOMETRY)'
    else:
        return ''

def verify_geom(ensemble, param):
    s = ensemble.structure_set.all()[0]
    try:
        p = s.properties.get(parameters=param)
    except Property.DoesNotExist:
        return False

    if p.geom:
        return True
    return False

@register.simple_tag
def get_sorted_params(ensemble):
    # Could be optimized to stop when the parameters linking to the geometry are found
    params = sorted(ensemble.unique_parameters, key=lambda i: verify_geom(ensemble, i), reverse=True)
    return params

@register.simple_tag
def get_ensemble_weighted_energy(param, ensemble):
    ret = ensemble.weighted_energy(param)
    return ret

@register.simple_tag
def get_ensemble_weighted_free_energy(param, ensemble):
    ret = ensemble.weighted_free_energy(param)
    return ret

@register.simple_tag
def get_simple_nmr_shifts_structure(prop):
    nmr = prop.simple_nmr
    if nmr == '':
        return ''
    ret = []
    for shift in nmr.split('\n'):
        ret.append(shift.split())
    return ret
