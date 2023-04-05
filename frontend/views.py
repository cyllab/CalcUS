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


import json
import os
import glob
import random
import string
import bleach
import math
import time
import zipfile
from os.path import basename
from io import BytesIO
import basis_set_exchange
import numpy as np
import tempfile
import json
import ccinput

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import generic
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth import login, update_session_auth_hash
from django.utils.datastructures import MultiValueDictKeyError
from django.db.models import Prefetch
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import login, authenticate
from django.db.models import Q

from .forms import (
    ResearcherCreateForm,
    StudentCreateForm,
    TrialUserCreateForm,
    CreateFullAccountForm,
)
from .models import (
    Calculation,
    User,
    Project,
    ClusterAccess,
    Example,
    ResearchGroup,
    ClassGroup,
    Parameters,
    Structure,
    Ensemble,
    BasicStep,
    CalculationOrder,
    Molecule,
    Property,
    Filter,
    Preset,
    Recipe,
    Folder,
    CalculationFrame,
    Flowchart,
    Step,
    FlowchartOrder,
    ResourceAllocation,
)
from .tasks import (
    dispatcher,
    del_project,
    del_molecule,
    del_ensemble,
    del_order,
    BASICSTEP_TABLE,
    SPECIAL_FUNCTIONALS,
    cancel,
    run_calc,
    send_cluster_command,
    load_output_files,
    system,
    analyse_opt,
    generate_xyz_structure,
    gen_fingerprint,
    send_gcloud_task,
    plot_peaks,
    get_calc_size,
    record_event_analytics,
)
from .decorators import superuser_required

from frontend import tasks
from .decorators import superuser_required
from .constants import *
from .libxyz import parse_xyz_from_text, equivalent_atoms
from .environment_variables import *
from .helpers import get_xyz_from_Gaussian_input, get_random_string

from shutil import copyfile, make_archive, rmtree
from django.db.models.functions import Lower
from django.conf import settings

from throttle.decorators import throttle

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s]  %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)


class IndexView(generic.ListView):
    template_name = "frontend/dynamic/list.html"
    context_object_name = "latest_frontend"
    paginate_by = "20"

    def get_queryset(self, *args, **kwargs):
        if isinstance(self.request.user, AnonymousUser):
            return []

        try:
            page = int(self.request.GET.get("page"))
        except KeyError:
            page = 0

        self.request.session["previous_page"] = page
        proj = clean(self.request.GET.get("project"))
        type = clean(self.request.GET.get("type"))
        status = clean(self.request.GET.get("status"))
        target_user_id = clean(self.request.GET.get("user_id"))
        mode = clean(self.request.GET.get("mode"))

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return []

        if user_intersection(target_user, self.request.user):
            if mode in ["Workspace", "Unseen only"]:
                hits = target_user.calculationorder_set.filter(hidden=False).exclude(
                    author=None
                )
            elif mode == "All orders":
                hits = target_user.calculationorder_set.all().exclude(author=None)

            if proj != "All projects":
                hits = hits.filter(project__name=proj)
            if type != "All steps":
                hits = hits.filter(step__name=type)
            if status != "All statuses":
                new_hits = []
                for hit in hits:
                    if hit.status == Calculation.CALC_STATUSES[status]:
                        new_hits.append(hit)
                hits = new_hits
            if mode == "Unseen only":
                new_hits = []
                for hit in hits:
                    if hit.status != hit.last_seen_status:
                        new_hits.append(hit)
                hits = new_hits

            res = sorted(
                hits,
                key=lambda d: (1 if d.new_status or d.status == 1 else 0, d.date),
                reverse=True,
            )
            return res
        else:
            return []


def home(request):
    return render(request, "frontend/home.html")


def register(request):
    acc_type = ""
    if request.method == "POST" and "acc_type" in request.POST:
        acc_type = clean(request.POST["acc_type"])
        if acc_type == "student":
            form_student = StudentCreateForm(request.POST)
            if form_student.is_valid():
                form_student.save()
                user = authenticate(
                    request,
                    email=form_student.rand_email,
                    password=form_student.rand_password,
                )
                record_event_analytics(request, "register_student")
                if user:
                    login(request, user)
                    return redirect("/projects/")  # Quickstart page?
                else:
                    logger.error(f"Could not log in student")
            form_researcher = ResearcherCreateForm()
        elif acc_type == "researcher":
            form_researcher = ResearcherCreateForm(request.POST)
            if form_researcher.is_valid():
                form_researcher.save()
                email = form_researcher.cleaned_data.get("email")
                password = form_researcher.cleaned_data.get("password1")
                user = authenticate(request, email=email, password=password)
                record_event_analytics(request, "register_full")
                if user:
                    login(request, user)
                    return redirect("/projects/")  # Quickstart page?
                else:
                    logger.error(f"Could not log in researcher {email}")
            form_student = StudentCreateForm()
        else:
            logger.error(f"Invalid account type: {acc_type}")
            form_researcher = ResearcherCreateForm()
            form_student = StudentCreateForm()
    else:
        form_researcher = ResearcherCreateForm()
        form_student = StudentCreateForm()

    return render(
        request,
        "registration/register.html",
        {
            "form_student": form_student,
            "form_researcher": form_researcher,
            "acc_type": acc_type,
        },
    )


def start_trial(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/launch/")
    if not settings.ALLOW_TRIAL:
        return HttpResponseRedirect("/home/")

    if request.method == "POST":
        form = TrialUserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(
                request,
                email=form.rand_email,
                password=form.rand_password,
            )
            record_event_analytics(request, "start_trial")
            if user:
                login(request, user)
                return redirect("/launch/")
            else:
                logger.error(f"Could not log in trial user")
    else:
        form = TrialUserCreateForm()

    return render(
        request, "registration/start_trial.html", {"form": form, "trial_tos": trial_tos}
    )


@login_required
def periodictable(request):
    return render(request, "frontend/dynamic/periodictable.html")


@login_required
def get_available_bs(request):
    if "elements" in request.POST.keys():
        raw_el = clean(request.POST["elements"])
        elements = [i.strip() for i in raw_el.split(" ") if i.strip() != ""]
    else:
        elements = None

    basis_sets = basis_set_exchange.filter_basis_sets(elements=elements)
    response = ""
    for k in basis_sets.keys():
        name = basis_sets[k]["display_name"]
        response += f"""<option value="{k}">{name}</option>\n"""
    return HttpResponse(response)


@login_required
def get_available_elements(request):
    if "bs" in request.POST.keys():
        bs = clean(request.POST["bs"])
    else:
        return HttpResponse(status=204)

    md = basis_set_exchange.get_metadata()
    if bs not in md.keys():
        return HttpResponse(status=404)

    version = md[bs]["latest_version"]
    elements = md[bs]["versions"][version]["elements"]
    response = " ".join(elements)
    return HttpResponse(response)


@login_required
def aux_molecule(request):
    if "proj" not in request.POST.keys():
        return HttpResponse(status=404)

    project = clean(request.POST["proj"])

    if project.strip() == "" or project == "New Project":
        return HttpResponse(status=204)

    try:
        project_set = request.user.project_set.filter(name=project)
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if len(project_set) != 1:
        logger.warning("More than one project with the same name found!")
        return HttpResponse(status=404)
    else:
        project_obj = project_set[0]

    return render(
        request,
        "frontend/dynamic/aux_molecule.html",
        {"molecules": project_obj.molecule_set.all()},
    )


@login_required
def aux_ensemble(request):
    if "mol_id" not in request.POST.keys():
        return HttpResponse(status=404)

    _id = clean(request.POST["mol_id"])
    if _id.strip() == "":
        return HttpResponse(status=204)

    try:
        mol = Molecule.objects.get(pk=_id)
    except Molecule.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_molecule(mol, request.user):
        return HttpResponse(status=404)

    return render(
        request,
        "frontend/dynamic/aux_ensembles.html",
        {"ensembles": mol.ensemble_set.all()},
    )


@login_required
def aux_structure(request):
    if "e_id" not in request.POST.keys():
        return HttpResponse(status=404)

    _id = clean(request.POST["e_id"])
    if _id.strip() == "":
        return HttpResponse(status=204)

    try:
        e = Ensemble.objects.get(pk=_id)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_ensemble(e, request.user):
        return HttpResponse(status=404)

    return render(
        request,
        "frontend/dynamic/aux_structures.html",
        {"structures": e.structure_set.all()},
    )


@login_required
def calculations(request):
    teammates = []
    if request.user.member_of:
        for t in request.user.member_of.members.all():
            teammates.append((t.name, t.id))

    if request.user.member_of and request.user.member_of.PI:
        teammates.append((request.user.member_of.PI.name, request.user.member_of.PI.id))

    if request.user.PI_of:
        for g in request.user.PI_of.all():
            for t in g.members.all():
                teammates.append((t.username, t.id))

    teammates = list(set(teammates))

    for ind, t in enumerate(teammates):
        if t[1] == request.user.id:
            del teammates[ind]
            break

    return render(
        request,
        "frontend/calculations.html",
        {
            "steps": BasicStep.objects.all(),
            "teammates": teammates,
        },
    )


@login_required
def projects(request):
    return render(
        request,
        "frontend/projects.html",
        {
            "target_user": request.user,
            "projects": request.user.project_set.all(),
        },
    )


@login_required
def projects_by_user(request, user_id):
    target_user_id = clean(user_id)

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if request.user == target_user:
        return render(
            request,
            "frontend/projects.html",
            {
                "user": request.user,
                "target_user": target_user,
                "projects": request.user.project_set.all(),
            },
        )
    elif user_intersection(target_user, request.user):
        return render(
            request,
            "frontend/projects.html",
            {
                "user": request.user,
                "target_user": target_user,
                "projects": target_user.project_set.filter(private=0),
            },
        )

    else:
        return HttpResponse(status=404)


@login_required
def get_projects(request):
    if request.method == "POST":
        target_user_id = clean(request.POST["user_id"])

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse(status=404)

        if request.user == target_user:
            return render(
                request,
                "frontend/dynamic/project_list.html",
                {"projects": target_user.project_set.all()},
            )
        elif user_intersection(target_user, request.user):
            return render(
                request,
                "frontend/dynamic/project_list.html",
                {"projects": target_user.project_set.filter(private=0)},
            )
        else:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)


@login_required
def create_project(request):
    if request.method == "POST":
        proj = Project.objects.create(name="My Project", author=request.user)

        return HttpResponse(f"{proj.id};{proj.name}")
    else:
        return HttpResponse(status=404)


@login_required
def create_flowchart(request):
    if request.method == "POST":
        profile = request.user
        if "flowchart_name" in request.POST.keys():
            flowchart_name = clean(request.POST["flowchart_name"])
        if "flowchart_data" in request.POST.keys():
            flowchart_dat = clean(request.POST["flowchart_data"])
        flowchart_view = Flowchart.objects.create(
            name=flowchart_name, author=request.user, flowchart=flowchart_dat
        )
        flowchart_view.save()
        if "flowchart_order_id" in request.POST.keys():
            flowchart_order_id = request.POST["flowchart_order_id"]
            if flowchart_order_id != "":
                flowchart_order_id = request.POST["flowchart_order_id"]
                flowchart_order_obj = FlowchartOrder.objects.get(pk=flowchart_order_id)
                flowchart_order_obj.flowchart = flowchart_view
                flowchart_order_obj.save()
        calc_name = request.POST.getlist("calc_name[]")
        calc_para_list = request.POST["calc_para_array"]
        y = json.loads(calc_para_list)
        flowchart_para_dict = {}
        flowchart_step_dict = {}
        for i in y:
            if i is not None:
                para_dict = {}
                for j in i:
                    para_dict[j["name"]] = j["value"]
                ret = parse_parameters(
                    request, para_dict, verify=False, is_flowchart=True
                )
                if isinstance(ret, str):
                    print("Error in Parameters")
                else:
                    params, step = ret
                    flowchart_para_dict[int(para_dict["para_calc_id"])] = params
                    flowchart_step_dict[int(para_dict["para_calc_id"])] = step
        calc_id = request.POST.getlist("calc_id[]")
        calc_parent_id = request.POST.getlist("calc_parent_id[]")
        calc_id = [int(x) for x in calc_id]
        calc_parent_id = [int(x) for x in calc_parent_id]
        max_id = max(calc_id)
        parent_dict = {}
        for i in range(max_id + 1):
            if i in calc_id:
                index = calc_id.index(i)
                parent_id = calc_parent_id[index]
                if parent_id in parent_dict.keys():
                    obj_parent = parent_dict.get(parent_id)
                    if index in flowchart_para_dict:
                        obj_para = flowchart_para_dict[index]
                        obj_para.save()
                        obj_view = Step.objects.create(
                            name=calc_name[index],
                            flowchart=flowchart_view,
                            step=flowchart_step_dict[index],
                            parameters=obj_para,
                            parentId=obj_parent,
                        )
                    else:
                        obj_view = Step.objects.create(
                            name=calc_name[index],
                            flowchart=flowchart_view,
                            step=None,
                            parameters=None,
                            parentId=obj_parent,
                        )
                    obj_view.save()
                    parent_dict[i] = obj_view
                else:
                    obj_view = Step.objects.create(
                        name=calc_name[index], flowchart=flowchart_view, parentId=None
                    )
                    obj_view.save()
                    parent_dict[i] = obj_view
        return HttpResponse(status=200)


@login_required
def submit_flowchart(request):
    keysList = list(request.POST)
    flowchart_id = keysList[0]
    flowchart_obj = Flowchart.objects.get(pk=flowchart_id)
    flowchart_order_obj = flowchart_obj.flowchartorder_set.all()
    drawing = None
    for i in range(flowchart_obj.step_set.all().count() - 1):
        dispatcher.delay(
            str(flowchart_order_obj[0].id),
            drawing,
            is_flowchart=True,
            flowchartStepObjectId=str(flowchart_obj.step_set.all()[i + 1].id),
        )
    return HttpResponse(status=200)


@login_required
def create_folder(request):
    if request.method == "POST":
        if "current_folder_id" not in request.POST.keys():
            return HttpResponse(status=403)

        current_folder_id = clean(request.POST["current_folder_id"])

        try:
            current_folder = Folder.objects.get(pk=current_folder_id)
        except Folder.DoesNotExist:
            return HttpResponse(status=404)

        if current_folder.depth > MAX_FOLDER_DEPTH:
            return HttpResponse(status=403)

        if current_folder.project.author != request.user:
            return HttpResponse(status=403)

        for i in range(1, 6):
            try:
                existing_folder = Folder.objects.get(name=f"My Folder {i}")
            except Folder.DoesNotExist:
                break
        else:
            return HttpResponse(status=403)

        folder = Folder.objects.create(
            name=f"My Folder {i}",
            project=current_folder.project,
            parent_folder=current_folder,
        )
        folder.depth = current_folder.depth + 1
        folder.save()

        return HttpResponse(f"{folder.id};{folder.name}")
    else:
        return HttpResponse(status=404)


@login_required
def project_details(request, user_id, proj):
    target_project = clean(proj)
    target_user_id = clean(user_id)

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return HttpResponseRedirect("/home/")

    if user_intersection(target_user, request.user):
        try:
            project = target_user.project_set.get(name=target_project)
        except Project.DoesNotExist:
            return HttpResponseRedirect("/home/")

        if can_view_project(project, request.user):
            molecules = []
            for m in (
                project.molecule_set.prefetch_related("ensemble_set")
                .all()
                .order_by(Lower("name"))
            ):
                molecules.append(m)

            return render(
                request,
                "frontend/project_details.html",
                {
                    "molecules": molecules,
                    "project": project,
                },
            )
        else:
            return HttpResponseRedirect("/home/")
    else:
        return HttpResponseRedirect("/home/")


def clean(txt):
    filter(lambda x: x in string.printable, txt)
    return bleach.clean(txt)


def clean_filename(txt):
    return clean(txt).replace(" ", "_").replace("/", "_")


