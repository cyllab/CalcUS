from django import template
from frontend.models import *

register = template.Library()

@register.simple_tag
def get_parent_url(url):
    s = url.split('/')
    if s[-1].strip() == '':
        s.pop(-1)
    return '/'.join(s[:-1]) + '/'

