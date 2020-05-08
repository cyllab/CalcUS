from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import views

app_name = 'frontend'
urlpatterns = [
    #Home and index
    path('', views.projects, name='projects'),
    path('home/', views.projects, name='projects'),
    path('list/', views.IndexView.as_view(), name='list'),
    path('documentation/', TemplateView.as_view(template_name="frontend/documentation.html"), name='documentation'),
    path('calculations/', views.calculations, name='calculations'),

    path('projects/', views.projects, name='projects'),
    path('projects/<str:username>', views.projects_username, name='projects_username'),
    path('get_projects/', views.get_projects, name='get_projects'),
    path('projects/<str:username>/<str:proj>', views.project_details, name='project_details'),
    path('project_list/', views.project_list, name='project_list'),

    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),

    path('rename_project/', views.rename_project, name='rename_project'),
    path('rename_molecule/', views.rename_molecule, name='rename_molecule'),
    path('rename_ensemble/', views.rename_ensemble, name='rename_ensemble'),

    path('create_project/', views.create_project, name='create_project'),

    path('download_project_csv/<int:project_id>', views.download_project_csv, name='download_project_csv'),

    #Documentation
    path('examples/', views.ExamplesView.as_view(), name='examples'),
    path('examples/<int:pk>', views.example, name='example'),

    path('calculationorder/<int:pk>', views.calculationorder, name='calculationorder'),

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
    path('server_summary/', views.server_summary, name='server_summary'),

    #Access management
    path('manage_access/<int:pk>', views.manage_access, name='manage_access'),
    path('add_clusteraccess/', views.add_clusteraccess, name='add_clusteraccess'),
    path('owned_accesses/', views.owned_accesses, name='owned_accesses'),
    path('test_access/', views.test_access, name='test_access'),
    path('get_command_status/', views.get_command_status, name='get_command_status'),
    path('delete_access/<int:pk>', views.delete_access, name='delete_access'),
    path('status_access/', views.status_access, name='status_access'),

    #Calculations
    path('molecule/<int:pk>', views.molecule, name='molecule'),
    path('ensemble/<int:pk>', views.ensemble, name='ensemble'),
    path('details_ensemble/', views.details_ensemble, name='details_ensemble'),
    path('details_structure/', views.details_structure, name='details_structure'),

    path('launch/', views.launch, name='launch'),
    path('launch/<int:pk>', views.launch_pk, name='launch_pk'),
    path('launch/<int:ee>/<int:pk>', views.launch_structure_pk, name='launch_structure_pk'),
    path('software/<str:software>', views.launch_software, name='launch_software'),
    path('get_theory_details/', views.get_theory_details, name='get_theory_details'),

    path('get_cube/', views.get_cube, name='get_cube'),
    path('details/<int:pk>', views.details, name='details'),
    path('next_step/<int:pk>', views.next_step, name='next_step'),
    path('info_table/<int:pk>', views.info_table, name='info_table'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),
    path('conformer_table/', views.conformer_table_post, name='conformer_table_post'),
    path('vib_table/<int:pk>', views.vib_table, name='vib_table'),
    path('ir_spectrum/<int:pk>', views.ir_spectrum, name='ir_spectrum'),

    path('log/<int:pk>', views.log, name='log'),
    path('submit_calculation/', views.submit_calculation, name='submit_calculation'),
    path('get_structure/', views.get_structure, name='get_structure'),
    path('get_details_sections/<int:pk>', views.get_details_sections, name='get_details_sections'),
    path('get_vib_animation/', views.get_vib_animation, name='get_vib_animation'),
    path('get_scan_animation/', views.get_scan_animation, name='get_scan_animation'),
    path('download_structures/<int:ee>', views.download_structures, name='download_structures'),
    path('download_structures/<int:ee>/<int:num>', views.download_structure, name='download_structure'),
    path('status/<int:pk>', views.status, name='status'),
    path('icon/<int:pk>', views.icon, name='icon'),
    path('uvvis/<int:pk>', views.uvvis, name='uvvis'),
    path('nmr/', views.nmr, name='nmr'),
    #path('delete/<int:pk>', views.delete, name='delete'),

    path('delete_project/', views.delete_project, name='delete_project'),
    path('delete_molecule/', views.delete_molecule, name='delete_molecule'),
    path('delete_ensemble/', views.delete_ensemble, name='delete_ensemble'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