@login_required
def molecule(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect("/home/")

    if not can_view_molecule(mol, request.user):
        return redirect("/home/")

    return render(
        request,
        "frontend/molecule.html",
        {
            "ensembles": mol.ensemble_set.filter(hidden=False),
            "molecule": mol,
        },
    )


@login_required
def ensemble_table_body(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect("/home/")

    if not can_view_molecule(mol, request.user):
        return redirect("/home/")

    return render(
        request,
        "frontend/dynamic/ensemble_table_body.html",
        {"molecule": mol},
    )


@login_required
def ensemble(request, pk):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect("/home/")

    if not can_view_ensemble(e, request.user):
        return redirect("/home/")

    return render(
        request,
        "frontend/ensemble.html",
        {"ensemble": e},
    )


def _get_related_calculations(e):
    orders = list(set([i.order for i in e.calculation_set.all()]))
    orders += list(e.calculationorder_set.prefetch_related("calculation_set").all())
    return orders


@login_required
def get_related_calculations(request, pk):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect("/home/")

    if not can_view_ensemble(e, request.user):
        return redirect("/home/")

    orders = _get_related_calculations(e)
    return render(
        request,
        "frontend/dynamic/get_related_calculations.html",
        {
            "ensemble": e,
            "orders": orders,
        },
    )


@login_required
def nmr_analysis(request, pk, pid):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect("/home/")

    if not can_view_ensemble(e, request.user):
        return redirect("/home/")

    try:
        param = Parameters.objects.get(pk=pid)
    except Parameters.DoesNotExist:
        return redirect("/home/")

    if not can_view_parameters(param, request.user):
        return redirect("/home/")

    return render(
        request,
        "frontend/nmr_analysis.html",
        {"ensemble": e, "parameters": param},
    )


def _get_shifts(request):
    if "id" not in request.POST.keys():
        return ""

    if "pid" not in request.POST.keys():
        return ""

    id = clean(request.POST["id"])
    pid = clean(request.POST["pid"])

    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return ""

    if not can_view_ensemble(e, request.user):
        return ""

    try:
        param = Parameters.objects.get(pk=pid)
    except Parameters.DoesNotExist:
        return ""

    if not can_view_parameters(param, request.user):
        return ""

    scaling_factors = {}
    if "scaling_factors" in request.POST.keys():
        scaling_str = clean(request.POST["scaling_factors"])
        for entry in scaling_str.split(";"):
            if entry.strip() == "":
                continue

            el, m, b = entry.split(",")
            el = clean(el)
            try:
                m = float(m)
                b = float(b)
            except ValueError:
                continue
            if el not in scaling_factors.keys():
                scaling_factors[el] = [m, b]

    structures = e.structure_set.all()
    shifts = {}
    s_ids = []
    for s in structures:
        try:
            p = s.properties.get(parameters=param)
        except Property.DoesNotExist:
            continue

        if p.simple_nmr == "":
            continue

        weighted_shifts = e.weighted_nmr_shifts(param)
        for entry in weighted_shifts:
            num = int(entry[0]) - 1
            el = entry[1]
            shift = float(entry[2])
            shifts[num] = [el, shift, "-"]

    xyz = parse_xyz_from_text(s.xyz_structure)
    eqs = equivalent_atoms(xyz)
    for nums in eqs:
        lnums = len(nums)
        eq_shift = sum([shifts[i][1] for i in nums]) / lnums
        for num in nums:
            shifts[num][1] = eq_shift

    if len(scaling_factors.keys()) > 0:
        for shift in shifts.keys():
            el = shifts[shift][0]
            if el in scaling_factors.keys():
                slope, intercept = scaling_factors[el]
                s = shifts[shift][1]
                shifts[shift][2] = f"{(s - intercept) / slope:.3f}"
    return shifts


@login_required
def get_shifts(request):
    shifts = _get_shifts(request)

    if shifts == "":
        return HttpResponse(status=404)

    CELL = """
    <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{:.3f}</td>
            <td>{}</td>
    </tr>"""

    def sort_nmr_shifts(l):
        pred = shifts[l][2]
        if pred == "-":
            return -1
        return float(pred)

    response = ""
    for shift in sorted(shifts.keys(), key=sort_nmr_shifts, reverse=True):
        response += CELL.format(shift, *shifts[shift])

    return HttpResponse(response)


### Legacy, might be removed
@login_required
def get_exp_spectrum_from_raw_data(request):
    import nmrglue as ng

    t = time.time()
    d = f"/tmp/nmr_{t}"
    os.mkdir(d)
    for ind, f in enumerate(request.FILES.getlist("file")):
        in_file = f.read()  # not cleaned
        with open(os.path.join(d, f.name), "wb") as out:
            out.write(in_file)

    dic, fid = ng.fileio.bruker.read(d)

    zero_fill_size = 32768
    fid = ng.bruker.remove_digital_filter(dic, fid)
    fid = ng.proc_base.zf_size(fid, zero_fill_size)  # <2>
    fid = ng.proc_base.rev(fid)  # <3>
    fid = ng.proc_base.fft(fid)
    fid = ng.proc_autophase.autops(fid, "acme")

    offset = (float(dic["acqus"]["SW"]) / 2.0) - (
        float(dic["acqus"]["O1"]) / float(dic["acqus"]["BF1"])
    )
    start = float(dic["acqus"]["SW"]) - offset
    end = -offset
    step = float(dic["acqus"]["SW"]) / zero_fill_size

    ppms = np.arange(start, end, -step)[:zero_fill_size]

    fid = ng.proc_base.mult(fid, c=1.0 / max(fid))

    def plotspectra(ppms, data, start=None, stop=None):
        if start:  # <1>
            dx = abs(ppms - start)
            ixs = list(dx).index(min(dx))
            ppms = ppms[ixs:]
            data = data[:, ixs:]
        if stop:
            dx = abs(ppms - stop)
            ixs = list(dx).index(min(dx))
            ppms = ppms[:ixs]
            data = data[:, :ixs]

        return ppms, data

    ppms, fid = plotspectra(ppms, np.array([fid]), start=10, stop=0)
    shifts = _get_shifts(request)
    if shifts == "":
        response = "PPM,Signal\n"
        for x, y in zip(ppms[0::10], fid[0, 0::10]):
            response += f"{-x},{np.real(y)}\n"

        return HttpResponse(response)
    else:
        sigma = 0.001

        def plot_peaks(_x, PP):
            val = 0
            for w in PP:
                dd = list(abs(ppms - w))
                T = fid[0, dd.index(min(dd))]
                val += np.exp(-((_x - w) ** 2) / sigma)
            val = val / max(val)
            return val

        _ppms = ppms[0::10]
        _fid = fid[0, 0::10] / max(fid[0, 0::10])
        l_shifts = [float(shifts[i][2]) for i in shifts if shifts[i][0] == "H"]
        pred = plot_peaks(_ppms, l_shifts)
        response = "PPM,Signal,Prediction\n"
        for x, y, z in zip(_ppms, _fid, pred):
            response += f"{-x:.3f},{np.real(y):.3f},{z:.3f}\n"
        return HttpResponse(response)


@login_required
def get_exp_spectrum(request):
    with tempfile.TemporaryDirectory() as d:
        if "spectrum" not in request.FILES:
            return HttpResponse(status=400)

        spectrum = request.FILES["spectrum"].read().decode()

    points = spectrum.strip().split("\n")

    if len(points) > 20000:
        step = len(points) // 20000
    else:
        step = 1

    ppms = []
    signal = []
    for text in points[0::step]:
        shift, sig = text.split()
        ppms.append(float(shift))
        signal.append(float(sig))

    start = ppms[0]
    end = ppms[-1]

    signal = np.array(signal) / max(signal)

    shifts = _get_shifts(request)
    if shifts == "":
        response = "PPM,Signal\n"
        for x, y in zip(ppms, signal):
            response += f"{-x:.5f},{y:.5f}\n"

        return HttpResponse(response)
    else:
        l_shifts = [(float(shifts[i][2]), 1) for i in shifts if shifts[i][0] == "H"]

        pred = plot_peaks(np.array(ppms), l_shifts, sigma=0.001)
        pred = pred / max(pred)
        response = "PPM,Signal,Prediction\n"

        for x, y, z in zip(ppms, signal, pred):
            response += f"{-x:.5f},{y:.5f},{z:.5f}\n"
        return HttpResponse(response)


@login_required
def link_order(request, pk):
    try:
        o = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponseRedirect("/calculations/")

    if not can_view_order(o, request.user) or o.calculation_set.count() == 0:
        return HttpResponseRedirect("/calculations/")

    if request.user == o.author:
        if o.new_status:
            o.last_seen_status = o.status
            o.author.unseen_calculations = max(o.author.unseen_calculations - 1, 0)
            o.author.save()
            o.save()

    if o.result_ensemble:
        return HttpResponseRedirect(f"/ensemble/{o.result_ensemble.id}")
    else:
        if o.ensemble is not None:
            return HttpResponseRedirect(f"/ensemble/{o.ensemble.id}")
        elif o.structure:
            return HttpResponseRedirect(f"/ensemble/{o.structure.parent_ensemble.id}")
        else:
            return HttpResponseRedirect("/calculations/")


@login_required
def details_ensemble(request):
    if request.method == "POST":
        pk = clean(request.POST["id"])
        try:
            p_id = clean(request.POST["p_id"])
        except KeyError:
            return HttpResponse(status=204)

        try:
            e = Ensemble.objects.get(pk=pk)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)
        try:
            p = Parameters.objects.get(pk=p_id)
        except Parameters.DoesNotExist:
            return HttpResponse(status=403)

        if not can_view_ensemble(e, request.user):
            return HttpResponse(status=403)

        if e.has_nmr(p):
            shifts = e.weighted_nmr_shifts(p)
            return render(
                request,
                "frontend/dynamic/details_ensemble.html",
                {
                    "ensemble": e,
                    "parameters": p,
                    "shifts": shifts,
                },
            )
        else:
            return render(
                request,
                "frontend/dynamic/details_ensemble.html",
                {"ensemble": e, "parameters": p},
            )

    return HttpResponse(status=403)


@login_required
def details_structure(request):
    if request.method == "POST":
        pk = clean(request.POST["id"])
        try:
            p_id = clean(request.POST["p_id"])
            num = int(clean(request.POST["num"]))
        except KeyError:
            return HttpResponse(status=204)

        try:
            e = Ensemble.objects.get(pk=pk)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if not can_view_ensemble(e, request.user):
            return HttpResponse(status=403)

        try:
            s = e.structure_set.get(number=num)
        except Structure.DoesNotExist:
            return HttpResponse(status=403)

        try:
            p = Parameters.objects.get(pk=p_id)
        except Parameters.DoesNotExist:
            return HttpResponse(status=403)

        for prop in s.properties.all():
            if prop.parameters == p:
                break
        else:
            return HttpResponse(status=404)

        return render(
            request,
            "frontend/dynamic/details_structure.html",
            {
                "structure": s,
                "property": prop,
                "ensemble": e,
            },
        )

    return HttpResponse(status=403)


def learn(request):
    examples = Example.objects.all()
    recipes = Recipe.objects.all()

    return render(
        request, "frontend/learn.html", {"examples": examples, "recipes": recipes}
    )


def flowchart(request):
    flag = True
    flowchartsData = Flowchart.objects.all()
    return render(
        request,
        "frontend/flowchart.html",
        {
            "is_flowchart": flag,
            "flowchartsData": flowchartsData,
            "procs": BasicStep.objects.all(),
            "stepsData": Step.objects.all(),
            "profile": request.user,
            "allow_local_calc": settings.ALLOW_LOCAL_CALC,
            "packages": settings.PACKAGES,
        },
    )


def example(request, pk):
    try:
        ex = Example.objects.get(pk=pk)
    except Example.DoesNotExist:
        pass

    return render(request, "examples/" + ex.page_path, {})


def recipe(request, pk):
    try:
        r = Recipe.objects.get(pk=pk)
    except Recipe.DoesNotExist:
        pass

    return render(request, "recipes/" + r.page_path, {})


def please_register(request):
    return render(request, "frontend/please_register.html", {})


def error(request, msg):
    if is_test:
        print("VIEWS ERROR: " + msg)
    return render(
        request,
        "frontend/error.html",
        {
            "error_message": msg,
        },
    )


@csrf_exempt
def cloud_refills(request):
    if not "X-CloudScheduler" in request.headers.keys():
        return HttpResponse(status=403)

    now = timezone.now()
    for u in User.objects.filter(is_temporary=False).all():
        if now > u.last_free_refill + timezone.timedelta(days=30):
            time_left = u.allocated_seconds - u.billed_seconds
            refill = 300 - time_left
            if refill > 0:
                u.last_free_refill = now
                u.save()

                r = ResourceAllocation.objects.create(
                    code=get_random_string(n=128),
                    allocation_seconds=refill,
                    note=ResourceAllocation.MONTHLY_FREE_REFILL,
                )
                r.redeem(u)
                logger.info(f"Issued a free refill of {refill} seconds to user {u.id}")
    return HttpResponse(status=200)


@csrf_exempt
def cloud_order(request):
    if not "X-Cloudtasks-QueueName" in request.headers.keys():
        return HttpResponse(status=403)

    body = request.body.decode("utf-8")

    try:
        o = CalculationOrder.objects.get(pk=body)
    except ValueError:
        logger.error(f"Could not convert to int: {body}")
        return HttpResponse(status=400)
    except CalculationOrder.DoesNotExist:
        logger.error(f"Could not find calculation order number {body}")
        return HttpResponse(status=400)

    dispatcher(o.id)

    return HttpResponse(status=200)


@csrf_exempt
def cloud_calc(request):
    if not "X-Cloudtasks-QueueName" in request.headers.keys():
        return HttpResponse(status=403)

    body = request.body.decode("utf-8")

    try:
        calc = Calculation.objects.get(pk=body)
    except ValueError:
        logger.error(f"Could not convert to int: {body}")
        return HttpResponse(status=400)
    except Calculation.DoesNotExist:
        logger.error(f"Could not find calculation number {body}")
        return HttpResponse(status=400)

    try:
        ret = run_calc(calc.id)
    except Exception as e:
        logger.error(f"Calculation {calc.id} finished with exception {str(e)}")
        raise e

    if ret != 0:
        logger.warning(f"Calculation {calc.id} finished with code {ret}")
        calc.status = 3
        calc.save()

    return HttpResponse(status=200)


@csrf_exempt
def cloud_action(request):
    if not "X-Cloudtasks-QueueName" in request.headers.keys():
        return HttpResponse(status=403)

    body = request.body.decode("utf-8")

    try:
        func_name, arg = body.split(";")
    except TypeError:
        logger.error(f"Invalid cloud action: {body}")
        return HttpResponse(status=400)

    if func_name not in [
        "del_project",
        "del_order",
        "del_molecule",
        "del_ensemble",
    ]:
        logger.error(f"Invalid cloud action: {body}")
        return HttpResponse(status=400)

    getattr(tasks, func_name)(arg)
    return HttpResponse(status=200)


def parse_parameters(request, parameters_dict, is_flowchart=None, verify=False):
    if "calc_type" in parameters_dict.keys():
        try:
            step = BasicStep.objects.get(name=clean(parameters_dict["calc_type"]))
        except BasicStep.DoesNotExist:
            return "No such procedure"

        if (
            "ALL" not in settings.LOCAL_ALLOWED_STEPS
            and step.name not in settings.LOCAL_ALLOWED_STEPS
        ):
            return "This type of calculation has been disabled"

    else:
        return "No calculation type"

    if is_flowchart is None:
        if "calc_project" in parameters_dict.keys():
            project = clean(parameters_dict["calc_project"])
            if project.strip() == "":
                return "No calculation project"
        else:
            return "No calculation project"

    if "calc_charge" in parameters_dict.keys():
        try:
            charge = int(clean(parameters_dict["calc_charge"]).replace("+", ""))
        except ValueError:
            return "Invalid calculation charge"
    else:
        return "No calculation charge"

    if "calc_multiplicity" in parameters_dict.keys():
        try:
            mult = int(clean(parameters_dict["calc_multiplicity"]))
        except ValueError:
            return "Invalid multiplicity"
        if mult < 1:
            return "Invalid multiplicity"
    else:
        return "No calculation multiplicity"

    if "calc_solvent" in parameters_dict.keys():
        solvent = clean(parameters_dict["calc_solvent"])
        if solvent.strip() == "":
            solvent = "Vacuum"
    else:
        solvent = "Vacuum"

    if solvent != "Vacuum":
        if "calc_solvation_model" in parameters_dict.keys():
            solvation_model = clean(parameters_dict["calc_solvation_model"])
            if solvation_model not in ["SMD", "PCM", "CPCM", "GBSA", "ALPB"]:
                return "Invalid solvation model"
            if solvation_model in ["GBSA", "ALPB"]:
                solvation_radii = "Default"
            elif "calc_solvation_radii" in parameters_dict.keys():
                solvation_radii = clean(parameters_dict["calc_solvation_radii"])
            else:
                return "No solvation radii"
        else:
            return "No solvation model"
    else:
        solvation_model = ""
        solvation_radii = ""

    if "calc_software" in parameters_dict.keys():
        software = clean(parameters_dict["calc_software"])
        if software.strip() == "":
            return "No software chosen"
        if software not in BASICSTEP_TABLE.keys():
            return "Invalid software chosen"
    else:
        return "No software chosen"

    if "calc_df" in parameters_dict.keys():
        df = clean(parameters_dict["calc_df"])
    else:
        df = ""

    if "calc_custom_bs" in parameters_dict.keys():
        bs = clean(parameters_dict["calc_custom_bs"])
    else:
        bs = ""

    if "calc_theory_level" in parameters_dict.keys():
        _theory = clean(parameters_dict["calc_theory_level"])
        if _theory.strip() == "":
            return "No theory level chosen"
        theory = ccinput.utilities.get_theory_level(_theory)
    else:
        return "No theory level chosen"

    if (
        "ALL" not in settings.LOCAL_ALLOWED_THEORY_LEVELS
        and theory not in settings.LOCAL_ALLOWED_THEORY_LEVELS
    ):
        return "This theory level has been disabled"

    if theory == "dft":
        special_functional = False
        if "calc_pbeh3c" in parameters_dict.keys() and software == "ORCA":
            field_pbeh3c = clean(parameters_dict["calc_pbeh3c"])
            if field_pbeh3c == "on":
                special_functional = True
                functional = "PBEh-3c"
                basis_set = ""

        if not special_functional:
            if "calc_functional" in parameters_dict.keys():
                functional = clean(parameters_dict["calc_functional"])
                if functional.strip() == "":
                    return "No method"
            else:
                return "No method"
            if functional not in SPECIAL_FUNCTIONALS:
                if "calc_basis_set" in parameters_dict.keys():
                    basis_set = clean(parameters_dict["calc_basis_set"])
                    if basis_set.strip() == "":
                        return "No basis set chosen"
                else:
                    return "No basis set chosen"
            else:
                basis_set = ""
    elif theory == "semiempirical":
        if "calc_se_method" in parameters_dict.keys():
            functional = clean(parameters_dict["calc_se_method"])
            if functional.strip() == "":
                return "No semi-empirical method chosen"
            basis_set = ""
        else:
            return "No semi-empirical method chosen"
    elif theory == "hf":
        special_functional = False
        if "calc_hf3c" in parameters_dict.keys() and software == "ORCA":
            field_hf3c = clean(parameters_dict["calc_hf3c"])
            if field_hf3c == "on":
                special_functional = True
                functional = "HF-3c"
                basis_set = ""

        if not special_functional:
            functional = "HF"
            if "calc_basis_set" in parameters_dict.keys():
                basis_set = clean(parameters_dict["calc_basis_set"])
                if basis_set.strip() == "":
                    return "No basis set chosen"
            else:
                return "No basis set chosen"
    elif theory == "mp2":
        if software != "ORCA":
            return "RI-MP2 is only available for ORCA"

        functional = "RI-MP2"
        if "calc_basis_set" in parameters_dict.keys():
            basis_set = clean(parameters_dict["calc_basis_set"])
            if basis_set.strip() == "":
                return "No basis set chosen"
        else:
            return "No basis set chosen"
    elif theory == "xtb":
        if "calc_xtb_method" in parameters_dict.keys():
            functional = clean(parameters_dict["calc_xtb_method"])
            if functional.strip() == "":
                return "No xTB method chosen"
            basis_set = "min"
        else:
            return "No xTB method chosen"

        # TODO: support for Coupled-cluster methods
    else:
        return "Invalid theory level"

    if "calc_driver" in parameters_dict:
        driver = clean(parameters_dict["calc_driver"]).lower()
        if driver not in ["xtb", "gaussian", "orca", "pysisyphus"]:
            return f"Unknown driver: {driver}"
        if driver == software:
            driver = ""
    else:
        driver = ""

    if is_flowchart is None:
        if len(project) > 100:
            return "The chosen project name is too long"

    if step.name not in BASICSTEP_TABLE[software].keys():
        return "Invalid calculation type"

    if "calc_specifications" in parameters_dict.keys():
        specifications = clean(parameters_dict["calc_specifications"]).lower()
    else:
        specifications = ""

    if (
        settings.IS_CLOUD
        and "Conformational Search" in step.name
        and "--gfn" not in specifications
    ):
        # Use GFN-FF by default in the cloud version unless something else is specified by the user
        specifications = (specifications + " --gfnff").strip()

    if is_flowchart is None:
        if project == "New Project":
            new_project_name = clean(parameters_dict["new_project_name"])
            try:
                project_obj = Project.objects.get(
                    name=new_project_name, author=request.user
                )
            except Project.DoesNotExist:
                if not verify:
                    project_obj = Project.objects.create(
                        name=new_project_name, author=request.user
                    )
                else:
                    project_obj = Project(name=new_project_name, author=request.user)
                    # project_obj.save(commit=False)
            else:
                logger.info("Project with that name already exists")
        else:
            try:
                project_set = request.user.project_set.filter(name=project)
            except Profile.DoesNotExist:
                return "No such project"

            if len(project_set) != 1:
                return "More than one project with the same name found!"
            else:
                project_obj = project_set[0]

    _params = {
        "charge": charge,
        "multiplicity": mult,
        "solvent": solvent,
        "method": functional,
        "basis_set": basis_set,
        "software": software,
        "theory_level": theory,
        "solvation_model": solvation_model,
        "solvation_radii": solvation_radii,
        "density_fitting": df,
        "custom_basis_sets": bs,
        "specifications": specifications,
        "driver": driver,
    }

    if is_flowchart is None:
        return _params, project_obj, step
    else:
        return _params, step


@login_required
def save_preset(request):
    ret = parse_parameters(request, request.POST)

    if isinstance(ret, str):
        return HttpResponse(ret)
    _params, project_obj, step = ret

    if "preset_name" in request.POST.keys():
        preset_name = clean(request.POST["preset_name"])
    else:
        return HttpResponse("No preset name")

    params = Parameters.objects.create(**_params)
    preset = Preset.objects.create(name=preset_name, author=request.user, params=params)
    preset.save()
    return HttpResponse("Preset created")


@login_required
def set_project_default(request):
    ret = parse_parameters(request, request.POST)

    if isinstance(ret, str):
        return HttpResponse(ret)

    _params, project_obj, step = ret

    params = Parameters.objects.create(**_params)

    preset = Preset.objects.create(
        name=f"{project_obj.name} Default",
        author=request.user,
        params=params,
    )
    preset.save()

    if project_obj.preset is not None:
        project_obj.preset.delete()

    project_obj.preset = preset
    project_obj.save()

    return HttpResponse("Default parameters updated")


def handle_file_upload(ff, is_local, verify=False):
    in_file = clean(ff.read().decode("utf-8"))
    fname = clean(ff.name)
    filename = ".".join(fname.split(".")[:-1])
    ext = fname.split(".")[-1]
    if ext == "xyz":
        slines = [i.strip() for i in in_file.split("\n") if i.strip() != ""]
        if len(slines) == 0:
            return "Empty file uploaded!"
        elif len(slines[0].split()) > 2:
            # The two first lines are probably missing
            xyz = f"{len(slines)}\n\n" + in_file
        else:
            xyz = in_file
    elif ext in ["mol", "mol2", "sdf", "log", "out", "com", "gjf"]:
        xyz = generate_xyz_structure(False, in_file, ext)
    else:
        return "Unknown file extension (Known formats: .mol, .mol2, .xyz, .sdf, .com, .gjf)"

    if (
        is_local
        and xyz.strip().count("\n") - 2 > settings.LOCAL_MAX_ATOMS
        and settings.LOCAL_MAX_ATOMS != -1
    ):
        return (
            f"Input structures are limited to at most {settings.LOCAL_MAX_ATOMS} atoms"
        )

    if verify:
        return xyz, filename

    s = Structure.objects.create(xyz_structure=xyz)

    _params = Parameters.objects.create(
        software="Unknown",
        method="Unknown",
        basis_set="",
        solvation_model="",
        charge=0,
        multiplicity=1,
    )
    p = Property.objects.create(parent_structure=s, parameters=_params, geom=True)

    return s, filename


def handle_file_upload_flowchart(ff):
    s = Structure.objects.create()
    drawing = False
    in_file = clean(ff.read().decode("utf-8"))
    fname = clean(ff.name)
    filename = ".".join(fname.split(".")[:-1])
    ext = fname.split(".")[-1]
    if ext == "mol":
        s.mol_structure = in_file
        generate_xyz_structure(False, s)
    elif ext == "xyz":
        slines = [i.strip() for i in in_file.split("\n") if i.strip() != ""]
        if len(slines[0].split()) < 2:
            # The two first lines are probably missing
            s.xyz_structure = f"{len(slines)}\n\n" + in_file
        else:
            s.xyz_structure = in_file
    elif ext == "sdf":
        s.sdf_structure = in_file
        generate_xyz_structure(False, s)
    elif ext == "mol2":
        s.mol2_structure = in_file
        generate_xyz_structure(False, s)
    elif ext in ["log", "out"]:
        s.xyz_structure = get_Gaussian_xyz(in_file)
    elif ext in ["com", "gjf"]:
        s.xyz_structure = get_xyz_from_Gaussian_input(in_file)
    else:
        return "Unknown file extension (Known formats: .mol, .mol2, .xyz, .sdf, .com, .gjf)"
    s.save()
    return s, filename


def process_filename(filename):
    if filename.find("_conf") != -1:
        sname = filename.split("_conf")
        if len(sname) > 2:
            return filename, 0
        name = sname[0]
        try:
            num = int(sname[1])
        except ValueError:
            return name, 0
        else:
            return name, num
    else:
        return filename, 0


@login_required
def verify_calculation(request):
    ret = _submit_calculation(request, verify=True)
    if isinstance(ret, str):
        logger.warning(f"Invalid calculation: {ret}")
        return HttpResponse(ret, status=400)
    return HttpResponse(status=200)


@login_required
def submit_flowchart_input(request):
    obj_id = ""
    profile = request.user
    if "calc_mol_name" in request.POST.keys():
        mol_name = clean(request.POST["calc_mol_name"])
    else:
        mol_name = ""
    combine = ""
    if "calc_combine_files" in request.POST.keys():
        combine = clean(request.POST["calc_combine_files"])
    parse_filenames = ""
    if "calc_parse_filenames" in request.POST.keys():
        parse_filenames = clean(request.POST["calc_parse_filenames"])
    else:
        if mol_name == "":
            return "Missing molecule name"
    num_files = 0
    if "calc_project" in request.POST.keys():
        project = clean(request.POST["calc_project"])
        if project.strip() == "":
            return "No calculation project"
    else:
        return "No calculation project"
    if len(project) > 100:
        return "The chosen project name is too long"
    if project == "New Project":
        new_project_name = clean(request.POST["new_project_name"])
        try:
            project_obj = Project.objects.get(
                name=new_project_name, author=request.user
            )
        except Project.DoesNotExist:
            project_obj = Project.objects.create(
                name=new_project_name, author=request.user
            )
        else:
            logger.info("Project with that name already exists")
    else:
        try:
            project_set = profile.project_set.filter(name=project)
        except Profile.DoesNotExist:
            return "No such project"

        if len(project_set) != 1:
            return "More than one project with the same name found!"
        else:
            project_obj = project_set[0]
    if "num_files" in request.POST:
        try:
            num_files = int(clean(request.POST["num_files"]))
        except ValueError:
            logger.warning("Got invalid number of files")
    if (
        len(request.FILES) > 0
    ):  # Can't really verify file uploads before actually processing the files
        files = request.FILES.getlist("file_structure")
        if len(files) > 1:
            if combine == "on" and parse_filenames != "on":
                mol = Molecule.objects.create(name=mol_name, project=project_obj)
                e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
                for ind, ff in enumerate(files):
                    ss = handle_file_upload_flowchart(ff)
                    if isinstance(ss, str):
                        e.structure_set.all().delete()
                        e.delete()
                        mol.delete()
                        return ss
                    struct, filename = ss

                    if ind == 0:
                        fing = gen_fingerprint(struct)
                        mol.inchi = fing
                        mol.save()

                    struct.number = ind + 1
                    struct.parent_ensemble = e
                    struct.save()

                obj = FlowchartOrder.objects.create(
                    name=mol_name,
                    structure=struct,
                    author=request.user,
                    project=project_obj,
                    ensemble=e,
                )
            elif combine != "on" and parse_filenames == "on":
                unique_molecules = {}
                for ff in files:
                    ss = handle_file_upload_flowchart(ff)
                    if isinstance(ss, str):
                        for _mol_name, arr_structs in unique_molecules.items():
                            for struct in arr_structs:
                                struct.delete()
                        return ss
                    struct, filename = ss

                    _mol_name, num = process_filename(filename)

                    struct.number = num
                    struct.save()
                    if _mol_name in unique_molecules.keys():
                        unique_molecules[_mol_name].append(struct)
                    else:
                        unique_molecules[_mol_name] = [struct]

                for _mol_name, arr_structs in unique_molecules.items():
                    used_numbers = []
                    fing = gen_fingerprint(arr_structs[0])
                    mol = Molecule.objects.create(
                        name=_mol_name, inchi=fing, project=project_obj
                    )
                    mol.save()

                    e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
                    for struct in arr_structs:
                        if struct.number == 0:
                            num = 1
                            while num in used_numbers:
                                num += 1
                            struct.number = num
                            used_numbers.append(num)
                        else:
                            used_numbers.append(struct.number)

                        struct.parent_ensemble = e
                        struct.save()
                    obj = FlowchartOrder.objects.create(
                        name=mol_name,
                        structure=struct,
                        author=request.user,
                        project=project_obj,
                        ensemble=e,
                    )
            elif combine == "on" and parse_filenames == "on":
                ss = handle_file_upload_flowchart(files[0])
                if isinstance(ss, HttpResponse):
                    return ss
                struct, filename = ss
                _mol_name, num = process_filename(filename)
                fing = gen_fingerprint(struct)

                mol = Molecule.objects.create(
                    name=_mol_name, project=project_obj, inchi=fing
                )
                e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
                struct.number = 1
                struct.parent_ensemble = e
                struct.save()

                for ind, ff in enumerate(files[1:]):
                    ss = handle_file_upload_flowchart(ff)
                    if isinstance(ss, HttpResponse):
                        e.structure_set.all().delete()
                        e.delete()
                        mol.delete()
                        return ss
                    struct, filename = ss
                    struct.number = ind + 2
                    struct.parent_ensemble = e
                    struct.save()
                obj = FlowchartOrder.objects.create(
                    name=mol_name,
                    structure=struct,
                    author=request.user,
                    project=project_obj,
                    ensemble=e,
                )
            else:
                unique_molecules = {}
                for ff in files:
                    ss = handle_file_upload_flowchart(ff)
                    if isinstance(ss, HttpResponse):
                        for _mol_name, arr_structs in unique_molecules.items():
                            for struct in arr_structs:
                                struct.delete()
                        return ss
                    struct, filename = ss

                    fing = gen_fingerprint(struct)
                    if fing in unique_molecules.keys():
                        unique_molecules[fing].append(struct)
                    else:
                        unique_molecules[fing] = [struct]

                for ind, (fing, arr_struct) in enumerate(unique_molecules.items()):
                    if len(unique_molecules.keys()) > 1:
                        mol = Molecule.objects.create(
                            name=f"{mol_name} set {ind + 1}",
                            inchi=fing,
                            project=project_obj,
                        )
                    else:
                        mol = Molecule.objects.create(
                            name=mol_name, inchi=fing, project=project_obj
                        )
                    e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)

                    for s_num, struct in enumerate(arr_struct):
                        struct.parent_ensemble = e
                        struct.number = s_num + 1
                        struct.save()

                    obj = FlowchartOrder.objects.create(
                        name=mol_name,
                        structure=struct,
                        author=request.user,
                        project=project_obj,
                        ensemble=e,
                    )
        elif len(files) == 1:
            ff = files[0]
            ss = handle_file_upload_flowchart(ff)
            if isinstance(ss, HttpResponse):
                return ss
            struct, filename = ss

            num = 1
            if parse_filenames == "on":
                _mol_name, num = process_filename(names[struct.id])  # Disable mol_name
            else:
                _mol_name = mol_name

            obj = FlowchartOrder.objects.create(
                name=mol_name,
                structure=struct,
                author=request.user,
                project=project_obj,
            )

            fing = gen_fingerprint(struct)
            mol = Molecule.objects.create(
                name=_mol_name, inchi=fing, project=project_obj
            )
            mol.save()

            e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
            obj.ensemble = e
            struct.parent_ensemble = e
            struct.number = num
            struct.save()

            obj.save()
            obj_id = obj.id
    else:  # No file upload
        if "structure" in request.POST.keys():
            drawing = True
            mol_obj = Molecule.objects.create(name=mol_name, project=project_obj)
            e = Ensemble.objects.create(name="Drawn Structure", parent_molecule=mol_obj)
            s = Structure.objects.create(parent_ensemble=e, number=1)
            mol = clean(request.POST["structure"])
            s.mol_structure = mol
            s.save()
            obj = FlowchartOrder.objects.create(
                name=mol_name,
                structure=s,
                author=request.user,
                project=project_obj,
                ensemble=e,
            )
            obj.save()
            obj_id = obj.id
        else:
            return "No input structure"
    ret = obj_id
    return HttpResponse(ret, status=200)


