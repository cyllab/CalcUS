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
from django.contrib.auth.views import LoginView

from frontend import views
from frontend.forms import UserLoginForm

app_name = "frontend"
urlpatterns = [
    # Override the default login page in order to use the ReCaptcha
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html", authentication_form=UserLoginForm
        ),
        name="login",
    ),
    # Home and index
    path("", views.home, name="home"),
    path("home/", views.home, name="home_dup"),
    path("start_trial/", views.start_trial, name="start_trial"),
    path("pricing/", views.pricing, name="pricing"),
    path("checkout/", views.checkout, name="checkout"),
    path("stripe_config/", views.stripe_config, name="stripe_config"),
    path("webhook/", views.webhook, name="webhook"),
    path(
        "subscription_successful/<str:session_id>",
        views.subscription_successful,
        name="subscription_successful",
    ),
    path("create_full_account/", views.create_full_account, name="create_full_account"),
    path("list/", views.IndexView.as_view(), name="list"),
    path("calculations/", views.calculations, name="calculations"),
    path("cloud_order/", views.cloud_order, name="cloud_order"),
    path("cloud_calc/", views.cloud_calc, name="cloud_calc"),
    path("cloud_action/", views.cloud_action, name="cloud_action"),
    path("cloud_refills/", views.cloud_refills, name="cloud_refills"),
    path("cancel_calc/", views.cancel_calc, name="cancel_calc"),
    path("relaunch_calc/", views.relaunch_calc, name="relaunch_calc"),
    path("refetch_calc/", views.refetch_calc, name="refetch_calc"),
    path("toggle_private/", views.toggle_private, name="toggle_private"),
    path("toggle_flag/", views.toggle_flag, name="toggle_flag"),
    path("projects/", views.projects, name="projects"),
    path(
        "projects/<str:user_id>/<str:proj>/<path:folder_path>",
        views.project_folders,
        name="project_folders",
    ),
    path("projects/<str:user_id>", views.projects_by_user, name="projects_by_user"),
    path("get_projects/", views.get_projects, name="get_projects"),
    path(
        "projects/<str:user_id>/<str:proj>",
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
    path("gen_3D/", views.gen_3D, name="gen_3D"),
    path("get_mol_preview/", views.get_mol_preview, name="get_mol_preview"),
    path("check_functional/", views.check_functional, name="check_functional"),
    path("check_basis_set/", views.check_basis_set, name="check_basis_set"),
    path("check_solvent/", views.check_solvent, name="check_solvent"),
    path("aux_molecule/", views.aux_molecule, name="aux_molecule"),
    path("aux_ensemble/", views.aux_ensemble, name="aux_ensemble"),
    path("aux_structure/", views.aux_structure, name="aux_structure"),
    path("please_register/", views.please_register, name="please_register"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("accounts/login", views.login, name="login"),
    path("update_name/", views.update_name, name="update_name"),
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
    path("download_project/<str:pk>", views.download_project, name="download_project"),
    path("download_folder/<str:pk>", views.download_folder, name="download_folder"),
    path("nmr_analysis/<str:pk>/<str:pid>", views.nmr_analysis, name="nmr_analysis"),
    path("get_shifts/", views.get_shifts, name="get_shifts"),
    path("get_exp_spectrum/", views.get_exp_spectrum, name="get_exp_spectrum"),
    path("analyse/<str:project_id>", views.analyse, name="analyse"),
    path("ensemble_map/<str:pk>", views.ensemble_map, name="ensemble_map"),
    path(
        "ensemble_table_body/<str:pk>",
        views.ensemble_table_body,
        name="ensemble_table_body",
    ),
    path("see/<str:pk>", views.see, name="see"),
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
    path("learn/example/<str:pk>", views.example, name="example"),
    path("learn/recipe/<str:pk>", views.recipe, name="recipe"),
    path("calculationorder/<str:pk>", views.calculationorder, name="calculationorder"),
    path("calculation/<str:pk>", views.calculation, name="calculation"),
    path("link_order/<str:pk>", views.link_order, name="link_order"),
    # Group management
    path("profile_groups/", views.profile_groups, name="profile_groups"),
    path("profile_classes/", views.profile_classes, name="profile_classes"),
    path("profile_allocation/", views.profile_allocation, name="profile_allocation"),
    path("add_user/", views.add_user, name="add_user"),
    path("remove_user/", views.remove_user, name="remove_user"),
    path("create_group/", views.create_group, name="create_group"),
    path("dissolve_group/", views.dissolve_group, name="dissolve_group"),
    path("redeem_allocation/", views.redeem_allocation, name="redeem_allocation"),
    path("server_summary/", views.server_summary, name="server_summary"),
    # Access management
    path("manage_access/<str:pk>", views.manage_access, name="manage_access"),
    path("add_clusteraccess/", views.add_clusteraccess, name="add_clusteraccess"),
    path("owned_accesses/", views.owned_accesses, name="owned_accesses"),
    path("connect_access/", views.connect_access, name="connect_access"),
    path("disconnect_access/", views.disconnect_access, name="disconnect_access"),
    path("get_command_status/", views.get_command_status, name="get_command_status"),
    path("delete_access/<str:pk>", views.delete_access, name="delete_access"),
    path("load_pub_key/<str:pk>", views.load_pub_key, name="load_pub_key"),
    path("load_password/", views.load_password, name="load_password"),
    path("update_access/", views.update_access, name="update_access"),
    path("status_access/", views.status_access, name="status_access"),
    # Calculations
    path("molecule/<str:pk>", views.molecule, name="molecule"),
    path("ensemble/<str:pk>", views.ensemble, name="ensemble"),
    path("details_ensemble/", views.details_ensemble, name="details_ensemble"),
    path("details_structure/", views.details_structure, name="details_structure"),
    path(
        "get_related_calculations/<str:pk>",
        views.get_related_calculations,
        name="get_related_calculations",
    ),
    path("launch/", views.launch, name="launch"),
    path("launch/project/<str:pk>", views.launch_project, name="launch_project"),
    path("load_params/<str:pk>", views.load_params, name="load_params"),
    path("load_preset/<str:pk>", views.load_preset, name="load_preset"),
    path("delete_preset/<str:pk>", views.delete_preset, name="delete_preset"),
    path("presets/", views.launch_presets, name="presets"),
    path("get_cube/", views.get_cube, name="get_cube"),
    path("get_calc_data/<str:pk>", views.get_calc_data, name="get_calc_data"),
    path(
        "get_calc_data_remote/<str:pk>",
        views.get_calc_data_remote,
        name="get_calc_data_remote",
    ),
    path(
        "get_calc_frame/<str:cid>/<str:fid>",
        views.get_calc_frame,
        name="get_calc_frame",
    ),
    path("next_step/<str:pk>", views.next_step, name="next_step"),
    path("info_table/<str:pk>", views.info_table, name="info_table"),
    path("conformer_table/<str:pk>", views.conformer_table, name="conformer_table"),
    path("conformer_table/", views.conformer_table_post, name="conformer_table_post"),
    path("vib_table/<str:pk>", views.vib_table, name="vib_table"),
    path("ir_spectrum/<str:pk>", views.ir_spectrum, name="ir_spectrum"),
    path("log/<str:pk>", views.log, name="log"),
    path("download_log/<str:pk>", views.download_log, name="download_log"),
    path(
        "download_all_logs/<str:pk>", views.download_all_logs, name="download_all_logs"
    ),
    path("verify_calculation/", views.verify_calculation, name="verify_calculation"),
    path("submit_calculation/", views.submit_calculation, name="submit_calculation"),
    path("get_structure/", views.get_structure, name="get_structure"),
    path("get_vib_animation/", views.get_vib_animation, name="get_vib_animation"),
    path(
        "download_structures/<str:ee>",
        views.download_structures,
        name="download_structures",
    ),
    path(
        "download_structures/<str:ee>/<int:num>",
        views.download_structure,
        name="download_structure",
    ),
    path("uvvis/<str:pk>", views.uvvis, name="uvvis"),
    path("nmr/", views.nmr, name="nmr"),
    path("delete_project/", views.delete_project, name="delete_project"),
    path("delete_molecule/", views.delete_molecule, name="delete_molecule"),
    path("delete_ensemble/", views.delete_ensemble, name="delete_ensemble"),
    path("delete_order/", views.delete_order, name="delete_order"),
    path("delete_folder/", views.delete_folder, name="delete_folder"),
    path("flowchart/", views.flowchart, name="flowchart"),
    path("create_flowchart/", views.create_flowchart, name="create_flowchart"),
    path("submit_flowchart/", views.submit_flowchart, name="submit_flowchart"),
    path(
        "verify_flowchart_calculation/",
        views.verify_flowchart_calculation,
        name="verify_flowchart_calculation",
    ),
    path(
        "load_flowchart_params/<int:pk>",
        views.load_flowchart_params,
        name="load_flowchart_params",
    ),
    path("change_password/", views.change_password, name="change_password"),
    path(
        "submit_flowchart_input/",
        views.submit_flowchart_input,
        name="submit_flowchart_input",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
