"""
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

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
"""


from django import template
from django.conf import settings

from frontend.constants import cloud_config

register = template.Library()


@register.simple_tag
def get_calcus_version():
    version = settings.CALCUS_VERSION_HASH
    if version == "":
        return "unknown"
    else:
        return version


@register.simple_tag
def get_extra_head_code():
    if "extra_head_code" in cloud_config:
        return cloud_config["extra_head_code"]
    else:
        return ""


@register.simple_tag
def get_extra_body_code():
    if "extra_body_code" in cloud_config:
        return cloud_config["extra_body_code"]
    else:
        return ""