@login_required
def verify_flowchart_calculation(request):
    ret = parse_parameters(request, request.POST, verify=False, is_flowchart=True)
    if isinstance(ret, str):
        logger.warning(f"Invalid calculation: {ret}")
        return HttpResponse(ret, status=400)
    return HttpResponse(status=200)


@login_required
def submit_calculation(request):
    ret = _submit_calculation(request, verify=False)
    if isinstance(ret, str):
        return error(request, ret)
    return ret


def _submit_calculation(request, verify=False):
    ret = parse_parameters(request, request.POST, verify=verify)

    if isinstance(ret, str):
        return ret

    _params, project_obj, step = ret

    if "calc_resource" in request.POST.keys():
        resource = clean(request.POST["calc_resource"])
        if resource.strip() == "":
            return "No computing resource chosen"
    else:
        return "No computing resource chosen"

    if resource != "Local":
        try:
            access = ClusterAccess.objects.get(
                cluster_address=resource, owner=request.user
            )
        except ClusterAccess.DoesNotExist:
            return "No such cluster access"

        if access.owner != request.user:
            return "You do not have the right to use this cluster access"

        is_local = False

        if not settings.ALLOW_REMOTE_CALC:
            return "Remote calculations are disabled"
    else:
        if settings.IS_CLOUD:
            if not request.user.has_sufficient_resources(
                1
            ):  # Placeholder calculation time
                return "You have insufficient calculation time to launch a calculation"
        else:
            if (
                not request.user.is_PI
                and request.user.group == None
                and not request.user.is_superuser
            ):
                return "You have no computing resource"

            if not settings.ALLOW_LOCAL_CALC:
                return "Local calculations are disabled"

        is_local = True

    orders = []

    def get_default_name():
        return step.name + " Result"

    if "calc_name" in request.POST.keys():
        name = clean(request.POST["calc_name"])

        if name.strip() == "" and step.creates_ensemble:
            name = get_default_name()
    else:
        name = get_default_name()

    if "calc_mol_name" in request.POST.keys():
        mol_name = clean(request.POST["calc_mol_name"])
    else:
        mol_name = ""

    if len(name) > 100:
        return "The chosen ensemble name is too long"

    if len(mol_name) > 100:
        return "The chosen molecule name is too long"

    if "starting_ensemble" in request.POST:
        start_id = clean(request.POST["starting_ensemble"])
        try:
            start_e = Ensemble.objects.get(pk=start_id)
        except Ensemble.DoesNotExist:
            return "No starting ensemble found"

        start_author = start_e.parent_molecule.project.author
        if not can_view_ensemble(start_e, request.user):
            return "You do not have permission to access the starting calculation"

        if step.creates_ensemble:
            order_name = name
        else:
            order_name = start_e.name

        filter = None
        if "starting_structs" in request.POST:
            structs_str = clean(request.POST["starting_structs"])
            structs_nums = [int(i) for i in structs_str.split(",")]

            avail_nums = [i["number"] for i in start_e.structure_set.values("number")]

            for s_num in structs_nums:
                if s_num not in avail_nums:
                    return "Invalid starting structures"

            filter = Filter.objects.create(type="By Number", value=structs_str)
        elif "calc_filter" in request.POST.keys():
            filter_type = clean(request.POST["calc_filter"])
            if filter_type == "None":
                pass
            elif (
                filter_type == "By Relative Energy"
                or filter_type == "By Boltzmann Weight"
            ):
                if "filter_value" in request.POST.keys():
                    try:
                        filter_value = float(clean(request.POST["filter_value"]))
                    except ValueError:
                        return "Invalid filter value"
                else:
                    return "No filter value"

                if "filter_parameters" in request.POST.keys():
                    try:
                        filter_parameters_id = clean(request.POST["filter_parameters"])
                    except ValueError:
                        return "Invalid filter parameters"

                    try:
                        filter_parameters = Parameters.objects.get(
                            pk=filter_parameters_id
                        )
                    except Parameters.DoesNotExist:
                        return "Invalid filter parameters"

                    if not can_view_parameters(filter_parameters, request.user):
                        return "Invalid filter parameters"

                    if not verify:
                        filter = Filter.objects.create(
                            type=filter_type,
                            parameters=filter_parameters,
                            value=filter_value,
                        )
                else:
                    return "No filter parameters"
            else:
                return "Invalid filter type"
        if not verify:
            params = Parameters.objects.create(**_params)

            obj = CalculationOrder.objects.create(
                name=order_name,
                date=timezone.now(),
                parameters=params,
                author=request.user,
                resource_provider=request.user.resource_provider,
                step=step,
                project=project_obj,
                ensemble=start_e,
            )

            if filter is not None:
                obj.filter = filter

            orders.append(obj)
    elif "starting_calc" in request.POST:
        if not "starting_frame" in request.POST:
            return "Missing starting frame number"

        c_id = clean(request.POST["starting_calc"])
        frame_num = int(clean(request.POST["starting_frame"]))

        try:
            start_c = Calculation.objects.get(pk=c_id)
        except Calculation.DoesNotExist:
            return "No starting ensemble found"
        if not can_view_calculation(start_c, request.user):
            return "You do not have permission to access the starting calculation"

        if step.creates_ensemble:
            order_name = name
        else:
            order_name = start_c.result_ensemble.name + f" - Frame {frame_num}"

        if not verify:
            params = Parameters.objects.create(**_params)

            obj = CalculationOrder.objects.create(
                name=order_name,
                date=timezone.now(),
                parameters=params,
                author=request.user,
                resource_provider=request.user.resource_provider,
                step=step,
                project=project_obj,
                start_calc=start_c,
                start_calc_frame=frame_num,
            )
            orders.append(obj)
    else:
        combine = ""
        if "calc_combine_files" in request.POST:
            combine = clean(request.POST["calc_combine_files"])

        parse_filenames = ""
        if (
            "calc_parse_filenames" in request.POST
            and clean(request.POST["calc_parse_filenames"]) == "on"
        ):
            parse_filenames = clean(request.POST["calc_parse_filenames"])
        else:
            if mol_name == "":
                return "Missing molecule name"

        if (
            len(request.FILES) > 0
        ):  # Can't really verify file uploads before actually processing the files
            # Just check that the charge+multiplicity combination is possible

            uploaded_files = {}

            for ind, ff in enumerate(request.FILES.getlist("file_structure")):
                ss = handle_file_upload(ff, is_local)
                if isinstance(ss, str):
                    return ss

                struct, filename = ss

                electrons = 0
                for line in struct.xyz_structure.split("\n")[2:]:
                    if line.strip() == "":
                        continue
                    el = line.split()[0]
                    electrons += ATOMIC_NUMBER[el]

                _charge = _params["charge"]
                _multiplicity = _params["multiplicity"]

                if parse_filenames == "on":
                    pc, pm = ccinput.utilities.get_charge_mult_from_name(filename)
                    if pc != 0:
                        _charge = pc
                    if pm != 1:
                        _multiplicity = pm

                _params["charge"] = _charge
                _params["multiplicity"] = _multiplicity

                electrons -= _charge
                odd_e = electrons % 2
                odd_m = _multiplicity % 2

                if odd_e == odd_m:
                    return "Impossible charge/multiplicity combination"

                sparams = struct.properties.first().parameters
                sparams.charge = _charge
                sparams.multiplicity = _multiplicity
                sparams.save()
                uploaded_files[filename] = struct

            if not verify:
                # Process the files
                if len(uploaded_files) > 1:
                    if combine == "on" and parse_filenames != "on":
                        mol = Molecule.objects.create(
                            name=mol_name, project=project_obj
                        )
                        e = Ensemble.objects.create(
                            name="File Upload", parent_molecule=mol
                        )

                        params = Parameters.objects.create(**_params)

                        for ind, (filename, struct) in enumerate(
                            uploaded_files.items()
                        ):
                            """
                            if ind == 0:
                                # fing = gen_fingerprint(struct)
                                # InChI fingerprints are disabled for now
                                fing = ""
                                mol.inchi = fing
                                mol.save()
                            """

                            struct.number = ind + 1
                            struct.parent_ensemble = e
                            struct.save()

                        obj = CalculationOrder.objects.create(
                            name=name,
                            date=timezone.now(),
                            parameters=params,
                            author=request.user,
                            resource_provider=request.user.resource_provider,
                            step=step,
                            project=project_obj,
                            ensemble=e,
                        )
                        orders.append(obj)
                    elif combine != "on" and parse_filenames == "on":
                        unique_molecules = {}
                        unique_params = {}

                        for ind, (filename, struct) in enumerate(
                            uploaded_files.items()
                        ):
                            _mol_name, num = process_filename(filename)

                            struct.number = num
                            struct.save()
                            if _mol_name in unique_molecules:
                                unique_molecules[_mol_name].append(struct)
                            else:
                                unique_molecules[_mol_name] = [struct]

                                # Since the charge/multiplicity keywords are considered when detecting molecules,
                                # all the structures of a given molecule must necessarily have the same charge/multiplicity
                                __params = _params.copy()
                                __params[
                                    "charge"
                                ] = struct.properties.first().parameters.charge
                                __params[
                                    "multiplicity"
                                ] = struct.properties.first().parameters.multiplicity
                                unique_params[_mol_name] = Parameters.objects.create(
                                    **__params
                                )

                        for mol_name, arr_structs in unique_molecules.items():
                            used_numbers = []
                            # fing = gen_fingerprint(arr_structs[0])
                            fing = ""
                            mol = Molecule.objects.create(
                                name=mol_name, inchi=fing, project=project_obj
                            )
                            mol.save()

                            e = Ensemble.objects.create(
                                name="File Upload", parent_molecule=mol
                            )
                            for struct in arr_structs:
                                if struct.number == 0:
                                    num = 1
                                    while num in used_numbers:
                                        num += 1
                                    struct.number = num
                                    used_numbers.append(num)
                                else:
                                    used_numbers.append(struct.number)

                                struct.parent_ensemble = e
                                struct.save()
                            obj = CalculationOrder.objects.create(
                                name=name,
                                date=timezone.now(),
                                parameters=unique_params[_mol_name],
                                author=request.user,
                                resource_provider=request.user.resource_provider,
                                step=step,
                                project=project_obj,
                                ensemble=e,
                            )

                            orders.append(obj)
                    elif combine == "on" and parse_filenames == "on":
                        all_filenames = list(uploaded_files.keys())
                        filename = all_filenames.pop(0)
                        struct = uploaded_files[filename]
                        _mol_name, num = process_filename(filename)

                        # fing = gen_fingerprint(struct)
                        fing = ""

                        mol = Molecule.objects.create(
                            name=_mol_name, project=project_obj, inchi=fing
                        )
                        e = Ensemble.objects.create(
                            name="File Upload", parent_molecule=mol
                        )
                        struct.number = 1
                        struct.parent_ensemble = e
                        struct.save()

                        charge = struct.properties.first().parameters.charge
                        multiplicity = struct.properties.first().parameters.multiplicity

                        # Verify that all the files have the same charge/multiplicity specifications
                        for other_filename, other_struct in uploaded_files.items():
                            c = other_struct.properties.first().parameters.charge
                            m = other_struct.properties.first().parameters.multiplicity
                            if c != charge:
                                return f"Cannot combine files with different charge specifications ({filename}: charge={charge}, {other_filename}: charge={c})"
                            if m != multiplicity:
                                return f"Cannot combine files with different multiplicity specifications ({filename}: multiplicity={mult}, {other_filename}: multiplicity={m})"
                        # Create the Parameters object for all the inputs
                        __params = _params.copy()
                        __params["charge"] = charge
                        __params["multiplicity"] = multiplicity
                        params = Parameters.objects.create(**__params)

                        for ind, filename in enumerate(all_filenames):
                            struct = uploaded_files[filename]
                            struct.number = ind + 2
                            struct.parent_ensemble = e
                            struct.save()

                        obj = CalculationOrder.objects.create(
                            name=name,
                            date=timezone.now(),
                            parameters=params,
                            author=request.user,
                            resource_provider=request.user.resource_provider,
                            step=step,
                            project=project_obj,
                            ensemble=e,
                        )
                        orders.append(obj)
                    else:
                        unique_molecules = {}
                        for ind, (filename, struct) in enumerate(
                            uploaded_files.items()
                        ):
                            # fing = gen_fingerprint(struct)
                            fing = str(random.random())
                            if fing in unique_molecules.keys():
                                unique_molecules[fing].append(struct)
                            else:
                                unique_molecules[fing] = [struct]

                        params = Parameters.objects.create(**_params)

                        for ind, (fing, arr_struct) in enumerate(
                            unique_molecules.items()
                        ):
                            if len(unique_molecules.keys()) > 1:
                                mol = Molecule.objects.create(
                                    name=f"{mol_name} set {ind + 1}",
                                    inchi=fing,
                                    project=project_obj,
                                )
                            else:
                                mol = Molecule.objects.create(
                                    name=mol_name, inchi=fing, project=project_obj
                                )
                            e = Ensemble.objects.create(
                                name="File Upload", parent_molecule=mol
                            )

                            for s_num, struct in enumerate(arr_struct):
                                struct.parent_ensemble = e
                                struct.number = s_num + 1
                                struct.save()

                            obj = CalculationOrder.objects.create(
                                name=name,
                                date=timezone.now(),
                                parameters=params,
                                author=request.user,
                                resource_provider=request.user.resource_provider,
                                step=step,
                                project=project_obj,
                                ensemble=e,
                            )
                            orders.append(obj)
                elif len(uploaded_files) == 1:
                    filename, struct = list(uploaded_files.items())[0]

                    params = Parameters.objects.create(**_params)

                    num = 1
                    if parse_filenames == "on":
                        _mol_name, num = process_filename(filename)  # Disable mol_name
                    else:
                        _mol_name = mol_name

                    obj = CalculationOrder.objects.create(
                        name=name,
                        date=timezone.now(),
                        parameters=params,
                        author=request.user,
                        resource_provider=request.user.resource_provider,
                        step=step,
                        project=project_obj,
                    )

                    # fing = gen_fingerprint(struct)
                    fing = ""
                    mol = Molecule.objects.create(
                        name=_mol_name, inchi=fing, project=project_obj
                    )
                    mol.save()

                    e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
                    struct.parent_ensemble = e
                    struct.number = num
                    struct.save()

                    obj.ensemble = e
                    obj.save()
                    orders.append(obj)
        else:  # No file upload
            if "structure" in request.POST.keys():
                mol = clean(request.POST["structure"])
                xyz = generate_xyz_structure(True, mol, "mol")
                if len(xyz) == 0:
                    return "Could not convert the input drawing to XYZ"

                if (
                    is_local
                    and xyz.strip().count("\n") - 2 > settings.LOCAL_MAX_ATOMS
                    and settings.LOCAL_MAX_ATOMS != -1
                ):
                    return f"Input structures are limited to at most {settings.LOCAL_MAX_ATOMS} atoms"

                if not verify:
                    obj = CalculationOrder.objects.create(
                        name=name,
                        date=timezone.now(),
                        parameters=Parameters.objects.create(**_params),
                        author=request.user,
                        resource_provider=request.user.resource_provider,
                        step=step,
                        project=project_obj,
                    )
                    mol_obj = Molecule.objects.create(
                        name=mol_name, project=project_obj
                    )
                    e = Ensemble.objects.create(
                        name="Drawn Structure", parent_molecule=mol_obj
                    )
                    obj.ensemble = e
                    obj.save()

                    s = Structure.objects.create(parent_ensemble=e, number=1)
                    params = Parameters.objects.create(
                        software="Open Babel",
                        method="Forcefield",
                        basis_set="",
                        solvation_model="",
                        charge=_params["charge"],
                        multiplicity=_params["multiplicity"],
                    )
                    p = Property.objects.create(
                        parent_structure=s, parameters=params, geom=True
                    )
                    p.save()
                    params.save()

                    s.xyz_structure = xyz
                    s.save()
                    orders.append(obj)
            else:
                return "No input structure"

    if step.name == "Minimum Energy Path":
        if verify:
            if "num_aux_files" not in request.POST.keys():
                return "No valid auxiliary structure"
            try:
                num_aux_files = int(clean(request.POST["num_aux_files"]))
            except ValueError:
                return "No valid auxiliary structure"
            if num_aux_files == 0:
                if "aux_struct" not in request.POST.keys():
                    return "No valid auxiliary structure"
                try:
                    aux_struct = Structure.objects.get(
                        pk=clean(request.POST["aux_struct"])
                    )
                except Structure.DoesNotExist:
                    return "No valid auxiliary structure"
                if not can_view_structure(aux_struct, request.user):
                    return "No valid auxiliary structure"

            elif num_aux_files > 1:
                return "Only one auxiliary structure can be used"
        else:
            if len(orders) != 1:
                return "Only one initial structure can be used"
            if len(request.FILES.getlist("aux_file_structure")) == 1:
                if not verify:
                    _aux_struct = handle_file_upload(
                        request.FILES.getlist("aux_file_structure")[0], is_local
                    )
                    if isinstance(_aux_struct, str):
                        return _aux_struct
                    aux_struct = _aux_struct[0]
            else:
                if "aux_struct" not in request.POST.keys():
                    return "No valid auxiliary structure"
                try:
                    aux_struct = Structure.objects.get(
                        pk=clean(request.POST["aux_struct"])
                    )
                except Structure.DoesNotExist:
                    return "No valid auxiliary structure"
                if not can_view_structure(aux_struct, request.user):
                    return "No valid auxiliary structure"

            aux_struct.save()  # to remove, not useful
            orders[0].aux_structure = aux_struct

    TYPE_LENGTH = {"Distance": 2, "Angle": 3, "Dihedral": 4}
    constraints = ""

    if (
        step.name in ["Constrained Optimisation", "Constrained Conformational Search"]
        and "constraint_num" in request.POST.keys()
    ):
        for ind in range(1, int(request.POST["constraint_num"]) + 1):
            try:
                mode = clean(request.POST[f"constraint_mode_{ind}"])
            except MultiValueDictKeyError:
                pass
            else:
                _type = clean(request.POST[f"constraint_type_{ind}"])
                ids = []
                for i in range(1, TYPE_LENGTH[_type] + 1):
                    id_txt = clean(request.POST[f"calc_constraint_{ind}_{i}"])
                    if id_txt != "":
                        try:
                            id = int(id_txt)
                        except ValueError:
                            return f"Invalid constraint: {id_txt}"
                        ids.append(id)

                if len(ids) == 0:
                    return "Invalid or missing constraints"

                ids = "_".join([str(i) for i in ids])
                if mode == "Freeze":
                    constraints += f"{mode}/{ids};"
                elif mode == "Scan":
                    if not verify:
                        obj.has_scan = True
                        obj.save()

                    if _params["software"] != "Gaussian":
                        try:
                            begin = float(clean(request.POST[f"calc_scan_{ind}_1"]))
                        except ValueError:
                            return "Invalid scan parameters"
                    else:
                        begin = 42.0
                    try:
                        end = float(clean(request.POST[f"calc_scan_{ind}_2"]))
                        steps = int(clean(request.POST[f"calc_scan_{ind}_3"]))
                    except ValueError:
                        return "Invalid scan parameters"
                    constraints += f"{mode}_{begin}_{end}_{steps}/{ids};"
                else:
                    return "Invalid constrained optimisation"

        if constraints == "":
            return "No constraint specified for constrained calculation"

    if verify:
        return

    for o in orders:
        o.constraints = constraints

        if resource != "Local":
            o.resource = access

        o.save()

    if "test" in request.POST.keys():
        return redirect("/calculations/")

    record_event_analytics(request, "launch_calc")

    if settings.IS_CLOUD:
        for o in orders:
            send_gcloud_task("/cloud_order/", str(o.id), compute=False)
    else:
        for o in orders:
            dispatcher.delay(str(o.id))

    return redirect("/calculations/")


