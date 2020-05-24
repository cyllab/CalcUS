from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def completed(ex, profile):
    try:
        c = ex.completedexercise_set.get(completed_by=profile)
    except CompletedExercise.DoesNotExist:
        return False
    else:
        return True

