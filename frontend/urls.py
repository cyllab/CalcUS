from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'frontend'
urlpatterns = [
    #Home and index
    path('', views.projects, name='projects'),
    path('home/', views.projects, name='projects'),
    path('list/', views.IndexView.as_view(), name='list'),

    path('projects/', views.projects, name='projects'),
    path('projects/<str:username>', views.projects_username, name='projects_username'),
    path('get_projects/', views.get_projects, name='get_projects'),
    path('projects/<str:username>/<str:proj>', views.project_details, name='project_details'),

    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),

    #Documentation
    path('examples/', views.ExamplesView.as_view(), name='examples'),
    path('examples/<int:pk>', views.example, name='example'),

    #Group management
    path('apply_pi/', views.apply_pi, name='apply_pi'),
    path('get_pi_requests/', views.get_pi_requests, name='get_pi_requests'),
    path('get_pi_requests_table/', views.get_pi_requests_table, name='get_pi_requests_table'),
    path('profile_groups/', views.profile_groups, name='profile_groups'),
    path('manage_pi_requests/', views.manage_pi_requests, name='manage_pi_requests'),
    path('deny_pi_request/<int:pk>', views.deny_pi_request, name='deny_pi_request'),
    path('accept_pi_request/<int:pk>', views.accept_pi_request, name='accept_pi_request'),
    path('add_user/', views.add_user, name='add_user'),
    path('gen_3D/', views.gen_3D, name='gen_3D'),
    path('remove_user/', views.remove_user, name='remove_user'),

    #Access management
    path('manage_access/<int:pk>', views.manage_access, name='manage_access'),
    path('add_clusteraccess/', views.add_clusteraccess, name='add_clusteraccess'),
    path('owned_accesses/', views.owned_accesses, name='owned_accesses'),
    path('test_access/', views.test_access, name='test_access'),
    path('get_command_status/', views.get_command_status, name='get_command_status'),
    path('delete_access/<int:pk>', views.delete_access, name='delete_access'),

    #Calculations
    path('launch/', views.launch, name='launch'),
    path('launch/<int:pk>', views.launch_pk, name='launch_pk'),
    path('software/<str:software>', views.launch_software, name='launch_software'),

    path('get_cube/', views.get_cube, name='get_cube'),
    path('details/<int:pk>', views.details, name='details'),
    path('next_step/<int:pk>', views.next_step, name='next_step'),
    path('info_table/<int:pk>', views.info_table, name='info_table'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),
    path('vib_table/<int:pk>', views.vib_table, name='vib_table'),
    path('ir_spectrum/<int:pk>', views.ir_spectrum, name='ir_spectrum'),

    path('log/<int:pk>', views.log, name='log'),
    path('submit_calculation/', views.submit_calculation, name='submit_calculation'),
    path('get_structure/', views.get_structure, name='get_structure'),
    path('get_details_sections/<int:pk>', views.get_details_sections, name='get_details_sections'),
    path('get_vib_animation/', views.get_vib_animation, name='get_vib_animation'),
    path('get_scan_animation/', views.get_scan_animation, name='get_scan_animation'),
    path('download_structure/<int:pk>', views.download_structure, name='download_structure'),
    path('status/<int:pk>', views.status, name='status'),
    path('icon/<int:pk>', views.icon, name='icon'),
    path('uvvis/<int:pk>', views.uvvis, name='uvvis'),
    path('nmr/<int:pk>', views.nmr, name='nmr'),
    path('delete/<int:pk>', views.delete, name='delete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