def can_view_project(proj, user):
    if proj.author == user:
        return True
    else:
        if not user_intersection(proj.author, user):
            return False
        if proj.private and not (user.is_PI or user.professor_of.count()):
            return False
        return True


def can_view_molecule(mol, user):
    return can_view_project(mol.project, user)


def can_view_ensemble(e, user):
    return can_view_molecule(e.parent_molecule, user)


def can_view_structure(s, user):
    return can_view_ensemble(s.parent_ensemble, user)


def can_view_parameters(p, user):
    prop = p.property_set.first()

    if prop is not None:
        return can_view_structure(prop.parent_structure, user)

    c = p.calculation_set.first()

    if c is not None:
        return can_view_calculation(c, user)

    pr = p.preset_set.first()

    if pr is not None:
        return can_view_preset(pr, user)

    raise Exception(
        f"Could not evaluate the visibility of parameters {p.id} for user {user.id}"
    )


def can_view_preset(p, user):
    return user_intersection(p.author, user)


def can_view_order(order, user):
    if order.author == user:
        return True
    elif user_intersection(order.author, user):
        if proj.private and not (user.is_PI or user.professor_of):
            return False
        return True
    return False


def can_view_calculation(calc, user):
    return can_view_order(calc.order, user)


def user_intersection(user1, user2):
    """
    user1 is the target
    user2 is the user trying to access
    """
    if user1 == user2:
        return True

    if user1.group is not None:
        if user2 in user1.group.members.all():
            return True
        if user2 == user1.group.PI:
            return True

    if user1.PI_of != None:
        for group in user1.PI_of.all():
            if user2 in group.members.all():
                return True

    if user1.in_class is not None:
        if user1.in_class.professor == user2:
            return True

    return False


