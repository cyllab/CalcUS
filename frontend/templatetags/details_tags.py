from django import template

register = template.Library()

@register.simple_tag
def get_structure_energy(struct, param):
    return struct.properties.get(parameters=param).energy

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


