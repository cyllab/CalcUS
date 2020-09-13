from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('frontend.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

handler404 = 'frontend.views.handler404'
handler400 = 'frontend.views.handler400'
handler403 = 'frontend.views.handler403'
handler500 = 'frontend.views.handler500'

from django.conf import settings
from django.urls import include, path

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