@login_required
def project_list(request):
    if request.method == "POST":
        target_user_id = clean(request.POST["user_id"])
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return HttpResponse(status=403)

        if not user_intersection(target_user, request.user):
            return HttpResponse(status=403)

        return render(
            request,
            "frontend/dynamic/project_list.html",
            {
                "target_use": target_user,
            },
        )

    else:
        return HttpResponse(status=403)


@login_required
def delete_project(request):
    if request.method == "POST":
        if "id" in request.POST.keys():
            proj_id = clean(request.POST["id"])
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Project.objects.get(pk=proj_id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.author != request.user:
            return HttpResponse(status=403)

        if settings.IS_CLOUD:
            send_gcloud_task("/cloud_action/", f"del_project;{proj_id}", compute=False)
        else:
            del_project.delay(proj_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)


@login_required
def delete_order(request):
    if request.method == "POST":
        if "id" in request.POST.keys():
            order_id = clean(request.POST["id"])
        else:
            return HttpResponse(status=403)

        try:
            to_delete = CalculationOrder.objects.get(pk=order_id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.author != request.user:
            return HttpResponse(status=403)

        if settings.IS_CLOUD:
            send_gcloud_task("/cloud_action/", f"del_order;{order_id}", compute=False)
        else:
            del_order.delay(order_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)


@login_required
def delete_folder(request):
    if request.method == "POST":
        if "id" in request.POST.keys():
            folder_id = clean(request.POST["id"])
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Folder.objects.get(pk=folder_id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.project.author != request.user:
            return HttpResponse(status=403)

        if (
            to_delete.ensemble_set.count() == 0 and to_delete.folder_set.count() == 0
        ):  ## To modify?
            to_delete.delete()
            return HttpResponse(status=204)

        return HttpResponse(status=400)
    else:
        return HttpResponse(status=403)


@login_required
def delete_molecule(request):
    if request.method == "POST":
        if "id" in request.POST.keys():
            mol_id = clean(request.POST["id"])
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Molecule.objects.get(pk=mol_id)
        except Molecule.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.project.author != request.user:
            return HttpResponse(status=403)

        if settings.IS_CLOUD:
            send_gcloud_task("/cloud_action/", f"del_molecule;{mol_id}", compute=False)
        else:
            del_molecule.delay(mol_id)

        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)


@login_required
def delete_ensemble(request):
    if request.method == "POST":
        if "id" in request.POST.keys():
            ensemble_id = clean(request.POST["id"])
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Ensemble.objects.get(pk=ensemble_id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=404)

        if to_delete.parent_molecule.project.author != request.user:
            return HttpResponse(status=403)

        if settings.IS_CLOUD:
            send_gcloud_task(
                "/cloud_action/", f"del_ensemble;{ensemble_id}", compute=False
            )
        else:
            del_ensemble.delay(ensemble_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)


@login_required
def add_clusteraccess(request):
    if request.method == "POST":
        address = clean(request.POST["cluster_address"])
        username = clean(request.POST["cluster_username"])
        pal = int(clean(request.POST["cluster_cores"]))
        memory = int(clean(request.POST["cluster_memory"]))
        password = clean(request.POST["cluster_password"])

        owner = request.user

        try:
            existing_access = owner.clusteraccess_owner.get(
                cluster_address=address, cluster_username=username, owner=owner
            )
        except ClusterAccess.DoesNotExist:
            pass
        else:
            return HttpResponse(status=403)

        access = ClusterAccess.objects.create(
            cluster_address=address,
            cluster_username=username,
            owner=owner,
            pal=pal,
            memory=memory,
        )
        access.save()
        owner.save()

        key = rsa.generate_private_key(
            backend=default_backend(), public_exponent=65537, key_size=2048
        )

        public_key = key.public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        )

        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(
                bytes(password, "UTF-8")
            ),
        )
        with open(os.path.join(CALCUS_KEY_HOME, str(access.id)), "wb") as out:
            out.write(pem)

        with open(os.path.join(CALCUS_KEY_HOME, str(access.id) + ".pub"), "wb") as out:
            out.write(public_key)
            out.write(b" %b@CalcUS" % bytes(owner.name, "utf-8"))

        return HttpResponse(public_key.decode("utf-8"))
    else:
        return HttpResponse(status=403)


@login_required
def connect_access(request):
    pk = clean(request.POST["access_id"])
    password = clean(request.POST["password"])

    try:
        access = ClusterAccess.objects.get(pk=pk)
    except ClusterAccess.DoesNotExist:
        return HttpResponse(status=403)

    if access.owner != request.user:
        return HttpResponse(status=403)

    access.status = "Pending"
    access.save()

    send_cluster_command(f"connect\n{pk}\n{password}\n")

    return HttpResponse("")


@login_required
def disconnect_access(request):
    pk = clean(request.POST["access_id"])

    access = ClusterAccess.objects.get(pk=pk)

    if access.owner != request.user:
        return HttpResponse(status=403)

    send_cluster_command(f"disconnect\n{pk}\n")

    return HttpResponse("")


@login_required
def status_access(request):
    pk = clean(request.POST["access_id"])

    access = ClusterAccess.objects.get(pk=pk)

    if access.owner != request.user and not request.user.is_superuser:
        return HttpResponse(status=403)

    dt = timezone.now() - access.last_connected
    if dt.total_seconds() < 600:
        return HttpResponse(f"Connected as of {int(dt.total_seconds())} seconds ago")
    else:
        return HttpResponse("Disconnected")


@login_required
def get_command_status(request):
    pk = request.POST["access_id"]

    try:
        access = ClusterAccess.objects.get(pk=pk)
    except ClusterAccess.DoesNotExist:
        return HttpResponse(status=403)

    if access.owner != request.user:
        return HttpResponse(status=403)

    return HttpResponse(access.status)


@login_required
def delete_access(request, pk):
    try:
        access = ClusterAccess.objects.get(pk=pk)
    except ClusterAccess.DoesNotExist:
        return HttpResponse(status=403)

    if access.owner != request.user:
        return HttpResponse(status=403)

    access.delete()

    send_cluster_command(f"delete_access\n{pk}\n")

    return HttpResponseRedirect("/profile")


@login_required
def load_pub_key(request, pk):
    try:
        access = ClusterAccess.objects.get(pk=pk)
    except ClusterAccess.DoesNotExist:
        return HttpResponse(status=403)

    if access.owner != request.user:
        return HttpResponse(status=403)

    key_path = os.path.join(CALCUS_KEY_HOME, f"{access.id}.pub")

    if not os.path.isfile(key_path):
        return HttpResponse(status=404)

    with open(key_path) as f:
        pub_key = f.readlines()[0]

    return HttpResponse(pub_key)


@login_required
def load_password(request):
    if request.user.is_trial:
        return HttpResponse(status=403)
    if not request.user.is_temporary:
        return HttpResponse(status=403)

    if request.user.email is None or request.user.email.find("@calcus.cloud") == -1:
        return HttpResponse(status=403)

    if request.user.random_password == "":
        logger.warning(f"Temporary user {request.user.id} has a blank random password")
        return HttpResponse(status=403)

    return HttpResponse(request.user.random_password)


@login_required
def update_access(request):
    vals = {}
    for param in ["pal", "mem"]:
        if param not in request.POST.keys():
            return HttpResponse(status=400)

        try:
            vals[param] = int(clean(request.POST[param]))
        except ValueError:
            return HttpResponse("Invalid value", status=400)

    if "access_id" not in request.POST:
        return HttpResponse(status=400)

    try:
        vals["access_id"] = clean(request.POST["access_id"])
    except ValueError:
        return HttpResponse("Invalid value", status=400)

    try:
        access = ClusterAccess.objects.get(pk=vals["access_id"])
    except ClusterAccess.DoesNotExist:
        return HttpResponse("No such cluster access", status=404)

    if access.owner != request.user:
        return HttpResponse(
            "You do not have the permission to modify this cluster access", status=403
        )

    if vals["pal"] < 1:
        return HttpResponse("Invalid number of cores", status=400)

    if vals["mem"] < 1:
        return HttpResponse("Invalid amount of memory", status=400)

    msg = ""
    curr_mem = access.memory
    curr_pal = access.pal

    if vals["pal"] != curr_pal:
        access.pal = vals["pal"]
        msg += f"Number of cores set to {vals['pal']}\n"

    if vals["mem"] != curr_mem:
        access.memory = vals["mem"]
        msg += f"Amount of memory set to {vals['mem']} MB\n"

    access.save()
    if msg == "":
        msg = "No change detected"

    return HttpResponse(msg)


@login_required
@superuser_required
def server_summary(request):
    users = User.objects.all()
    groups = ResearchGroup.objects.all()
    accesses = ClusterAccess.objects.all()
    return render(
        request,
        "frontend/server_summary.html",
        {
            "users": users,
            "groups": groups,
            "accesses": accesses,
        },
    )


@login_required
def create_group(request):
    if request.method == "POST":
        if not request.user.is_subscriber:
            return HttpResponse(
                "You need a subscription in order to create groups or classes",
                status=403,
            )

        try:
            group_name = clean(request.POST["group_name"])
        except KeyError:
            return HttpResponse("No group name given", status=400)

        if len(group_name) < 4:
            return HttpResponse("Group name too short", status=400)

        if len(group_name) > 64:
            return HttpResponse("Group name too long", status=400)

        try:
            type = clean(request.POST["type"])
        except KeyError:
            return HttpResponse("No group type given", status=400)

        if type == "group":
            if request.user.is_PI:
                return HttpResponse("You already have a research group", status=400)
            group = ResearchGroup.objects.create(name=group_name, PI=request.user)
        elif type == "class":
            cls = ClassGroup.objects.create(name=group_name, professor=request.user)
            cls.generate_code()
        else:
            return HttpResponse("Unknown group type", status=400)

        return HttpResponse(status=200)

    return HttpResponse(status=403)


@login_required
def dissolve_group(request):
    if request.method == "POST":
        try:
            group_id = clean(request.POST["group_id"])
        except KeyError:
            return HttpResponse("No group ID given", status=400)

        try:
            type = clean(request.POST["type"])
        except KeyError:
            return HttpResponse("No type given", status=400)

        if type == "group":
            try:
                group = ResearchGroup.objects.get(pk=group_id)
            except ResearchGroup.DoesNotExist:
                return HttpResponse("No research group with this ID", status=404)

            if not request.user.is_PI:
                return HttpResponse("No research group to dissolve", status=400)

            if group.PI != request.user:
                return HttpResponse(
                    "You do not have permission to dissolve this group", status=403
                )

            group.delete()
        elif type == "class":
            try:
                cls = ClassGroup.objects.get(pk=group_id)
            except ClassGroup.DoesNotExist:
                return HttpResponse("No class with this ID", status=404)

            if cls.professor != request.user:
                return HttpResponse(
                    "You do not have permission to dissolve this class", status=403
                )

            cls.delete()  # or make inactive?
        else:
            return HttpResponse("Invalid type given", status=400)

        return HttpResponse(status=200)

    return HttpResponse(status=403)


