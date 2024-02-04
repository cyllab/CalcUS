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

from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.sitemaps.views import sitemap

from .sitemaps import CalcUSSitemap
from .views import privacy

sitemaps = {
    "static": CalcUSSitemap,
}

urlpatterns = [
    path("", include("frontend.urls", namespace="frontend")),
    path("privacy/", privacy),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]

handler404 = "frontend.views.handler404"
handler500 = "frontend.views.handler500"

from django.conf import settings
from django.urls import include, path

if settings.DEBUG and False:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
