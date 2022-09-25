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


from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from . import views

app_name = "frontend"
urlpatterns = [
    # Home and index
    path("", views.home, name="home"),
    path("home/", views.home, name="home"),
    path("list/", views.IndexView.as_view(), name="list"),
    path("calculations/", views.calculations, name="calculations"),
    path("cloud_order/", views.cloud_order, name="cloud_order"),
    path("cloud_calc/", views.cloud_calc, name="cloud_calc"),
    path("cloud_action/", views.cloud_action, name="cloud_action"),
    path("cancel_calc/", views.cancel_calc, name="cancel_calc"),
    path("relaunch_calc/", views.relaunch_calc, name="relaunch_calc"),
    path("refetch_calc/", views.refetch_calc, name="refetch_calc"),
    path("toggle_private/", views.toggle_private, name="toggle_private"),
    path("toggle_flag/", views.toggle_flag, name="toggle_flag"),
    path("projects/", views.projects, name="projects"),
    path(
        "projects/<str:username>/<str:proj>/<path:folder_path>",
        views.project_folders,
        name="project_folders",
    ),
    path("projects/<str:username>", views.projects_username, name="projects_username"),
    path("get_projects/", views.get_projects, name="get_projects"),
    path(
        "projects/<str:username>/<str:proj>",
        views.project_details,
        name="project_details",
    ),
    path("project_list/", views.project_list, name="project_list"),
    path("periodictable/", views.periodictable, name="periodictable"),
    path("get_available_bs/", views.get_available_bs, name="get_available_bs"),
    path(
        "get_available_elements/",
        views.get_available_elements,
        name="get_available_elements",
    ),
    path("check_functional/", views.check_functional, name="check_functional"),
    path("check_basis_set/", views.check_basis_set, name="check_basis_set"),
    path("check_solvent/", views.check_solvent, name="check_solvent"),
    path("aux_molecule/", views.aux_molecule, name="aux_molecule"),
    path("aux_ensemble/", views.aux_ensemble, name="aux_ensemble"),
    path("aux_structure/", views.aux_structure, name="aux_structure"),
    path("please_register/", views.please_register, name="please_register"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.profile, name="profile"),
    path("accounts/login", views.login, name="login"),
    path("rename_project/", views.rename_project, name="rename_project"),
    path("rename_molecule/", views.rename_molecule, name="rename_molecule"),
    path("rename_ensemble/", views.rename_ensemble, name="rename_ensemble"),
    path("rename_folder/", views.rename_folder, name="rename_folder"),
    path("create_project/", views.create_project, name="create_project"),
    path("create_folder/", views.create_folder, name="create_folder"),
    path("move_element/", views.move_element, name="move_element"),
    path(
        "download_project/", views.download_project_post, name="download_project_post"
    ),
    path("download_project/<int:pk>", views.download_project, name="download_project"),
    path("download_folder/<int:pk>", views.download_folder, name="download_folder"),
    path("nmr_analysis/<int:pk>/<int:pid>", views.nmr_analysis, name="nmr_analysis"),
    path("get_shifts/", views.get_shifts, name="get_shifts"),
    path("get_exp_spectrum/", views.get_exp_spectrum, name="get_exp_spectrum"),
    path("analyse/<int:project_id>", views.analyse, name="analyse"),
    path("ensemble_map/<int:pk>", views.ensemble_map, name="ensemble_map"),
    path(
        "ensemble_table_body/<int:pk>",
        views.ensemble_table_body,
        name="ensemble_table_body",
    ),
    path("see/<int:pk>", views.see, name="see"),
    path("see_all/", views.see_all, name="see_all"),
    path(
        "clean_all_successful/", views.clean_all_successful, name="clean_all_successful"
    ),
    path("clean_all_completed/", views.clean_all_completed, name="clean_all_completed"),
    path("update_preferences/", views.update_preferences, name="update_preferences"),
    path("set_project_default/", views.set_project_default, name="set_project_default"),
    path("save_preset/", views.save_preset, name="save_preset"),
    # Documentation
    path("learn/", views.learn, name="learn"),
    path("learn/example/<int:pk>", views.example, name="example"),
    path("learn/recipe/<int:pk>", views.recipe, name="recipe"),
    path("calculationorder/<int:pk>", views.calculationorder, name="calculationorder"),
    path("calculation/<int:pk>", views.calculation, name="calculation"),
    path("link_order/<int:pk>", views.link_order, name="link_order"),
    # Group management
    path("apply_pi/", views.apply_pi, name="apply_pi"),
    path("get_pi_requests/", views.get_pi_requests, name="get_pi_requests"),
    path(
        "get_pi_requests_table/",
        views.get_pi_requests_table,
        name="get_pi_requests_table",
    ),
    path("profile_groups/", views.profile_groups, name="profile_groups"),
    path("manage_pi_requests/", views.manage_pi_requests, name="manage_pi_requests"),
    path("deny_pi_request/<int:pk>", views.deny_pi_request, name="deny_pi_request"),
    path(
        "accept_pi_request/<int:pk>", views.accept_pi_request, name="accept_pi_request"
    ),
    path("add_user/", views.add_user, name="add_user"),
    path("gen_3D/", views.gen_3D, name="gen_3D"),
    path("get_mol_preview/", views.get_mol_preview, name="get_mol_preview"),
    path("remove_user/", views.remove_user, name="remove_user"),
    path("server_summary/", views.server_summary, name="server_summary"),
    # Access management
    path("manage_access/<int:pk>", views.manage_access, name="manage_access"),
    path("add_clusteraccess/", views.add_clusteraccess, name="add_clusteraccess"),
    path("owned_accesses/", views.owned_accesses, name="owned_accesses"),
    path("connect_access/", views.connect_access, name="connect_access"),
    path("disconnect_access/", views.disconnect_access, name="disconnect_access"),
    path("get_command_status/", views.get_command_status, name="get_command_status"),
    path("delete_access/<int:pk>", views.delete_access, name="delete_access"),
    path("load_pub_key/<int:pk>", views.load_pub_key, name="load_pub_key"),
    path("update_access/", views.update_access, name="update_access"),
    path("status_access/", views.status_access, name="status_access"),
    # Calculations
    path("molecule/<int:pk>", views.molecule, name="molecule"),
    path("ensemble/<int:pk>", views.ensemble, name="ensemble"),
    path("details_ensemble/", views.details_ensemble, name="details_ensemble"),
    path("details_structure/", views.details_structure, name="details_structure"),
    path(
        "get_related_calculations/<int:pk>",
        views.get_related_calculations,
        name="get_related_calculations",
    ),
    path("launch/", views.launch, name="launch"),
    path("launch/project/<int:pk>", views.launch_project, name="launch_project"),
    path("load_params/<int:pk>", views.load_params, name="load_params"),
    path("load_preset/<int:pk>", views.load_preset, name="load_preset"),
    path("delete_preset/<int:pk>", views.delete_preset, name="delete_preset"),
    path("presets/", views.launch_presets, name="presets"),
    path("get_cube/", views.get_cube, name="get_cube"),
    path("get_calc_data/<int:pk>", views.get_calc_data, name="get_calc_data"),
    path(
        "get_calc_data_remote/<int:pk>",
        views.get_calc_data_remote,
        name="get_calc_data_remote",
    ),
    path(
        "get_calc_frame/<int:cid>/<int:fid>",
        views.get_calc_frame,
        name="get_calc_frame",
    ),
    path("next_step/<int:pk>", views.next_step, name="next_step"),
    path("info_table/<int:pk>", views.info_table, name="info_table"),
    path("conformer_table/<int:pk>", views.conformer_table, name="conformer_table"),
    path("conformer_table/", views.conformer_table_post, name="conformer_table_post"),
    path("vib_table/<int:pk>", views.vib_table, name="vib_table"),
    path("ir_spectrum/<int:pk>", views.ir_spectrum, name="ir_spectrum"),
    path("log/<int:pk>", views.log, name="log"),
    path("download_log/<int:pk>", views.download_log, name="download_log"),
    path(
        "download_all_logs/<int:pk>", views.download_all_logs, name="download_all_logs"
    ),
    path("verify_calculation/", views.verify_calculation, name="verify_calculation"),
    path("submit_calculation/", views.submit_calculation, name="submit_calculation"),
    path("get_structure/", views.get_structure, name="get_structure"),
    path("get_vib_animation/", views.get_vib_animation, name="get_vib_animation"),
    path(
        "download_structures/<int:ee>",
        views.download_structures,
        name="download_structures",
    ),
    path(
        "download_structures/<int:ee>/<int:num>",
        views.download_structure,
        name="download_structure",
    ),
    path("uvvis/<int:pk>", views.uvvis, name="uvvis"),
    path("nmr/", views.nmr, name="nmr"),
    path("delete_project/", views.delete_project, name="delete_project"),
    path("delete_molecule/", views.delete_molecule, name="delete_molecule"),
    path("delete_ensemble/", views.delete_ensemble, name="delete_ensemble"),
    path("delete_order/", views.delete_order, name="delete_order"),
    path("delete_folder/", views.delete_folder, name="delete_folder"),
    path("change_password/", views.change_password, name="change_password"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