@login_required
def add_user(request):
    if request.method == "POST":
        if not request.user.is_PI:
            return HttpResponse(status=403)

        user_id = clean(request.POST["user_id"])
        group_id = clean(request.POST["group_id"])

        try:
            group = ResearchGroup.objects.get(pk=group_id)
        except ResearchGroup.DoesNotExist:
            return HttpResponse(status=403)

        if group.PI != request.user:
            return HttpResponse(status=403)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse(status=403)

        if user == request.user:
            return HttpResponse(status=403)

        group.members.add(user)

        return HttpResponse(status=200)

    return HttpResponse(status=403)


@login_required
def remove_user(request):
    if request.method == "POST":
        try:
            type = clean(request.POST["type"])
        except KeyError:
            return HttpResponse("No group type given", status=400)

        member_id = clean(request.POST["member_id"])
        group_id = clean(request.POST["group_id"])

        try:
            member = User.objects.get(pk=member_id)
        except User.DoesNotExist:
            return HttpResponse(status=403)

        if member == request.user:
            return HttpResponse(status=403)

        if type == "group":
            try:
                group = ResearchGroup.objects.get(pk=group_id)
            except ResearchGroup.DoesNotExist:
                return HttpResponse(status=403)

            if member not in group.members.all():
                return HttpResponse(status=403)

            if group.PI != request.user:
                return HttpResponse(status=403)

            group.members.remove(member)
        elif type == "class":
            try:
                cls = ClassGroup.objects.get(pk=group_id)
            except ClassGroup.DoesNotExist:
                return HttpResponse(status=403)

            if member not in cls.members.all():
                return HttpResponse(status=403)

            if cls.professor != request.user:
                return HttpResponse(status=403)

            cls.members.remove(member)
        else:
            return HttpResponse("Invalid group type given", status=400)

        return HttpResponse(status=200)

    return HttpResponse(status=403)


@login_required
def redeem_allocation(request):
    if request.method != "POST":
        return HttpResponse(status=400)

    if "code" not in request.POST or clean(request.POST["code"]).strip() == "":
        return HttpResponse("No code given", status=400)

    code = clean(request.POST["code"]).strip()

    try:
        alloc = ResourceAllocation.objects.get(code=code)
    except ResourceAllocation.DoesNotExist:
        return HttpResponse("Invalid code given", status=400)

    if not alloc.redeem(request.user):
        return HttpResponse("Code already redeemed", status=400)

    record_event_analytics(request, "allocation_redeemed")
    return HttpResponse("Resource redeemed!", status=200)


@login_required
def profile_groups(request):
    return render(
        request,
        "frontend/dynamic/profile_groups.html",
    )


@login_required
def profile_classes(request):
    return render(
        request,
        "frontend/dynamic/profile_classes.html",
    )


@login_required
def profile_allocation(request):
    return render(
        request,
        "frontend/dynamic/profile_allocation.html",
    )


@login_required
def conformer_table(request, pk):
    id = str(pk)
    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_ensemble(e, request.user):
        return HttpResponse(status=403)

    return render(
        request,
        "frontend/dynamic/conformer_table.html",
        {
            "ensemble": e,
        },
    )


@login_required
def conformer_table_post(request):
    if request.method == "POST":
        try:
            id = clean(request.POST["ensemble_id"])
            p_id = clean(request.POST["param_id"])
        except KeyError:
            return HttpResponse(status=204)

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if not can_view_ensemble(e, request.user):
            return HttpResponse(status=403)

        try:
            p = Parameters.objects.get(pk=p_id)
        except Parameters.DoesNotExist:
            return HttpResponse(status=403)

        full_summary, hashes = e.ensemble_summary

        if p.md5 in full_summary.keys():
            summary = full_summary[p.md5]

            fms = request.user.pref_units_format_string

            rel_energies = [
                fms.format(i)
                for i in np.array(summary[5]) * request.user.unit_conversion_factor
            ]
            structures = [e.structure_set.get(pk=i) for i in summary[4]]
            data = zip(structures, summary[2], rel_energies, summary[6])
            data = sorted(data, key=lambda i: i[0].number)

        else:
            blank = ["-" for i in range(e.structure_set.count())]
            structures = e.structure_set.all()
            data = zip(structures, blank, blank, blank)
            data = sorted(data, key=lambda i: i[0].number)
        return render(
            request,
            "frontend/dynamic/conformer_table.html",
            {
                "data": data,
            },
        )

    else:
        return HttpResponse(status=403)


