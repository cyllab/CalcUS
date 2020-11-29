from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import views

app_name = 'frontend'
urlpatterns = [
    #Home and index
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),

    path('list/', views.IndexView.as_view(), name='list'),
    path('documentation/', TemplateView.as_view(template_name="frontend/documentation.html"), name='documentation'),
    path('calculations/', views.calculations, name='calculations'),

    path('answer/', views.answer, name='answer'),
    path('cancel_calc/', views.cancel_calc, name='cancel_calc'),
    path('relaunch_calc/', views.relaunch_calc, name='relaunch_calc'),
    path('refetch_calc/', views.refetch_calc, name='refetch_calc'),
    path('toggle_private/', views.toggle_private, name='toggle_private'),
    path('toggle_flag/', views.toggle_flag, name='toggle_flag'),

    path('projects/', views.projects, name='projects'),
    path('projects/<str:username>', views.projects_username, name='projects_username'),
    path('get_projects/', views.get_projects, name='get_projects'),
    path('projects/<str:username>/<str:proj>', views.project_details, name='project_details'),
    path('project_list/', views.project_list, name='project_list'),

    path('periodictable/', views.periodictable, name='periodictable'),
    path('specifications/', views.specifications, name='specifications'),
    path('get_available_bs/', views.get_available_bs, name='get_available_bs'),
    path('get_available_elements/', views.get_available_elements, name='get_available_elements'),

    path('aux_molecule/', views.aux_molecule, name='aux_molecule'),
    path('aux_ensemble/', views.aux_ensemble, name='aux_ensemble'),
    path('aux_structure/', views.aux_structure, name='aux_structure'),

    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),

    path('rename_project/', views.rename_project, name='rename_project'),
    path('rename_molecule/', views.rename_molecule, name='rename_molecule'),
    path('rename_ensemble/', views.rename_ensemble, name='rename_ensemble'),

    path('create_project/', views.create_project, name='create_project'),

    path('download_project/', views.download_project_post, name='download_project_post'),
    path('download_project/<int:pk>', views.download_project, name='download_project'),

    path('nmr_analysis/<int:pk>/<int:pid>', views.nmr_analysis, name='nmr_analysis'),
    path('get_shifts/', views.get_shifts, name='get_shifts'),
    path('get_exp_spectrum/', views.get_exp_spectrum, name='get_exp_spectrum'),

    path('analyse/<int:project_id>', views.analyse, name='analyse'),
    path('ensemble_map/<int:pk>', views.ensemble_map, name='ensemble_map'),
    path('ensemble_table_body/<int:pk>', views.ensemble_table_body, name='ensemble_table_body'),

    path('see/<int:pk>', views.see, name='see'),
    path('update_preferences/', views.update_preferences, name='update_preferences'),

    path('set_project_default/', views.set_project_default, name='set_project_default'),
    path('save_preset/', views.save_preset, name='save_preset'),

    #Documentation
    path('learn/', views.learn, name='learn'),
    path('learn/exercise/<int:pk>', views.exercise, name='exercise'),
    path('learn/example/<int:pk>', views.example, name='example'),
    path('learn/recipe/<int:pk>', views.recipe, name='recipe'),

    path('calculationorder/<int:pk>', views.calculationorder, name='calculationorder'),
    path('calculation/<int:pk>', views.calculation, name='calculation'),
    path('link_order/<int:pk>', views.link_order, name='link_order'),

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
    path('connect_access/', views.connect_access, name='connect_access'),
    path('disconnect_access/', views.disconnect_access, name='disconnect_access'),
    path('get_command_status/', views.get_command_status, name='get_command_status'),
    path('delete_access/<int:pk>', views.delete_access, name='delete_access'),
    path('status_access/', views.status_access, name='status_access'),

    #Calculations
    path('molecule/<int:pk>', views.molecule, name='molecule'),
    path('ensemble/<int:pk>', views.ensemble, name='ensemble'),
    path('details_ensemble/', views.details_ensemble, name='details_ensemble'),
    path('details_structure/', views.details_structure, name='details_structure'),

    path('get_related_calculations/<int:pk>', views.get_related_calculations, name='get_related_calculations'),

    path('launch/', views.launch, name='launch'),
    path('launch/calc/<int:cid>/<int:fid>', views.launch_frame, name='launch_frame'),
    path('launch/<int:pk>', views.launch_pk, name='launch_pk'),
    path('launch/<int:ee>/<int:pk>', views.launch_structure_pk, name='launch_structure_pk'),
    path('launch/project/<int:pk>', views.launch_project, name='launch_project'),
    path('load_params_ensemble/<int:pk>', views.load_params_ensemble, name='load_params_ensemble'),
    path('load_params_structure/<int:pk>', views.load_params_structure, name='load_params_structure'),
    path('load_preset/<int:pk>', views.load_preset, name='load_preset'),
    path('delete_preset/<int:pk>', views.delete_preset, name='delete_preset'),
    path('presets/', views.launch_presets, name='presets'),

    path('get_cube/', views.get_cube, name='get_cube'),
    path('get_calc_data/<int:pk>', views.get_calc_data, name='get_calc_data'),
    path('get_calc_data_remote/<int:pk>', views.get_calc_data_remote, name='get_calc_data_remote'),
    path('get_calc_frame/<int:cid>/<int:fid>', views.get_calc_frame, name='get_calc_frame'),

    path('next_step/<int:pk>', views.next_step, name='next_step'),
    path('info_table/<int:pk>', views.info_table, name='info_table'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),
    path('conformer_table/', views.conformer_table_post, name='conformer_table_post'),
    path('vib_table/<int:pk>', views.vib_table, name='vib_table'),
    path('ir_spectrum/<int:pk>', views.ir_spectrum, name='ir_spectrum'),

    path('log/<int:pk>', views.log, name='log'),
    path('download_log/<int:pk>', views.download_log, name='download_log'),
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

    path('delete_project/', views.delete_project, name='delete_project'),
    path('delete_molecule/', views.delete_molecule, name='delete_molecule'),
    path('delete_ensemble/', views.delete_ensemble, name='delete_ensemble'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