@login_required
def uvvis(request, pk):
    try:
        prop = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_structure(prop.parent_structure, request.user):
        return HttpResponse(status=404)

    response = HttpResponse(prop.uvvis, content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f"attachment; filename=uvvis_{prop.parent_structure.id}.csv"
    return response


@login_required
def get_calc_data(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    return format_frames(calc, request.user)


def format_frames(calc, user):
    if calc.status == 1:
        analyse_opt(calc.id)

    multi_xyz = ""
    scan_energy = "Frame,Relative Energy\n"
    RMSD = "Frame,RMSD\n"

    scan_frames = []
    scan_energies = []

    for f in (
        calc.calculationframe_set.values(
            "xyz_structure", "number", "RMSD", "converged", "energy"
        )
        .order_by("number")
        .all()
    ):
        multi_xyz += f["xyz_structure"]
        RMSD += f"{f['number']},{f['RMSD']}\n"
        if f["converged"] == True:
            scan_frames.append(f["number"])
            scan_energies.append(f["energy"])

    if len(multi_xyz) > 0:
        if len(scan_energies) > 0:
            scan_min = min(scan_energies)
            for n, E in zip(scan_frames, scan_energies):
                scan_energy += f"{n},{(E - scan_min) * user.unit_conversion_factor}\n"
        return HttpResponse(multi_xyz + ";" + RMSD + ";" + scan_energy)
    else:
        return HttpResponse(status=204)


@login_required
@throttle(zone="load_remote_log")
def get_calc_data_remote(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    if calc.order.author != request.user:
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    if calc.parameters.software == "Gaussian":
        logname = "calc.log"
    else:
        logname = "calc.out"

    try:
        os.remove(os.path.join(CALCUS_SCR_HOME, str(calc.id), logname))
    except OSError:
        pass

    send_cluster_command(f"load_log\n{calc.id}\n{calc.order.resource.id}\n")

    last_size = 0
    # We need to wait until the file download is complete, although we cannot directly communicate with the cluster daemon
    for i in range(20):
        if os.path.isfile(os.path.join(CALCUS_SCR_HOME, str(calc.id), logname)):
            fsize = os.path.getsize(
                os.path.join(CALCUS_SCR_HOME, str(calc.id), logname)
            )
            if fsize == last_size:
                break
            last_size = fsize
        time.sleep(0.5)

    if not os.path.isfile(os.path.join(CALCUS_SCR_HOME, str(calc.id), logname)):
        return HttpResponse(status=404)

    load_output_files(calc)

    return format_frames(calc, request.user)


def get_calc_frame(request, cid, fid):
    try:
        calc = Calculation.objects.get(pk=cid)
    except Calculation.DoesNotExist:
        return redirect("/home/")

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    xyz = calc.calculationframe_set.get(number=fid).xyz_structure
    return HttpResponse(xyz)


@login_required
def get_cube(request):
    if request.method == "POST":
        id = clean(request.POST["id"])
        orb = int(clean(request.POST["orb"]))

        try:
            prop = Property.objects.get(pk=id)
        except Property.DoesNotExist:
            return HttpResponse(status=404)

        if not can_view_structure(prop.parent_structure, request.user):
            return HttpResponse(status=404)

        if len(prop.mo) == 0:
            return HttpResponse(status=204)

        cubes = json.loads(prop.mo)

        if orb == 0:
            cube_mo = "HOMO"
        elif orb == 1:
            cube_mo = "LUMO"
        elif orb == 2:
            cube_mo = "LUMOA"
        elif orb == 3:
            cube_mo = "LUMOB"
        else:
            return HttpResponse(status=204)

        if cube_mo in cubes:
            return HttpResponse(cubes[cube_mo])

    return HttpResponse(status=204)


@login_required
def nmr(request):
    if request.method != "POST":
        return HttpResponse(status=404)

    if "id" in request.POST.keys():
        try:
            e = Ensemble.objects.get(pk=clean(request.POST["id"]))
        except Ensemble.DoesNotExist:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)
    if "p_id" in request.POST.keys():
        try:
            params = Parameters.objects.get(pk=clean(request.POST["p_id"]))
        except Parameters.DoesNotExist:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)

    if "nucleus" in request.POST.keys():
        nucleus = clean(request.POST["nucleus"])
    else:
        return HttpResponse(status=404)

    if not can_view_ensemble(e, request.user):
        return HttpResponse(status=403)

    if not e.has_nmr(params):
        return HttpResponse(status=204)

    shifts = e.weighted_nmr_shifts(params)

    if nucleus == "H":
        content = "Shift,Intensity\n-10,0\n0,0\n"
    else:
        content = "Shift,Intensity\n-200,0\n0,0\n"

    for shift in shifts:
        if shift[1] == nucleus:
            if len(shift) == 4:
                content += f"{-(shift[3] - 0.001)},{0}\n"
                content += f"{-shift[3]},{1}\n"
                content += f"{-(shift[3] + 0.001)},{0}\n"

    response = HttpResponse(content, content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f"attachment; filename=nmr_{clean_filename(e.name)}.csv"
    return response


@login_required
def ir_spectrum(request, pk):
    try:
        prop = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_structure(prop.parent_structure, request.user):
        return HttpResponse(status=404)

    if prop.ir_spectrum != "":
        response = HttpResponse(prop.ir_spectrum, content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f"attachment; filename=ir_{prop.parent_structure.id}.csv"
        return response
    else:
        return HttpResponse(status=204)


@login_required
def vib_table(request, pk):
    try:
        prop = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_structure(prop.parent_structure, request.user):
        return HttpResponse(status=404)

    response = ""
    for ind, vib in enumerate(prop.freq_list):
        response += f'<div class="column is-narrow"><a class="button" id="vib_mode_{ind}" onclick="animate_vib({ind});">{vib:.1f}</a></div>'

    return HttpResponse(response)


@login_required
def info_table(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    return render(
        request,
        "frontend/dynamic/info_table.html",
        {
            "calculation": calc,
        },
    )


@login_required
def next_step(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    return render(
        request,
        "frontend/dynamic/next_step.html",
        {
            "calculation": calc,
        },
    )


@login_required
def download_structures(request, ee):
    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_ensemble(e, request.user):
        return HttpResponse(status=404)

    name = f"{clean_filename(e.parent_molecule.name)}.{clean_filename(e.name)}"
    structs = ""
    for s in e.structure_set.all():
        if s.xyz_structure == "":
            structs += "1\nMissing Structure\nC 0 0 0"
            logger.warning(f"Missing structure! ({request.user.name}, {name})")
        structs += s.xyz_structure

    response = HttpResponse(structs)
    response["Content-Type"] = "text/plain"
    response["Content-Disposition"] = f"attachment; filename={name}.xyz"
    return response


@login_required
def download_structure(request, ee, num):
    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_ensemble(e, request.user):
        return HttpResponse(status=404)

    try:
        s = e.structure_set.get(number=num)
    except Structure.DoesNotExist:
        return HttpResponse(status=404)

    name = (
        f"{clean_filename(e.parent_molecule.name)}_{clean_filename(e.name)}_conf{num}"
    )

    response = HttpResponse(s.xyz_structure)
    response["Content-Type"] = "text/plain"
    response["Content-Disposition"] = f"attachment; filename={name}.xyz"
    return response


def get_mol_preview(request):
    if request.method == "POST":
        mol = clean(request.POST["mol"])
        ext = clean(request.POST["ext"])

        if ext == "xyz":
            return HttpResponse(mol)

        xyz = generate_xyz_structure(False, mol, ext)

        if xyz == ErrorCodes.UNIMPLEMENTED:
            return HttpResponse(status=204)

        return HttpResponse(xyz)


def gen_3D(request):
    if request.method == "POST":
        mol = clean(request.POST["mol"])
        xyz = generate_xyz_structure(True, mol, "mol")
        return HttpResponse(xyz)


@login_required
def update_name(request):
    if request.method == "POST":
        name = clean(request.POST["name"])
        if len(name) == 0:
            return HttpResponse("No name given", status=400)
        elif len(name) < 3:
            return HttpResponse("The name entered is unreasonably short", status=400)
        elif len(name) > 255:
            return HttpResponse("The name entered is unreasonably long", status=400)

        request.user.full_name = name
        request.user.save()
        return HttpResponse("Name updated")


@login_required
def rename_molecule(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            mol = Molecule.objects.get(pk=id)
        except Molecule.DoesNotExist:
            return HttpResponse(status=403)

        if mol.project.author != request.user:
            return HttpResponse(status=403)

        if "new_name" in request.POST.keys():
            name = clean(request.POST["new_name"])

        if name.strip() == "":
            name = "Nameless molecule"

        mol.name = name
        mol.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def rename_project(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            proj = Project.objects.get(pk=id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if proj.author != request.user:
            return HttpResponse(status=403)

        if "new_name" in request.POST.keys():
            name = clean(request.POST["new_name"])

        if name.strip() == "":
            name = "Nameless project"

        proj.name = name
        proj.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def toggle_private(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            proj = Project.objects.get(pk=id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if proj.author != request.user:
            return HttpResponse(status=403)

        if "val" in request.POST.keys():
            try:
                val = int(clean(request.POST["val"]))
            except ValueError:
                return HttpResponse(status=403)
        else:
            return HttpResponse(status=403)

        if val not in [0, 1]:
            return HttpResponse(status=403)

        proj.private = val
        proj.save()

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def toggle_flag(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if e.parent_molecule.project.author != request.user:
            return HttpResponse(status=403)

        if "val" in request.POST.keys():
            try:
                val = int(clean(request.POST["val"]))
            except ValueError:
                return HttpResponse(status=403)
        else:
            return HttpResponse(status=403)

        if val not in [0, 1]:
            return HttpResponse(status=403)

        e.flagged = val
        e.save()

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def rename_ensemble(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if e.parent_molecule.project.author != request.user:
            return HttpResponse(status=403)

        if "new_name" in request.POST.keys():
            name = clean(request.POST["new_name"])

        if name.strip() == "":
            name = "Nameless ensemble"

        e.name = name
        e.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def rename_folder(request):
    if request.method == "POST":
        id = clean(request.POST["id"])

        try:
            f = Folder.objects.get(pk=id)
        except Folder.DoesNotExist:
            return HttpResponse(status=403)

        if f.project.author != request.user:
            return HttpResponse(status=403)

        if "new_name" in request.POST.keys():
            name = clean(request.POST["new_name"])

        if name.strip() == "":
            return HttpResponse(status=403)

        f.name = name
        f.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@login_required
def get_structure(request):
    if request.method == "POST":
        try:
            id = clean(request.POST["id"])
        except ValueError:
            return HttpResponse(status=404)

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if not can_view_ensemble(e, request.user):
            return HttpResponse(status=403)

        structs = e.structure_set.all()

        if len(structs) == 0:
            return HttpResponse(status=204)

        if "num" in request.POST.keys():
            num = int(clean(request.POST["num"]))
            try:
                struct = structs.get(number=num)
            except Structure.DoesNotExist:
                inds = [i.number for i in structs]
                m = inds.index(min(inds))
                return HttpResponse(structs[m].xyz_structure)

            else:
                return HttpResponse(struct.xyz_structure)
        else:
            inds = [i.number for i in structs]
            m = inds.index(min(inds))
            return HttpResponse(structs[m].xyz_structure)


@login_required
def get_vib_animation(request):
    if request.method == "POST":
        if "id" not in request.POST:
            return HttpResponse(status=400)

        if "num" not in request.POST:
            return HttpResponse(status=400)

        try:
            id = clean(request.POST["id"])
        except ValueError:
            return HttpResponse(status=400)

        try:
            prop = Property.objects.get(pk=id)
        except Property.DoesNotExist:
            return HttpResponse(status=404)

        if not can_view_structure(prop.parent_structure, request.user):
            return HttpResponse(status=403)

        num = int(clean(request.POST["num"]))

        animation = prop.freq_animations[num]
        return HttpResponse(animation)


@login_required
def download_log(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    name = f"{clean_filename(calc.order.molecule_name)}_{clean_filename(calc.corresponding_ensemble.name)}"

    if len(calc.output_files) == 0:
        logger.warning(f"No log to download! (Calculation {pk})")
        return HttpResponse(status=404)

    data = json.loads(calc.output_files)
    if len(data) > 1:
        mem = BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zip:
            # Write the main file, then others with suffixes
            zip.writestr(name, data["calc"])

            for logname, log in data.items():
                if logname == "calc":
                    continue
                zip.write(log, f"{name}_{logname}")

        response = HttpResponse(mem.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{name}.zip"'
        return response
    else:
        response = HttpResponse(data["calc"], content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{name}.log"'
        return response


@login_required
def download_all_logs(request, pk):
    try:
        order = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_order(order, request.user):
        return HttpResponse(status=403)

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zip:
        for calc in order.calculation_set.all():
            if calc.status in [0, 1]:
                return HttpResponse(status=204)

            for logname, log in json.loads(calc.output_files).items():
                if logname == "calc":
                    _logname = ""
                else:
                    _logname = f"_{logname}"
                if calc.structure:
                    conf_num = calc.structure.number
                else:
                    conf_num = 1
                zip.writestr(
                    f"{clean_filename(order.molecule_name)}_{clean_filename(calc.corresponding_ensemble.name)}_{clean_filename(calc.step.short_name)}_conf{conf_num}.log",
                    log,
                )

    response = HttpResponse(mem.getvalue(), content_type="application/zip")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="{order.molecule_name}_order_{pk}.zip"'
    return response


@login_required
def log(request, pk):
    LOG_HTML = """
    <label class="label">{}</label>
    <textarea class="textarea" style="height: 300px;" readonly>
    {}
    </textarea>
    """

    response = ""

    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=403)

    load_output_files(calc)

    if len(calc.output_files) == 0:
        return HttpResponse(status=204)

    data = json.loads(calc.output_files)

    for log_name, log in data.items():
        response += LOG_HTML.format(log_name, log)

    return HttpResponse(response)


@login_required
def manage_access(request, pk):
    try:
        access = ClusterAccess.objects.get(pk=pk)
    except ClusterAccess.DoesNotExist:
        return HttpResponse(status=404)

    if access.owner != request.user:
        return HttpResponse(status=404)

    return render(
        request,
        "frontend/manage_access.html",
        {
            "access": access,
        },
    )


@login_required
def owned_accesses(request):
    return render(
        request,
        "frontend/dynamic/owned_accesses.html",
    )


@login_required
def profile(request):
    return render(
        request,
        "frontend/profile.html",
    )


@login_required
def update_preferences(request):
    if request.method == "POST":
        if "pref_units" not in request.POST.keys():
            return HttpResponse(status=204)

        if "default_gaussian" in request.POST.keys():
            default_gaussian = clean(request.POST["default_gaussian"]).replace("\n", "")
            request.user.default_gaussian = default_gaussian

        if "default_orca" in request.POST.keys():
            default_orca = clean(request.POST["default_orca"]).replace("\n", "")
            request.user.default_orca = default_orca

        units = clean(request.POST["pref_units"])

        try:
            unit_code = request.user.INV_UNITS[units]
        except KeyError:
            return HttpResponse(status=204)

        request.user.pref_units = unit_code
        request.user.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=404)


@login_required
def launch(request):
    params = {
        "procs": BasicStep.objects.all().order_by(Lower("name")),
        "packages": settings.PACKAGES,
    }

    if "ensemble" in request.POST.keys():
        try:
            e = Ensemble.objects.get(pk=clean(request.POST["ensemble"]))
        except Ensemble.DoesNotExist:
            return redirect("/home/")

        if not can_view_ensemble(e, request.user):
            return HttpResponse(status=403)

        o = False
        if e.result_of.first() is not None:
            o = e.result_of.first()
        elif e.calculationorder_set.first() is not None:  # e.g. SP on uploaded file
            o = e.calculationorder_set.first()

        if o and o.resource is not None:
            params["resource"] = o.resource.cluster_address

        params["ensemble"] = e
        if "structures" in request.POST.keys():
            s_str = clean(request.POST["structures"])
            s_nums = [int(i) for i in s_str.split(",")]

            try:
                struct = e.structure_set.get(number=s_nums[0])
            except Structure.DoesNotExist:
                return HttpResponse(status=404)

            avail_nums = [i["number"] for i in e.structure_set.values("number")]

            for s_num in s_nums:
                if s_num not in avail_nums:
                    return HttpResponse(status=404)

            init_params = struct.properties.all()[0].parameters

            params["structures"] = s_str
            params["structure"] = struct
            params["init_params_id"] = init_params.id
        else:
            init_params = e.structure_set.all()[0].properties.all()[0].parameters

            params["init_params_id"] = init_params.id
    elif "calc_id" in request.POST.keys():
        calc_id = clean(request.POST["calc_id"])

        if "frame_num" not in request.POST.keys():
            return HttpResponse(status=404)

        frame_num = int(clean(request.POST["frame_num"]))

        try:
            calc = Calculation.objects.get(pk=calc_id)
        except Calculation.DoesNotExist:
            return redirect("/home/")

        if not can_view_calculation(calc, request.user):
            return HttpResponse(status=403)

        if calc.order.resource is not None:
            params["resource"] = calc.order.resource.cluster_address

        try:
            frame = calc.calculationframe_set.get(number=frame_num)
        except CalculationFrame.DoesNotExist:
            return redirect("/home/")

        init_params = calc.order.parameters

        params["calc"] = calc
        params["frame_num"] = frame_num
        params["init_params_id"] = init_params.id
    return render(request, "frontend/launch.html", params)


@login_required
def launch_project(request, pk):
    try:
        proj = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return redirect("/home/")

    if not can_view_project(proj, request.user):
        return HttpResponse(status=403)

    if proj.preset is not None:
        init_params_id = proj.preset.params.id

        return render(
            request,
            "frontend/launch.html",
            {
                "proj": proj,
                "procs": BasicStep.objects.all(),
                "init_params_id": init_params_id,
                "packages": settings.PACKAGES,
            },
        )
    else:
        return render(
            request,
            "frontend/launch.html",
            {
                "proj": proj,
                "procs": BasicStep.objects.all(),
                "packages": settings.PACKAGES,
            },
        )


@login_required
def check_functional(request):
    if "functional" not in request.POST.keys():
        return HttpResponse(status=400)

    func = clean(request.POST["functional"])

    if func.strip() == "":
        return HttpResponse("")

    try:
        ccinput.utilities.get_abs_method(func)
    except ccinput.exceptions.InvalidParameter:
        return HttpResponse("Unknown functional")

    return HttpResponse("")


@login_required
def check_basis_set(request):
    if "basis_set" not in request.POST.keys():
        return HttpResponse(status=400)

    bs = clean(request.POST["basis_set"])

    if bs.strip() == "":
        return HttpResponse("")

    try:
        ccinput.utilities.get_abs_basis_set(bs)
    except ccinput.exceptions.InvalidParameter:
        return HttpResponse("Unknown basis set")

    return HttpResponse("")


@login_required
def check_solvent(request):
    if "solvent" not in request.POST:
        return HttpResponse(status=400)

    solv = clean(request.POST["solvent"])

    if solv.strip() == "" or solv.strip().lower() == "vacuum":
        return HttpResponse("")

    if "software" not in request.POST:
        return HttpResponse(status=400)

    software = clean(request.POST["software"]).lower()

    if software != "xtb":  # To change once xtb is supported by ccinput
        try:
            software = ccinput.utilities.get_abs_software(software)
        except ccinput.exceptions.InvalidParameter:
            return HttpResponse(status=400)

    try:
        solvent = ccinput.utilities.get_abs_solvent(solv)
    except ccinput.exceptions.InvalidParameter:
        return HttpResponse("Unknown solvent")

    if solvent not in ccinput.constants.SOFTWARE_SOLVENTS[software]:
        return HttpResponse("Unknown solvent")
    else:
        return HttpResponse("")


@login_required
def delete_preset(request, pk):
    try:
        p = Preset.objects.get(pk=pk)
    except Preset.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_preset(p, request.user):
        return HttpResponse(status=403)

    p.delete()
    return HttpResponse("Preset deleted")


@login_required
def launch_presets(request):
    presets = request.user.preset_set.all().order_by("name")
    return render(request, "frontend/dynamic/launch_presets.html", {"presets": presets})


@login_required
def load_preset(request, pk):
    try:
        p = Preset.objects.get(pk=pk)
    except Preset.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_preset(p, request.user):
        return HttpResponse(status=403)

    return render(
        request,
        "frontend/dynamic/load_params.js",
        {
            "params": p.params,
            "load_charge": False,
        },
    )


@login_required
def load_params(request, pk):
    try:
        params = Parameters.objects.get(pk=pk)
    except Parameters.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_parameters(params, request.user):
        return HttpResponse(status=403)

    return render(
        request,
        "frontend/dynamic/load_params.js",
        {
            "params": params,
            "load_charge": True,
        },
    )


@login_required
def load_flowchart_params(request, pk):
    flowchartObj = Flowchart.objects.get(pk=pk)
    params_dict = {}
    for j in flowchartObj.step_set.all():
        params = {}
        if j.parameters is not None:
            params["calc_solvent"] = j.parameters.solvent
            params["calc_solvation_model"] = j.parameters.solvation_model
            params["calc_solvation_radii"] = j.parameters.solvation_radii
            params["calc_software"] = j.parameters.software
            params["calc_theory_level"] = j.parameters.theory_level
            params["calc_basis_set"] = j.parameters.basis_set
            if j.parameters.method == "PBEh-3c":
                params["pbeh3c"] = True
            elif j.parameters.method == "HF-3c":
                params["hf3c"] = True
            else:
                params["calc_functional"] = j.parameters.method
            params["calc_charge"] = j.parameters.charge
            params["calc_multiplicity"] = j.parameters.multiplicity
            params["calc_df"] = j.parameters.density_fitting
            params["calc_custom_bs"] = j.parameters.custom_basis_sets
            params["calc_specifications"] = j.parameters.specifications
        params_dict[j.id] = params
    return render(
        request,
        "frontend/dynamic/load_flowchart_params.js",
        {
            "params_dict": json.dumps(params_dict),
        },
    )


class CsvParameters:
    def __init__(self):
        self.molecules = {}


class CsvMolecule:
    def __init__(self):
        self.ensembles = {}
        self.name = ""


class CsvEnsemble:
    def __init__(self):
        self.name = ""
        self.data = []


def get_csv(proj, user, scope="flagged", details="full", folders=True):
    pref_units = user.pref_units
    units = user.pref_units_name

    if pref_units == 0:
        CONVERSION = HARTREE_FVAL
        structure_str = ",,,{},{},{:.1f},{:.1f},{:.3f},{:.1f}\n"
        ensemble_str = "{:.1f}"
    elif pref_units == 1:
        CONVERSION = HARTREE_TO_KCAL_F
        structure_str = ",,,{},{},{:.2f},{:.2f},{:.3f},{:.2f}\n"
        ensemble_str = "{:.2f}"
    elif pref_units == 2:
        CONVERSION = 1
        structure_str = ",,,{},{},{:.7f},{:.7f},{:.3f},{:.7f}\n"
        ensemble_str = "{:.7f}"

    summary = {}
    hashes = {}
    csv = ""

    if folders:

        def get_folder_data(folder):
            subfolders = folder.folder_set.all()
            ensembles = folder.ensemble_set.filter(flagged=True)

            ensemble_data = {}
            folder_data = {}

            for e in ensembles:
                if details == "full":
                    summ, ehashes = e.ensemble_summary
                else:
                    summ, ehashes = e.ensemble_short_summary

                for hash, long_name in ehashes.items():
                    if hash not in hashes.keys():
                        hashes[hash] = long_name
                ensemble_data[f"{e.parent_molecule.name} - {e.name}"] = summ

            for f in subfolders:
                folder_data[f.name] = get_folder_data(f)

            return [ensemble_data, folder_data]

        main_folder = proj.main_folder
        if main_folder is None:
            raise Exception(f"Main folder of project {proj.id} is null!")

        data = get_folder_data(main_folder)

        def format_data(ensemble_data, folder_data, hash):
            _str = ""
            for ename, edata in sorted(ensemble_data.items(), key=lambda a: a[0]):
                if hash in edata.keys():
                    (
                        nums,
                        degens,
                        energies,
                        free_energies,
                        ids,
                        rel_energies,
                        weights,
                        w_e,
                        w_f_e,
                    ) = edata[hash]
                    if isinstance(w_f_e, float):
                        _w_f_e = ensemble_str.format(w_f_e * CONVERSION)
                    else:
                        _w_f_e = w_f_e
                    _w_e = ensemble_str.format(w_e * CONVERSION)
                    _str += f"{ename},{_w_e},{_w_f_e}\n"

            for fname, f in sorted(folder_data.items(), key=lambda a: a[0]):
                _str += f"\n,{fname},Energy,Free Energy\n"

                f_str = format_data(*f, hash)
                _str += "\n".join(["," + i for i in f_str.split("\n")])
            return _str

        main_str = ""
        for i, n in hashes.items():
            main_str += f"{n}\n"
            main_str += format_data(*data, i)
            main_str += "\n\n"
        return main_str
    else:
        molecules = list(proj.molecule_set.prefetch_related("ensemble_set").all())
        for mol in molecules:
            if scope == "flagged":
                ensembles = mol.ensemble_set.filter(flagged=True)
            else:
                ensembles = mol.ensemble_set.all()

            for e in ensembles:
                if details == "full":
                    summ, ehashes = e.ensemble_summary
                else:
                    summ, ehashes = e.ensemble_short_summary

                for hash, long_name in ehashes.items():
                    if hash not in hashes.keys():
                        hashes[hash] = long_name

                for p_name in summ.keys():
                    if p_name in summary.keys():
                        csv_p = summary[p_name]
                        if mol.id in csv_p.molecules.keys():
                            csv_mol = csv_p.molecules[mol.id]

                            csv_e = CsvEnsemble()
                            csv_e.name = e.name
                            csv_e.data = summ[p_name]
                            csv_mol.ensembles[e.id] = csv_e

                        else:
                            csv_mol = CsvMolecule()
                            csv_mol.name = mol.name
                            csv_p.molecules[mol.id] = csv_mol

                            csv_e = CsvEnsemble()
                            csv_e.name = e.name
                            csv_e.data = summ[p_name]
                            csv_mol.ensembles[e.id] = csv_e
                    else:
                        csv_p = CsvParameters()

                        csv_mol = CsvMolecule()
                        csv_mol.name = mol.name

                        csv_e = CsvEnsemble()
                        csv_e.name = e.name
                        csv_e.data = summ[p_name]

                        csv_mol.ensembles[e.id] = csv_e

                        csv_p.molecules[mol.id] = csv_mol
                        summary[p_name] = csv_p

        if details == "full":
            csv += "Parameters,Molecule,Ensemble,Structure\n"
            for p_name in summary.keys():
                p = summary[p_name]
                csv += f"{hashes[p_name]},\n"
                for mol in p.molecules.values():
                    csv += f",{mol.name},\n"
                    csv += ",,,Number,Degeneracy,Energy,Relative Energy,Weight,Free Energy,\n"
                    for e in mol.ensembles.values():
                        csv += f",,{e.name},\n"
                        (
                            nums,
                            degens,
                            energies,
                            free_energies,
                            ids,
                            rel_energies,
                            weights,
                            w_e,
                            w_f_e,
                        ) = e.data
                        for n, d, en, f_en, r_el, w in zip(
                            nums, degens, energies, free_energies, rel_energies, weights
                        ):
                            csv += structure_str.format(
                                n,
                                d,
                                en * CONVERSION,
                                r_el * CONVERSION,
                                w,
                                f_en * CONVERSION,
                            )
        csv += "\n\n"
        csv += "SUMMARY\n"
        csv += "Method,Molecule,Ensemble,Weighted Energy ({}),Weighted Free Energy ({}),\n".format(
            units, units
        )
        for p_name in summary.keys():
            p = summary[p_name]
            csv += f"{hashes[p_name]},\n"
            for mol in p.molecules.values():
                csv += f",{mol.name},\n"
                for e in mol.ensembles.values():
                    if details == "full":
                        arr_ind = 7
                    else:
                        arr_ind = 0

                    _w_e = e.data[arr_ind]
                    if _w_e != "-":
                        w_e = ensemble_str.format(_w_e * CONVERSION)
                    else:
                        w_e = _w_e

                    _w_f_e = e.data[arr_ind + 1]
                    if _w_f_e != "-":
                        w_f_e = ensemble_str.format(_w_f_e * CONVERSION)
                    else:
                        w_f_e = _w_f_e

                    csv += f",,{e.name},{w_e},{w_f_e}\n"

    return csv


def download_project_csv(proj, user, scope, details, folders):
    csv = get_csv(proj, user, scope, details, folders)

    proj_name = proj.name.replace(" ", "_")
    response = HttpResponse(csv, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={proj_name}.csv"
    return response


@login_required
def cancel_calc(request):
    if request.method != "POST":
        return HttpResponse(status=403)

    if "id" in request.POST.keys():
        try:
            id = clean(request.POST["id"])
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if request.user != calc.order.author:
        return HttpResponse(status=403)

    if settings.IS_CLOUD:
        logger.info(f"Killing calc {calc.id}")
        calc.set_as_cancelled()
    else:
        if is_test:
            cancel(calc.id)
        else:
            cancel.delay(str(calc.id))

    return HttpResponse(status=200)


def download_project_logs(proj, user, scope, details, folders):
    # folders options makes this somewhat duplicate code

    tmp_dir = f"/tmp/{user.id}_{proj.author.username}_{time.time()}"  ## tmpdir
    os.mkdir(tmp_dir)
    for mol in sorted(proj.molecule_set.all(), key=lambda l: l.name):
        for e in mol.ensemble_set.all():
            if scope == "flagged" and not e.flagged:
                continue
            e_dir = os.path.join(tmp_dir, str(e.id) + "_" + e.name.replace(" ", "_"))
            try:
                os.mkdir(e_dir)
            except FileExistsError:
                pass
            for ind, s in enumerate(e.structure_set.all()):
                for calc in s.calculation_set.all():
                    if calc.status == 0:
                        continue
                    if details == "freq":
                        if calc.step.name != "Frequency Calculation":
                            continue
                        log_name = (
                            e.name
                            + "_"
                            + calc.parameters.file_name
                            + f"_conf{s.number}"
                        )
                    elif details == "full":
                        log_name = (
                            e.name
                            + "_"
                            + calc.step.name
                            + "_"
                            + calc.parameters.file_name
                            + f"_conf{s.number}"
                        )

                    if len(calc.output_files) == 0:
                        continue

                    logs = json.loads(calc.output_files)

                    for subname, log in logs.items():
                        if subname == "calc":
                            _log_name = log_name + ".log"
                        else:
                            _log_name = f"{log_name}_{subname}.log"

                        with open(os.path.join(e_dir, _log_name), "w") as out:
                            out.write(log)

                    if (
                        calc.parameters.software == "xtb"
                    ):  # xtb logs don't contain the structure
                        with open(os.path.join(e_dir, log_name + ".xyz"), "w") as out:
                            out.write(s.xyz_structure)

    for d in glob.glob(f"{tmp_dir}/*/"):
        if len(os.listdir(d)) == 0:
            os.rmdir(d)

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zip:
        for d in glob.glob(f"{tmp_dir}/*/"):
            for f in glob.glob(f"{d}*"):
                zip.write(
                    f, os.path.join(proj.name.replace(" ", "_"), *f.split("/")[3:])
                )

    response = HttpResponse(mem.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="{}_logs.zip"'.format(
        proj.name.replace(" ", "_")
    )
    return response


@login_required
def download_project_post(request):
    if "id" in request.POST.keys():
        try:
            id = clean(request.POST["id"])
        except ValueError:
            return error(request, "Invalid project")
    else:
        return HttpResponse(status=403)

    if "data" in request.POST.keys():
        data = clean(request.POST["data"])
        if data not in ["summary", "logs"]:
            return error(request, "Invalid data type requested")
    else:
        return error(request, "No data type requested")

    if "scope" in request.POST.keys():
        scope = clean(request.POST["scope"])
        if scope not in ["all", "flagged"]:
            return error(request, "Invalid scope")
    else:
        return error(request, "No scope given")

    if "details" in request.POST.keys():
        details = clean(request.POST["details"])
        if data == "summary" and details not in ["full", "summary"]:
            return error(request, "Invalid details level")
        if data == "logs" and details not in ["full", "freq"]:
            return error(request, "Invalid details level")
    else:
        return error(request, "No details level given")

    folders = False
    if "folders" in request.POST.keys():
        folders = clean(request.POST["folders"])
        if folders.lower() == "false":
            folders = False
        elif folders.lower() == "true":
            folders = True
        else:
            return error(request, "Invalid folders option (true or false)")

    try:
        proj = Project.objects.get(pk=id)
    except Project.DoesNotExist:
        return error(request, "Invalid project")

    if not can_view_project(proj, request.user):
        return HttpResponseRedirect("/home/")

    if data == "summary":
        return download_project_csv(proj, request.user, scope, details, folders)
    elif data == "logs":
        return download_project_logs(proj, request.user, scope, details, folders)


@login_required
def download_project(request, pk):
    try:
        proj = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_project(proj, request.user):
        return HttpResponseRedirect("/home/")

    return render(request, "frontend/download_project.html", {"proj": proj})


@login_required
def project_folders(request, user_id, proj, folder_path):
    path = clean(folder_path).split("/")

    # Make trailing slashes mandatory
    if path[-1].strip() != "":
        return HttpResponseRedirect(f"/projects/{username}/{proj}/{folder_path + '/'}")

    target_project = clean(proj)
    target_user_id = clean(user_id)

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return HttpResponseRedirect("/home/")

    if not user_intersection(target_user, request.user):
        return HttpResponseRedirect("/home/")

    try:
        project = target_user.project_set.get(name=target_project)
    except Project.DoesNotExist:
        return HttpResponseRedirect("/home/")

    if not can_view_project(project, request.user):
        return HttpResponseRedirect("/home/")

    folders = []
    ensembles = []

    def get_subfolder(path, folder):
        if len(path) == 0 or path[0].strip() == "":
            return folder
        name = path.pop(0)

        try:
            subfolder = folder.folder_set.get(name=name)
        except Folder.DoesNotExist:
            return None

        return get_subfolder(path, subfolder)

    if len(path) == 1:
        folder = project.main_folder
    else:
        folder = get_subfolder(path[1:], project.main_folder)

    if folder is None:
        return HttpResponse(status=404)

    folders = folder.folder_set.all().order_by(Lower("name"))
    ensembles = folder.ensemble_set.all().order_by(Lower("parent_molecule__name"))

    return render(
        request,
        "frontend/project_folders.html",
        {
            "project": project,
            "folder": folder,
            "folders": folders,
            "ensembles": ensembles,
        },
    )


@login_required
def download_folder(request, pk):
    try:
        folder = Folder.objects.get(pk=pk)
    except Folder.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_project(folder.project, request.user):
        return HttpResponse(status=403)

    def add_folder_data(zip, folder, path):
        subfolders = folder.folder_set.all()
        ensembles = folder.ensemble_set.filter(flagged=True)

        for e in ensembles:
            prefix = f"{e.parent_molecule.name}_"
            related_orders = _get_related_calculations(e)
            # Verify if the user can view the ensemble?
            # The ensembles should be in the project which he can view, so probably not necessary

            for o in related_orders:
                for c in o.calculation_set.all():
                    if c.status == 2:
                        log_name = clean_filename(
                            prefix
                            + c.corresponding_ensemble.name
                            + "_"
                            + c.step.short_name
                            + "_conf"
                            + str(c.structure.number)
                        )

                        if len(c.output_files) == 0:
                            continue

                        logs = json.loads(c.output_files)
                        for subname, log in logs.items():
                            if subname == "calc":
                                _log_name = log_name + ".log"
                            else:
                                _log_name = f"{log_name}_{subname}.log"

                            zip.writestr(
                                os.path.join(
                                    path, clean_filename(folder.name), _log_name
                                ),
                                log,
                            )

                        if c.parameters.software == "xtb":
                            zip.writestr(
                                os.path.join(
                                    path,
                                    clean_filename(folder.name),
                                    f"{log_name}.xyz",
                                ),
                                c.structure.xyz_structure,
                            )

        for f in subfolders:
            add_folder_data(zip, f, os.path.join(path, clean_filename(folder.name)))

    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zip:
        add_folder_data(zip, folder, "")

    response = HttpResponse(mem.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="{}_{}.zip"'.format(
        clean_filename(folder.project.name), clean_filename(folder.name)
    )
    return response


@login_required
def move_element(request):
    if "id" not in request.POST.keys():
        return HttpResponse(status=400)

    id = clean(request.POST["id"])

    if "folder_id" not in request.POST.keys():
        return HttpResponse(status=400)

    folder_id = clean(request.POST["folder_id"])

    if "type" not in request.POST.keys():
        return HttpResponse(status=400)

    type = clean(request.POST["type"])

    if type not in ["ensemble", "folder"]:
        return HttpResponse(status=400)

    try:
        folder = Folder.objects.get(pk=folder_id)
    except Folder.DoesNotExist:
        return HttpResponse(status=404)

    if request.user != folder.project.author:
        return HttpResponse(status=403)

    if type == "ensemble":
        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=404)

        if request.user != e.parent_molecule.project.author:
            return HttpResponse(status=404)

        if not e.flagged:
            return HttpResponse(status=400)

        if e.folder != folder:
            e.folder = folder
            e.save()
    elif type == "folder":
        if folder.depth > MAX_FOLDER_DEPTH:
            return HttpResponse(status=403)

        try:
            f = Folder.objects.get(pk=id)
        except Folder.DoesNotExist:
            return HttpResponse(status=404)

        if request.user != f.project.author:
            return HttpResponse(status=403)

        if f.parent_folder != folder:
            f.parent_folder = folder
            f.depth = folder.depth + 1
            f.save()

    return HttpResponse(status=204)


@login_required
def relaunch_calc(request):
    if request.method != "POST":
        return HttpResponse(status=403)

    if "id" in request.POST.keys():
        try:
            id = clean(request.POST["id"])
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if request.user != calc.order.author:
        return HttpResponse(status=403)

    if calc.status != 3:
        return HttpResponse(status=204)

    scr_dir = os.path.join(CALCUS_SCR_HOME, str(calc.id))

    try:
        rmtree(scr_dir)
    except FileNotFoundError:
        pass

    calc.status = 0
    calc.remote_id = 0
    calc.order.hidden = False
    calc.order.save()
    calc.save()

    if calc.local:
        if settings.IS_CLOUD:
            send_gcloud_task("/cloud_calc/", str(calc.id), size=get_calc_size(calc))
        else:
            t = run_calc.s(str(calc.id)).set(queue="comp")
            res = t.apply_async()
            calc.task_id = res
            calc.save()
    else:
        send_cluster_command(f"launch\n{calc.id}\n{calc.order.resource_id}\n")

    return HttpResponse(status=200)


@login_required
def refetch_calc(request):
    if request.method != "POST":
        return HttpResponse(status=403)

    if "id" in request.POST.keys():
        try:
            id = clean(request.POST["id"])
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if request.user != calc.order.author:
        return HttpResponse(status=403)

    if calc.status < 2:
        return HttpResponse(status=204)

    if calc.local:
        return HttpResponse(status=204)

    calc.status = 1
    calc.save()

    send_cluster_command(f"launch\n{calc.id}\n{calc.order.resource_id}\n")

    return HttpResponse(status=200)


@login_required
def ensemble_map(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect("/home/")

    if not can_view_molecule(mol, request.user):
        return redirect("/home/")
    json = """{{
                "nodes": [
                        {}
                        ],
                "edges": [
                        {}
                    ]
                }}"""
    nodes = ""
    for e in mol.ensemble_set.all():
        label = "{} ({})".format(e.name, str(e.id)[:5])
        if e.flagged:
            border_text = """, "bcolor": "black", "bwidth": 2"""
        else:
            border_text = ""
        nodes += """{{ "data": {{"label":"{}","id": "{}", "name": "{}", "href": "/ensemble/{}", "color": "{}"{}}} }},""".format(
            label, e.id, e.name, e.id, e.get_node_color, border_text
        )
    nodes = nodes[:-1]

    edges = ""
    for e in mol.ensemble_set.all():
        if e.origin != None:
            edges += """{{ "data": {{"source": "{}", "target": "{}"}} }},""".format(
                e.origin.id, e.id
            )
    edges = edges[:-1]
    response = HttpResponse(json.format(nodes, edges), content_type="text/json")

    return HttpResponse(response)


@login_required
def analyse(request, project_id):
    try:
        proj = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_project(proj, request.user):
        return HttpResponse(status=403)

    csv = get_csv(proj, request.user, folders=False)
    js_csv = []
    """
    # Generates a list of cells in the format [value, xcoord, ycoord]
    for ind1, line in enumerate(csv.split("\n")):
        for ind2, el in enumerate(line.split(",")):
            js_csv.append([el, ind1, ind2])
    """
    for ind1, line in enumerate(csv.split("\n")[1:]):
        js_csv.append(line.replace("Relative Energy", "Rel. Energy").split(","))

    l = len(csv.split("\n")) + 5
    return render(
        request,
        "frontend/analyse.html",
        {"data": json.dumps(js_csv), "len": l, "proj": proj},
    )


@login_required
def calculationorder(request, pk):
    try:
        order = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_order(order, request.user):
        return HttpResponse(status=404)

    return render(request, "frontend/calculationorder.html", {"order": order})


@login_required
def calculation(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_calculation(calc, request.user):
        return HttpResponse(status=404)

    return render(request, "frontend/calculation.html", {"calc": calc})


@login_required
def see(request, pk):
    try:
        order = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponse(status=404)

    if request.user != order.author:
        return HttpResponse(status=404)

    order.see()

    return HttpResponse(status=200)


@login_required
def see_all(request):
    calcs = CalculationOrder.objects.filter(author=request.user, hidden=False)

    for c in calcs:
        if c.new_status:
            c.see()

    # This should be true if everything works.
    # If a glitch happens and the counter is off, this will reset it.
    request.user.unseen_calculations = 0
    request.user.save()

    return HttpResponse(status=200)


@login_required
def clean_all_successful(request):
    to_update = []
    calcs = CalculationOrder.objects.filter(author=request.user, hidden=False)
    for c in calcs:
        if c.last_seen_status != 0:    #default value of c.last_seen_status is 0, if calculation is not viewed
            if c.status == 2:
                c.hidden = True
                c.see()
                to_update.append(c)

    CalculationOrder.objects.bulk_update(to_update, ["hidden", "last_seen_status"])

    return HttpResponse(status=200)


@login_required
def clean_all_completed(request):
    to_update = []
    calcs = CalculationOrder.objects.filter(author=request.user, hidden=False)
    for c in calcs:
        if c.last_seen_status != 0:   #default value of c.last_seen_status is 0, if calculation is not viewed
            if c.status in [2, 3]:
                c.hidden = True
                c.see()
                to_update.append(c)

    CalculationOrder.objects.bulk_update(to_update, ["hidden", "last_seen_status"])

    return HttpResponse(status=200)


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was updated.")
            return HttpResponseRedirect("/change_password/")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "frontend/change_password.html", {"form": form})


@login_required
def create_full_account(request):
    if request.method == "POST":
        form = CreateFullAccountForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            return redirect("/profile/")
    else:
        form = CreateFullAccountForm(request.user)

    return render(
        request,
        "registration/create_full_account.html",
        {"form": form, "tos": full_tos},
    )


def handler404(request, *args, **argv):
    if request.method == "POST":
        return HttpResponse("Content not found")
    return render(request, "error/404.html", {})


def handler500(request, *args, **argv):
    if request.method == "POST":
        return HttpResponse("Content could not be loaded: internal server error")

    return render(request, "error/500.html", {})


def pricing(request):
    return render(request, "frontend/pricing.html")


def checkout(request):
    import stripe

    ## iff
    price_id = clean(request.POST["priceId"])

    session = stripe.checkout.Session.create(
        success_url=settings.HOST_URL
        + "/subscription_successful/{CHECKOUT_SESSION_ID}",
        cancel_url=f"{settings.HOST_URL}/home/",
        mode="subscription",
        line_items=[
            {
                "price": price_id,
                # For metered billing, do not pass quantity
                "quantity": 1,
            }
        ],
    )

    return redirect(session.url)


def subscription_successful(request, session_id):
    logger.info(f"Subscription successful for {session_id}")
    return redirect("/profile/")


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return HttpResponse(status=400)

    import stripe

    data = request.body
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            data, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Receive Stripe webhook with invalid payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Receive Stripe webhook with invalid signature: {str(e)}")
        return HttpResponse(status=400)

    if event.type == "payment_intent.succeeded":
        payment = event["data"]["object"]
        customer = stripe.Customer.retrieve(payment["customer"])
        logger.info(f"Payment successful by {customer['email']}")

        try:
            user = User.objects.get(email=customer["email"])
        except User.DoesNotExist:
            logger.error(
                f"Customer with email {customer['email']} does not have an account"
            )
        else:
            tasks.create_subscription(user)
            logger.info(f"Subscription created for {customer['email']}")
    else:
        logger.info(f"Unhandled Stripe event: {event.type}")

    return HttpResponse(status=200)


@csrf_exempt
def stripe_config(request):
    if request.method == "GET":
        stripe_config = {"publicKey": settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)
