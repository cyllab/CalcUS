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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.views import generic
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.utils.datastructures import MultiValueDictKeyError

from .forms import UserCreateForm
from .models import Calculation, Profile, Project, ClusterAccess, ClusterCommand, Example, PIRequest, ResearchGroup, Parameters, Structure, Ensemble, Procedure, Step, BasicStep, CalculationOrder, Molecule, Property, Filter, Exercise, CompletedExercise, Preset, Recipe
from .tasks import dispatcher, del_project, del_molecule, del_ensemble, BASICSTEP_TABLE, SPECIAL_FUNCTIONALS, cancel, run_calc
from .decorators import superuser_required
from .tasks import system, analyse_opt, generate_xyz_structure, gen_fingerprint, get_Gaussian_xyz
from .constants import *

from shutil import copyfile, make_archive, rmtree
from django.db.models.functions import Lower

from throttle.decorators import throttle

import nmrglue as ng

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False

if is_test:
    CALCUS_SCR_HOME = os.environ['CALCUS_TEST_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_TEST_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_TEST_KEY_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_TEST_CLUSTER_HOME']
else:
    CALCUS_SCR_HOME = os.environ['CALCUS_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_KEY_HOME']
    CALCUS_CLUSTER_HOME = os.environ['CALCUS_CLUSTER_HOME']

KEY_SIZE = 32

class IndexView(generic.ListView):
    template_name = 'frontend/list.html'
    context_object_name = 'latest_frontend'
    paginate_by = '20'

    def get_queryset(self, *args, **kwargs):
        if isinstance(self.request.user, AnonymousUser):
            return []

        try:
            page = int(self.request.GET.get('page'))
        except KeyError:
            page = 0

        self.request.session['previous_page'] = page
        proj = self.request.GET.get('project')
        type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        target_username = self.request.GET.get('user')
        unseen = self.request.GET.get('unseen')

        try:
            target_profile = User.objects.get(username=target_username).profile
        except User.DoesNotExist:
            return []

        if profile_intersection(self.request.user.profile, target_profile):
            hits = target_profile.calculationorder_set.all()
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
            if unseen == "true":
                new_hits = []
                for hit in hits:
                    if hit.status != hit.last_seen_status:
                        new_hits.append(hit)
                hits = new_hits

            return sorted(hits, key=lambda d: d.date, reverse=True)

        else:
            return []

def home(request):
    return render(request, 'frontend/home.html')

@login_required
def periodictable(request):
    return render(request, 'frontend/periodictable.html')

@login_required
def specifications(request):
    return render(request, 'frontend/dynamic/specifications.html')

@login_required
def get_available_bs(request):
    if 'elements' in request.POST.keys():
        raw_el = clean(request.POST['elements'])
        elements = [i.strip() for i in raw_el.split(' ') if i.strip() != '']
    else:
        elements = None

    basis_sets = basis_set_exchange.filter_basis_sets(elements=elements)
    response = ""
    for k in basis_sets.keys():
        name = basis_sets[k]['display_name']
        response += """<option value="{}">{}</option>\n""".format(k, name)
    return HttpResponse(response)

@login_required
def get_available_elements(request):
    if 'bs' in request.POST.keys():
        bs = clean(request.POST['bs'])
    else:
        return HttpResponse(status=204)

    md = basis_set_exchange.get_metadata()
    if bs not in md.keys():
        return HttpResponse(status=404)

    version = md[bs]['latest_version']
    elements = md[bs]['versions'][version]['elements']
    response = ' '.join(elements)
    return HttpResponse(response)

@login_required
def aux_molecule(request):
    if 'proj' not in request.POST.keys():
        return HttpResponse(status=404)

    project = clean(request.POST['proj'])

    if project.strip() == '' or project == 'New Project':
        return HttpResponse(status=204)

    try:
        project_set = request.user.profile.project_set.filter(name=project)
    except Profile.DoesNotExist:
        return HttpResponse(status=404)

    if len(project_set) != 1:
        print("More than one project with the same name found!")
        return HttpResponse(status=404)
    else:
        project_obj = project_set[0]

    return render(request, 'frontend/dynamic/aux_molecule.html', {'molecules': project_obj.molecule_set.all()})

@login_required
def aux_ensemble(request):
    if 'mol_id' not in request.POST.keys():
        return HttpResponse(status=404)

    _id = clean(request.POST['mol_id'])
    if _id.strip() == '':
        return HttpResponse(status=204)
    id = int(_id)

    try:
        mol = Molecule.objects.get(pk=id)
    except Molecule.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_molecule(mol, request.user.profile):
        return HttpResponse(status=404)

    return render(request, 'frontend/dynamic/aux_ensembles.html', {'ensembles': mol.ensemble_set.all()})

@login_required
def aux_structure(request):
    if 'e_id' not in request.POST.keys():
        return HttpResponse(status=404)

    _id = clean(request.POST['e_id'])
    if _id.strip() == '':
        return HttpResponse(status=204)
    id = int(_id)

    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    if not can_view_ensemble(e, request.user.profile):
        return HttpResponse(status=404)

    return render(request, 'frontend/dynamic/aux_structures.html', {'structures': e.structure_set.all()})


@login_required
def calculations(request):
    return render(request, 'frontend/calculations.html', {
            'profile': request.user.profile,
            'steps': BasicStep.objects.all(),
        })

@login_required
def projects(request):
    return render(request, 'frontend/projects.html', {
            'profile': request.user.profile,
            'target_profile': request.user.profile,
            'projects': request.user.profile.project_set.all(),
        })

@login_required
def projects_username(request, username):
    target_username = clean(username)

    try:
        target_profile = User.objects.get(username=target_username).profile
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if request.user.profile == target_profile:
        return render(request, 'frontend/projects.html', {
                    'profile': request.user.profile,
                    'target_profile': target_profile,
                    'projects': request.user.profile.project_set.all(),
                })
    elif profile_intersection(request.user.profile, target_profile):
        return render(request, 'frontend/projects.html', {
                    'profile': request.user.profile,
                    'target_profile': target_profile,
                    'projects': target_profile.project_set.filter(private=0),
                })

    else:
        return HttpResponse(status=404)

@login_required
def get_projects(request):
    if request.method == 'POST':
        target_username = clean(request.POST['username'])
        profile = request.user.profile

        try:
            target_profile = User.objects.get(username=target_username).profile
        except User.DoesNotExist:
            return HttpResponse(status=404)

        if profile == target_profile:
            return render(request, 'frontend/project_list.html', {'projects' : target_profile.project_set.all()})
        elif profile_intersection(profile, target_profile):
            return render(request, 'frontend/project_list.html', {'projects' : target_profile.project_set.filter(private=0)})
        else:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)

@login_required
def create_project(request):
    if request.method == 'POST':
        profile = request.user.profile
        proj = Project.objects.create(name="My Project", author=profile)
        proj.save()
        response = """
<div class="box has-background-danger" id="proj_box_{}">
        <p style="float: right;">
                        <a href="/analyse/{}"><i class="fas fa-table"></i></a>
                        <a href="/download_project/{}"><i class="fas fa-download"></i></a>
                        <a onclick="edit_field({});"><i class="fas fa-edit" id="icon_{}"></i></a>
                        <a onclick="del({});"><i class="fas fa-trash-alt"></i></a>
        </p>
        <a href="/projects/{}/{}">
                <strong><p id="proj_name_{}">{}</p></strong>
                <p>0 Molecule(s) &nbsp; (0 Calculation(s): &nbsp; 0 Queued; &nbsp; 0 Running; &nbsp; 0 Completed) </p>
        </a>
</div>
""".format(proj.id, proj.id, proj.id, proj.id, proj.id, proj.id, profile.username, proj.name, proj.id, proj.name)

        return HttpResponse(response)
    else:
        return HttpResponse(status=404)

@login_required
def project_details(request, username, proj):
    target_project = clean(proj)
    target_username = clean(username)

    try:
        target_profile = User.objects.get(username=target_username).profile
    except User.DoesNotExist:
        return HttpResponseRedirect("/home/")

    if profile_intersection(request.user.profile, target_profile):
        try:
            project = target_profile.project_set.get(name=target_project)
        except Project.DoesNotExist:
            return HttpResponseRedirect("/home/")
        if can_view_project(project, request.user.profile):
            return render(request, 'frontend/project_details.html', {
            'molecules': project.molecule_set.all().order_by(Lower('name')),
            'project': project,
            })
        else:
            return HttpResponseRedirect("/home/")
    else:
        return HttpResponseRedirect("/home/")

def clean(txt):
    return bleach.clean(txt)

@login_required
def molecule(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect('/home/')

    if not can_view_molecule(mol, request.user.profile):
        return redirect('/home/')

    return render(request, 'frontend/molecule.html', {'profile': request.user.profile,
        'ensembles': mol.ensemble_set.filter(hidden=False),
        'molecule': mol})

@login_required
def ensemble_table_body(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect('/home/')

    if not can_view_molecule(mol, request.user.profile):
        return redirect('/home/')

    return render(request, 'frontend/ensemble_table_body.html', {'profile': request.user.profile,
        'molecule': mol})

@login_required
def ensemble(request, pk):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    if not can_view_ensemble(e, request.user.profile):
        return redirect('/home/')

    return render(request, 'frontend/ensemble.html', {'profile': request.user.profile,
        'ensemble': e})

@login_required
def nmr_analysis(request, pk, pid):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    if not can_view_ensemble(e, request.user.profile):
        return redirect('/home/')

    try:
        param = Parameters.objects.get(pk=pid)
    except Parameters.DoesNotExist:
        return redirect('/home/')

    if not can_view_parameters(param, request.user.profile):
        return redirect('/home/')

    return render(request, 'frontend/nmr_analysis.html', {'profile': request.user.profile,
        'ensemble': e, 'parameters': param})

def _get_shifts(request):
    if 'id' not in request.POST.keys():
        return ''

    if 'pid' not in request.POST.keys():
        return ''

    if 'eq_str' not in request.POST.keys():
        return ''

    id = clean(request.POST['id'])
    pid = clean(request.POST['pid'])
    eq_str = clean(request.POST['eq_str'])

    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return ''

    if not can_view_ensemble(e, request.user.profile):
        return ''

    try:
        param = Parameters.objects.get(pk=pid)
    except Parameters.DoesNotExist:
        return ''

    if not can_view_parameters(param, request.user.profile):
        return ''

    scaling_factors = {}
    if 'scaling_factors' in request.POST.keys():
        scaling_str = clean(request.POST['scaling_factors'])
        for entry in scaling_str.split(';'):
            if entry.strip() == '':
                continue

            el, m, b = entry.split(',')
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

        if p.simple_nmr == '':
            continue

        weighted_shifts = e.weighted_nmr_shifts(param)
        for entry in weighted_shifts:
            num = int(entry[0])-1
            el = entry[1]
            shift = float(entry[2])
            shifts[num] = [el, shift, '-']

    eq_split = eq_str.split(';')
    for group in eq_split:
        if group.strip() == "":
            continue
        nums = [int(i.strip()) for i in group.split() if i.strip() != '']
        lnums = len(nums)
        eq_shift = sum([shifts[i][1] for i in nums])/lnums
        for num in nums:
            shifts[num][1] = eq_shift

    if len(scaling_factors.keys()) > 0:
        for shift in shifts.keys():
            el = shifts[shift][0]
            if el in scaling_factors.keys():
                slope, intercept = scaling_factors[el]
                s = shifts[shift][1]
                shifts[shift][2] = "{:.3f}".format((s-intercept)/slope)
    return shifts

@login_required
def get_shifts(request):

    shifts = _get_shifts(request)

    if shifts == '':
        return HttpResponse(status=404)

    CELL = """
    <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{:.3f}</td>
            <td>{}</td>
    </tr>"""

    response = ""
    for shift in shifts.keys():
        response += CELL.format(shift, *shifts[shift])

    return HttpResponse(response)

@login_required
def get_exp_spectrum(request):
    t = time.time()
    d = "/tmp/nmr_{}".format(t)
    os.mkdir(d)
    for ind, f in enumerate(request.FILES.getlist("file")):
        in_file = f.read()#not cleaned
        with open(os.path.join(d, f.name), 'wb') as out:
            out.write(in_file)

    dic, fid = ng.fileio.bruker.read(d)

    zero_fill_size = 32768
    fid = ng.bruker.remove_digital_filter(dic, fid)
    fid = ng.proc_base.zf_size(fid, zero_fill_size) # <2>
    fid = ng.proc_base.rev(fid) # <3>
    fid = ng.proc_base.fft(fid)
    fid = ng.proc_autophase.autops(fid, 'acme')

    offset = (float(dic['acqus']['SW']) / 2.) - (float(dic['acqus']['O1']) / float(dic['acqus']['BF1']))
    start = float(dic['acqus']['SW']) - offset
    end = -offset
    step = float(dic['acqus']['SW']) / zero_fill_size

    ppms = np.arange(start, end, -step)[:zero_fill_size]

    fid = ng.proc_base.mult(fid, c=1./max(fid))
    def plotspectra(ppms, data, start=None, stop=None):
        if start: # <1>
            dx = abs(ppms - start)
            ixs = list(dx).index(min(dx))
            ppms = ppms[ixs:]
            data = data[:,ixs:]
        if stop:
            dx = abs(ppms - stop)
            ixs = list(dx).index(min(dx))
            ppms = ppms[:ixs]
            data = data[:,:ixs]

        return ppms, data

    ppms, fid = plotspectra(ppms, np.array([fid]), start=10, stop=0)
    shifts = _get_shifts(request)
    if shifts == '':
        response = "PPM,Signal\n"
        for x, y in zip(ppms[0::10], fid[0,0::10]):
            response += "{},{}\n".format(-x, np.real(y))

        return HttpResponse(response)
    else:
        sigma = 0.001
        def plot_peaks(_x, PP):
            val = 0
            for w in PP:
                dd = list(abs(ppms - w))
                T = fid[0,dd.index(min(dd))]
                val += np.exp(-(_x-w)**2/sigma)
            val = val/max(val)
            return val
        _ppms = ppms[0::10]
        _fid = fid[0,0::10]/max(fid[0,0::10])
        l_shifts = [float(shifts[i][2]) for i in shifts if shifts[i][0] == 'H']
        pred = plot_peaks(_ppms, l_shifts)
        response = "PPM,Signal,Prediction\n"
        for x, y, z in zip(_ppms, _fid, pred):
            response += "{:.3f},{:.3f},{:.3f}\n".format(-x, np.real(y), z)
        return HttpResponse(response)

@login_required
def link_order(request, pk):
    try:
        o = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponseRedirect("/home/")

    profile = request.user.profile

    if not can_view_order(o, profile):
        return HttpResponseRedirect("/home/")

    if profile == o.author:
        if o.last_seen_status != o.status:
            o.last_seen_status = o.status
            o.save()

    if o.result_ensemble:
        return HttpResponseRedirect("/ensemble/{}".format(o.result_ensemble.id))
    else:
        if o.ensemble:
            return HttpResponseRedirect("/ensemble/{}".format(o.ensemble.id))
        elif o.structure:
            return HttpResponseRedirect("/ensemble/{}".format(o.structure.parent_ensemble.id))
        else:
            return HttpResponseRedirect("/calculations/")

@login_required
def details_ensemble(request):
    if request.method == 'POST':
        pk = int(clean(request.POST['id']))
        try:
            p_id = int(clean(request.POST['p_id']))
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

        if not can_view_ensemble(e, request.user.profile):
            return HttpResponse(status=403)

        if e.has_nmr(p):
            shifts = e.weighted_nmr_shifts(p)
            return render(request, 'frontend/details_ensemble.html', {'profile': request.user.profile,
                'ensemble': e, 'parameters': p, 'shifts': shifts})
        else:
            return render(request, 'frontend/details_ensemble.html', {'profile': request.user.profile,
                'ensemble': e, 'parameters': p})

    return HttpResponse(status=403)

@login_required
def details_structure(request):
    if request.method == 'POST':
        pk = int(clean(request.POST['id']))
        try:
            p_id = int(clean(request.POST['p_id']))
            num = int(clean(request.POST['num']))
        except KeyError:
            return HttpResponse(status=204)

        try:
            e = Ensemble.objects.get(pk=pk)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if not can_view_ensemble(e, request.user.profile):
            return HttpResponse(status=403)

        try:
            s = e.structure_set.get(number=num)
        except Structure.DoesNotExist:
            return HttpResponse(status=403)

        try:
            p = Parameters.objects.get(pk=p_id)
        except Parameters.DoesNotExist:
            return HttpResponse(status=403)

        try:
            prop = s.properties.get(parameters=p)
        except Property.DoesNotExist:
            return HttpResponse(status=404)

        return render(request, 'frontend/details_structure.html', {'profile': request.user.profile,
            'structure': s, 'property': prop, 'ensemble': e})

    return HttpResponse(status=403)

@login_required
def details(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return redirect('/home/')

    if not can_view_calculation(calc, request.user.profile):
        return redirect('/home/')

    return render(request, 'frontend/details.html', {'profile': request.user.profile,
        'calculation': calc})

def learn(request):
    exercises = Exercise.objects.all()
    examples = Example.objects.all()
    recipes = Recipe.objects.all()

    return render(request, 'frontend/learn.html', {'exercises': exercises, 'examples': examples, 'recipes': recipes})

def is_close(ans, question):
    if ans >= question.answer - question.tolerance and ans <= question.answer + question.tolerance:
        return True
    else:
        return False

def answer(request):
    if request.method != "POST":
        return HttpResponse(status=404)

    if 'exercise' not in request.POST.keys():
        return HttpResponse("Error")

    try:
        ex_id = int(clean(request.POST['exercise']))
    except ValueError:
        return HttpResponse("Error")

    try:
        ex = Exercise.objects.get(pk=ex_id)
    except Exercise.DoesNotExist:
        return HttpResponse("Error")

    questions = ex.question_set.all()
    for q in questions:
        try:
            answer = float(clean(request.POST['answer_{}'.format(q.id)]))
        except KeyError:
            return HttpResponse("Error")
        except ValueError:
            return HttpResponse("Please enter numbers")

        if not is_close(answer, q):
            return HttpResponse("Not all answers are correct")

    profile = request.user.profile

    try:
        c = CompletedExercise.objects.get(exercise=ex, completed_by=profile)
    except CompletedExercise.DoesNotExist:
        c = CompletedExercise.objects.create(exercise=ex, completed_by=profile)
        c.save()

    return HttpResponse("Correct!")

def exercise(request, pk):
    try:
        ex = Exercise.objects.get(pk=pk)
    except Exercise.DoesNotExist:
        pass

    return render(request, 'exercises/' + ex.page_path, {'questions': ex.question_set.all(), 'exercise': ex})

def example(request, pk):
    try:
        ex = Example.objects.get(pk=pk)
    except Example.DoesNotExist:
        pass

    return render(request, 'examples/' + ex.page_path, {})

def recipe(request, pk):
    try:
        r = Recipe.objects.get(pk=pk)
    except Recipe.DoesNotExist:
        pass

    return render(request, 'recipes/' + r.page_path, {})

class RegisterView(generic.CreateView):
    form_class = UserCreateForm
    template_name = 'registration/signup.html'
    model = Profile
    success_url = '/accounts/login/'

def please_register(request):
        return render(request, 'frontend/please_register.html', {})

def error(request, msg):
    return render(request, 'frontend/error.html', {
        'profile': request.user.profile,
        'error_message': msg,
        })

def parse_parameters(request, name_required=True):
    profile = request.user.profile

    if name_required:
        if 'calc_name' in request.POST.keys():
            name = clean(request.POST['calc_name'])
            if name.strip() == '':
                if 'starting_struct' not in request.POST.keys() and 'starting_ensemble' not in request.POST.keys():
                    return "No calculation name"
        else:
            if 'starting_struct' not in request.POST.keys() and 'starting_ensemble' not in request.POST.keys():
                return "No calculation name"
            else:
                name = "Followup"
    else:
        name = ""

    if 'calc_type' in request.POST.keys():
        try:
            step = BasicStep.objects.get(name=clean(request.POST['calc_type']))
        except BasicStep.DoesNotExist:
            return "No such procedure"
    else:
        return "No calculation type"

    if 'calc_project' in request.POST.keys():
        project = clean(request.POST['calc_project'])
        if project.strip() == '':
            return "No calculation project"
    else:
        return "No calculation project"

    if 'calc_charge' in request.POST.keys():
        charge = clean(request.POST['calc_charge'])
        if charge.strip() == '':
            return "No calculation charge"
    else:
        return "No calculation charge"

    if 'calc_multiplicity' in request.POST.keys():
        mult = clean(request.POST['calc_multiplicity'])
        if mult.strip() == '':
            return "No calculation multiplicity"
    else:
        return "No calculation multiplicity"

    if 'calc_solvent' in request.POST.keys():
        solvent = clean(request.POST['calc_solvent'])
        if solvent.strip() == '':
            return "No calculation solvent"
    else:
        return "No calculation solvent"

    if solvent != "Vacuum":
        if 'calc_solvation_model' in request.POST.keys():
            solvation_model = clean(request.POST['calc_solvation_model'])
            if solvation_model not in ['SMD', 'SMD18', 'PCM', 'CPCM', 'GBSA']:
                return "Invalid solvation model"
        else:
            return "No solvation model"
    else:
        solvation_model = ""

    if 'calc_software' in request.POST.keys():
        software = clean(request.POST['calc_software'])
        if software.strip() == '':
            return "No software chosen"
        if software not in BASICSTEP_TABLE.keys():
            return "Invalid software chosen"
    else:
        return "No software chosen"

    if 'calc_df' in request.POST.keys():
        df = clean(request.POST['calc_df'])
    else:
        df = ''

    if 'calc_custom_bs' in request.POST.keys():
        bs = clean(request.POST['calc_custom_bs'])
    else:
        bs = ''

    if software == 'ORCA' or software == 'Gaussian':
        if 'calc_theory_level' in request.POST.keys():
            theory = clean(request.POST['calc_theory_level'])
            if theory.strip() == '':
                return "No theory level chosen"
        else:
            return "No theory level chosen"

        if theory == "DFT":
            special_functional = False
            if 'pbeh3c' in request.POST.keys():
                field_pbeh3c = clean(request.POST['pbeh3c'])
                if field_pbeh3c == "on":
                    special_functional = True
                    functional = "PBEh-3c"
                    basis_set = ""

            if not special_functional:
                if 'calc_functional' in request.POST.keys():
                    functional = clean(request.POST['calc_functional'])
                    if functional.strip() == '':
                        return "No method"
                else:
                    return "No method"
                if functional not in SPECIAL_FUNCTIONALS:
                    if 'calc_basis_set' in request.POST.keys():
                        basis_set = clean(request.POST['calc_basis_set'])
                        if basis_set.strip() == '':
                            return "No basis set chosen"
                    else:
                        return "No basis set chosen"
                else:
                    basis_set = ""
        elif theory == "Semi-empirical":
            if 'calc_se_method' in request.POST.keys():
                functional = clean(request.POST['calc_se_method'])
                if functional.strip() == '':
                    return "No semi-empirical method chosen"
                basis_set = ''
            else:
                return "No semi-empirical method chosen"
        elif theory == "HF":
            special_functional = False
            if 'hf3c' in request.POST.keys():
                field_hf3c = clean(request.POST['hf3c'])
                if field_hf3c == "on":
                    special_functional = True
                    functional = "HF-3c"
                    basis_set = ""

            if not special_functional:
                functional = "HF"
                if 'calc_basis_set' in request.POST.keys():
                    basis_set = clean(request.POST['calc_basis_set'])
                    if basis_set.strip() == '':
                        return "No basis set chosen"
                else:
                    return "No basis set chosen"
        elif theory == "RI-MP2":
            if software != "ORCA":
                return "RI-MP2 is only available for ORCA"

            functional = "RI-MP2"
            if 'calc_basis_set' in request.POST.keys():
                basis_set = clean(request.POST['calc_basis_set'])
                if basis_set.strip() == '':
                    return "No basis set chosen"
            else:
                return "No basis set chosen"
        else:
            return "Invalid theory level"

    else:
        theory = "GFN2-xTB"
        if software == "xtb":
            functional = "GFN2-xTB"
            basis_set = "min"
            if step.name == "Conformational Search":
                if 'calc_conf_option' in request.POST.keys():
                    conf_option = clean(request.POST['calc_conf_option'])
                    if conf_option not in ['GFN2-xTB', 'GFN-FF', 'GFN2-xTB//GFN-FF']:
                        return "Error in the option for the conformational search"
                    functional = conf_option
        else:
            functional = ""
            basis_set = ""

    if 'calc_additional_command' in request.POST.keys():
        additional_command = clean(request.POST['calc_additional_command'])
    else:
        additional_command = ""

    if len(name) > 100:
        return "The chosen name is too long"

    if len(project) > 100:
        return "The chosen project name is too long"

    if charge not in ["-2", "-1", "0", "+1", "+2"]:
        return "Invalid charge (-2 to +2)"

    if mult not in ["1", "2", "3"]:
        return "Invalid multiplicity (1 to 3)"

    if solvent not in SOLVENT_TABLE.keys() and solvent != "Vacuum":
        return "Invalid solvent"

    if step.name not in BASICSTEP_TABLE[software].keys():
        return "Invalid calculation type"

    if 'calc_specifications' in request.POST.keys():
        specifications = clean(request.POST['calc_specifications'])

        def valid():
            for spec in specifications.split(';'):
                if spec.strip() == '':
                    continue
                key, option = spec.split('(')
                option = option.replace(')', '')
                if key not in SPECIFICATIONS[software].keys():
                    return False
                if option.find('=') != -1:
                    option, val = option.split('=')
                if option not in SPECIFICATIONS[software][key].keys():
                    return False
            return True

        if not valid():
            return "Invalid specifications"
    else:
        specifications = ""

    if project == "New Project":
        new_project_name = clean(request.POST['new_project_name'])
        try:
            project_obj = Project.objects.get(name=new_project_name, author=profile)
        except Project.DoesNotExist:
            project_obj = Project.objects.create(name=new_project_name, author=profile)
            profile.project_set.add(project_obj)
        else:
            print("Project with that name already exists")
    else:
        try:
            project_set = profile.project_set.filter(name=project)
        except Profile.DoesNotExist:
            return "No such project"

        if len(project_set) != 1:
            return "More than one project with the same name found!"
        else:
            project_obj = project_set[0]

    params = Parameters.objects.create(charge=charge, multiplicity=mult, solvent=solvent, method=functional, basis_set=basis_set, additional_command=additional_command, software=software, theory_level=theory, solvation_model=solvation_model, density_fitting=df, custom_basis_sets=bs, specifications=specifications)
    params.save()

    return params, project_obj, name, step

@login_required
def save_preset(request):
    ret = parse_parameters(request, name_required=False)

    if isinstance(ret, str):
        return HttpResponse(ret)
    params, project_obj, name, step = ret

    if 'preset_name' in request.POST.keys():
        preset_name = clean(request.POST['preset_name'])
    else:
        return HttpResponse("No preset name")

    preset = Preset.objects.create(name=preset_name, author=request.user.profile, params=params)
    preset.save()
    return HttpResponse("Preset created")

@login_required
def set_project_default(request):
    ret = parse_parameters(request, name_required=False)

    if isinstance(ret, str):
        return HttpResponse(ret)

    params, project_obj, name, step = ret

    preset = Preset.objects.create(name="{} Default".format(project_obj.name), author=request.user.profile, params=params)
    preset.save()
    project_obj.preset = preset
    project_obj.save()

    return HttpResponse("Default parameters updated")

def handle_file_upload(ff, params):
    s = Structure.objects.create()

    _params = Parameters.objects.create(software="Unknown", method="Unknown", basis_set="", solvation_model="", charge=params.charge, multiplicity=1)
    p = Property.objects.create(parent_structure=s, parameters=_params, geom=True)
    p.save()
    _params.save()

    drawing = False
    in_file = clean(ff.read().decode('utf-8'))
    filename, ext = ff.name.split('.')

    if ext == 'mol':
        s.mol_structure = in_file
        generate_xyz_structure(False, s)
    elif ext == 'xyz':
        s.xyz_structure = in_file
    elif ext == 'sdf':
        s.sdf_structure = in_file
        generate_xyz_structure(False, s)
    elif ext == 'mol2':
        s.mol2_structure = in_file
        generate_xyz_structure(False, s)
    elif ext == 'log':
        s.xyz_structure = get_Gaussian_xyz(in_file)
    else:
        return error(request, "Unknown file extension (Known formats: .mol, .mol2, .xyz, .sdf)")
    s.save()
    return s, filename

@login_required
def submit_calculation(request):
    ret = parse_parameters(request, name_required=True)

    if isinstance(ret, str):
        return error(request, ret)

    profile = request.user.profile

    params, project_obj, name, step = ret

    if 'calc_ressource' in request.POST.keys():
        ressource = clean(request.POST['calc_ressource'])
        if ressource.strip() == '':
            return error(request, "No computing resource chosen")
    else:
        return error(request, "No computing resource chosen")

    if ressource != "Local":
        try:
            access = ClusterAccess.objects.get(cluster_address=ressource, owner=profile)
        except ClusterAccess.DoesNotExist:
            return error(request, "No such cluster access")

        if access.owner != profile:
            return error(request, "You do not have the right to use this cluster access")
    else:
        if not profile.is_PI and profile.group == None:
            return error(request, "You have no computing resource")

    orders = []
    drawing = True

    if 'starting_ensemble' in request.POST.keys():
        obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)
        drawing = False
        start_id = int(clean(request.POST['starting_ensemble']))
        try:
            start_e = Ensemble.objects.get(pk=start_id)
        except Ensemble.DoesNotExist:
            return error(request, "No starting ensemble found")

        start_author = start_e.parent_molecule.project.author
        if not can_view_ensemble(start_e, profile):
            return error(request, "You do not have permission to access the starting calculation")
        obj.ensemble = start_e

        if 'calc_filter' in request.POST.keys():
            filter_type = clean(request.POST['calc_filter'])
            if filter_type == "None":
                pass
            elif filter_type == "By Relative Energy" or filter_type == "By Boltzmann Weight":
                if 'filter_value' in request.POST.keys():
                    try:
                        filter_value = float(clean(request.POST['filter_value']))
                    except ValueError:
                        return error(request, "Invalid filter value")
                else:
                    return error(request, "No filter value")

                if 'filter_parameters' in request.POST.keys():
                    try:
                        filter_parameters_id = int(clean(request.POST['filter_parameters']))
                    except ValueError:
                        return error(request, "Invalid filter parameters")

                    try:
                        filter_parameters = Parameters.objects.get(pk=filter_parameters_id)
                    except Parameters.DoesNotExist:
                        return error(request, "Invalid filter parameters")

                    if not can_view_parameters(filter_parameters, profile):
                        return error(request, "Invalid filter parameters")

                    filter = Filter.objects.create(type=filter_type, parameters=filter_parameters, value=filter_value)
                    obj.filter = filter
                else:
                    return error(request, "No filter parameters")

            else:
                return error(request, "Invalid filter type")
        orders.append(obj)

    elif 'starting_struct' in request.POST.keys():
        obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)
        drawing = False
        start_id = int(clean(request.POST['starting_struct']))
        try:
            start_s = Structure.objects.get(pk=start_id)
        except Structure.DoesNotExist:
            return error(request, "No starting ensemble found")
        if not can_view_structure(start_s, profile):
            return error(request, "You do not have permission to access the starting calculation")
        obj.structure = start_s
        orders.append(obj)
    elif 'starting_calc' in request.POST.keys():
        print("Starting calc")
        obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)
        if not 'starting_frame' in request.POST.keys():
            return error(request, "Missing starting frame number")
        c_id = int(clean(request.POST['starting_calc']))
        f_id = int(clean(request.POST['starting_frame']))
        try:
            start_c = Calculation.objects.get(pk=c_id)
        except Calculation.DoesNotExist:
            return error(request, "No starting ensemble found")
        if not can_view_calculation(start_c, profile):
            return error(request, "You do not have permission to access the starting calculation")
        obj.start_calc = start_c
        obj.start_calc_frame = f_id
        orders.append(obj)
    else:
        fingerprints = {}
        unique_fingerprints = []
        in_structs = []
        names = {}
        if len(request.FILES) > 0:
            for ind, ff in enumerate(request.FILES.getlist("file_structure")):
                ss = handle_file_upload(ff, params)
                if isinstance(ss, HttpResponse):
                    return ss
                s, filename = ss
                names[s.id] = filename
                fing = gen_fingerprint(s)

                if fing in fingerprints.keys():
                    fingerprints[fing].append(s.id)
                else:
                    fingerprints[fing] = [s.id]

                if fing not in unique_fingerprints:
                    unique_fingerprints.append(fing)

            for fing in unique_fingerprints:
                tmpname = names[fingerprints[fing][0]]
                obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)
                mol = Molecule.objects.create(name=tmpname, inchi=fing, project=project_obj)
                mol.save()
                e = Ensemble.objects.create(name="File Upload", parent_molecule=mol)
                for s_id in fingerprints[fing]:
                    s = Structure.objects.get(pk=s_id)
                    s.parent_ensemble = e
                    s.save()
                e.save()
                obj.ensemble = e
                obj.save()
                orders.append(obj)
        else:
            if 'structureB' in request.POST.keys():
                obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)
                drawing = True
                e = Ensemble.objects.create(name="Drawn Structure")
                obj.ensemble = e

                s = Structure.objects.create(parent_ensemble=e, number=1)
                params = Parameters.objects.create(software="Open Babel", method="Forcefield", basis_set="", solvation_model="", charge=params.charge, multiplicity="1")
                p = Property.objects.create(parent_structure=s, parameters=params, geom=True)
                p.save()
                params.save()

                mol = clean(request.POST['structureB'])
                s.mol_structure = mol
                orders.append(obj)
            else:
                return error(request, "No input structure")

        e.save()
        s.save()

    if step.name == "Minimum Energy Path":
        if len(orders) != 1:
            return error(request, 'Only one initial structure can be used')

        if len(request.FILES.getlist("aux_file_structure")) == 1:
            _aux_struct = handle_file_upload(request.FILES.getlist("aux_file_structure")[0], params)
            if isinstance(_aux_struct, HttpResponse):
                return _aux_struct
            aux_struct = _aux_struct[0]
        else:
            if 'aux_struct' not in request.POST.keys():
                return error(request, 'No valid auxiliary structure')
            try:
                aux_struct = Structure.objects.get(pk=int(clean(request.POST['aux_struct'])))
            except Structure.DoesNotExist:
                return error(request, 'No valid auxiliary structure')
            if not can_view_structure(aux_struct, profile):
                return error(request, 'No valid auxiliary structure')

        aux_struct.save()
        orders[0].aux_structure = aux_struct

    TYPE_LENGTH = {'Distance' : 2, 'Angle' : 3, 'Dihedral' : 4}
    constraints = ""
    if step.name == "Constrained Optimisation" and 'constraint_num' in request.POST.keys():
        for ind in range(1, int(request.POST['constraint_num'])+1):
            try:
                mode = clean(request.POST['constraint_mode_{}'.format(ind)])
            except MultiValueDictKeyError:
                pass
            else:
                _type = clean(request.POST['constraint_type_{}'.format(ind)])
                ids = []
                for i in range(1, TYPE_LENGTH[_type]+1):
                    id_txt = clean(request.POST['calc_constraint_{}_{}'.format(ind, i)])
                    if id_txt != "":
                        id = int(id_txt)
                        ids.append(id)

                ids = '_'.join([str(i) for i in ids])
                if mode == "Freeze":
                    constraints += "{}-{};".format(mode, ids)
                elif mode == "Scan":
                    obj.has_scan = True
                    begin = clean(request.POST['calc_scan_{}_1'.format(ind)])
                    end = float(clean(request.POST['calc_scan_{}_2'.format(ind)]))
                    steps = float(clean(request.POST['calc_scan_{}_3'.format(ind)]))
                    constraints += "{}_{}_{}_{}-{};".format(mode, begin, end, steps, ids)
                else:
                    return error(request, "Invalid constrained optimisation")
    obj.save()
    for o in orders:
        o.constraints = constraints

        if ressource != "Local":
            o.resource = access

        o.save()

    profile.save()

    if not 'test' in request.POST.keys():
        for o in orders:
            dispatcher.delay(drawing, o.id)

    return redirect("/calculations/")

def can_view_project(proj, profile):
    if proj.author == profile:
        return True
    else:
        if not profile_intersection(proj.author, profile):
            return False
        if proj.private and not profile.is_PI:
            return False
        return True

def can_view_molecule(mol, profile):
    return can_view_project(mol.project, profile)

def can_view_ensemble(e, profile):
    return can_view_molecule(e.parent_molecule, profile)

def can_view_structure(s, profile):
    return can_view_ensemble(s.parent_ensemble, profile)

def can_view_parameters(p, profile):
    prop = p.property_set.all()[0]
    return can_view_structure(prop.parent_structure, profile)

def can_view_preset(p, profile):
    return profile_intersection(p.author, profile)

def can_view_order(order, profile):
    if order.author == profile:
        return True
    elif profile_intersection(order.author, profile):
        if order.project.private and not profile.is_PI:
            return False
        return True

def can_view_calculation(calc, profile):
    return can_view_order(calc.order, profile)

def profile_intersection(profile1, profile2):
    if profile1 == profile2:
        return True
    if profile1.group != None:
        if profile2 in profile1.group.members.all():
            return True
        if profile2 == profile1.group.PI:
            return True
    else:
        return False

    if profile2.group == None:
        return False

    if profile1.researchgroup_PI != None:
        for group in profile1.researchgroup_PI:
            if profile2 in group.members.all():
                return True
    return False

@login_required
def project_list(request):
    if request.method == "POST":
        target_username = clean(request.POST['user'])
        try:
            target_profile = User.objects.get(username=target_username).profile
        except User.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if not profile_intersection(profile, target_profile):
            return HttpResponse(status=403)

        return render(request, 'frontend/project_list.html', {
                'profile': request.user.profile,
                'target_profile': target_profile,
            })

    else:
        return HttpResponse(status=403)

@login_required
def delete_project(request):
    if request.method == 'POST':
        if 'id' in request.POST.keys():
            proj_id = int(clean(request.POST['id']))
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Project.objects.get(pk=proj_id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.author != request.user.profile:
            return HttpResponse(status=403)

        del_project.delay(proj_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)

@login_required
def delete_molecule(request):
    if request.method == 'POST':
        if 'id' in request.POST.keys():
            mol_id = int(clean(request.POST['id']))
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Molecule.objects.get(pk=mol_id)
        except Molecule.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.project.author != request.user.profile:
            return HttpResponse(status=403)

        del_molecule.delay(mol_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)

@login_required
def delete_ensemble(request):
    if request.method == 'POST':
        if 'id' in request.POST.keys():
            ensemble_id = int(clean(request.POST['id']))
        else:
            return HttpResponse(status=403)

        try:
            to_delete = Ensemble.objects.get(pk=ensemble_id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        if to_delete.parent_molecule.project.author != request.user.profile:
            return HttpResponse(status=403)

        del_ensemble.delay(ensemble_id)
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=403)

@login_required
def add_clusteraccess(request):
    if request.method == 'POST':
        address = clean(request.POST['cluster_address'])
        username = clean(request.POST['cluster_username'])
        pal = int(clean(request.POST['cluster_cores']))
        memory = int(clean(request.POST['cluster_memory']))

        owner = request.user.profile

        try:
            existing_access = owner.clusteraccess_owner.get(cluster_address=address, cluster_username=username, owner=owner)
        except ClusterAccess.DoesNotExist:
            pass
        else:
            return HttpResponse(status=403)

        key_private_name = "{}_{}_{}".format(owner.username, username, ''.join(ch for ch in address if ch.isalnum()))
        key_public_name = key_private_name + '.pub'

        access = ClusterAccess.objects.create(cluster_address=address, cluster_username=username, private_key_path=key_private_name, public_key_path=key_public_name, owner=owner, pal=pal, memory=memory)
        access.save()
        owner.save()

        key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=2048)

        public_key = key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)

        pem = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
        with open(os.path.join(CALCUS_KEY_HOME, key_private_name), 'wb') as out:
            out.write(pem)

        with open(os.path.join(CALCUS_KEY_HOME, key_public_name), 'wb') as out:
            out.write(public_key)
            out.write(b' %b@calcUS' % bytes(owner.username, 'utf-8'))

        return HttpResponse(public_key.decode('utf-8'))
    else:
        return HttpResponse(status=403)

@login_required
def test_access(request):
    pk = clean(request.POST['access_id'])

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access.owner != profile:
        return HttpResponse(status=403)

    cmd = ClusterCommand.objects.create(issuer=profile)
    cmd.save()
    profile.save()

    with open(os.path.join(CALCUS_CLUSTER_HOME, "todo", str(cmd.id)), 'w') as out:
        out.write("access_test\n")
        out.write("{}\n".format(pk))

    return HttpResponse(cmd.id)

@login_required
def status_access(request):
    pk = clean(request.POST['access_id'])

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access.owner != profile and not profile.user.is_superuser:
        return HttpResponse(status=403)

    path = os.path.join(CALCUS_CLUSTER_HOME, "connections", pk)
    if os.path.isfile(path):
        with open(path) as f:
            lines = f.readlines()
            if lines[0].strip() == "Connected":
                t = int(lines[1].strip())
                dtime = time.time() - t
                if dtime < 6*60:
                    return HttpResponse("Connected {} seconds ago".format(int(dtime)))
                else:
                    return HttpResponse("Disconnected")
    else:
        return HttpResponse("Disconnected")

    return HttpResponse(cmd.id)

@login_required
def get_command_status(request):
    pk = request.POST['command_id']

    cmd = ClusterCommand.objects.get(pk=pk)

    profile = request.user.profile
    if cmd not in profile.clustercommand_set.all():
        return HttpResponse(status=403)

    expected_file = os.path.join(CALCUS_CLUSTER_HOME, "done", str(cmd.id))
    if not os.path.isfile(expected_file):
        return HttpResponse("Pending")
    else:
        with open(expected_file) as f:
            lines = f.readlines()
            return HttpResponse(lines[0].strip())

@login_required
def delete_access(request, pk):
    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access.owner != profile:
        return HttpResponse(status=403)

    access.delete()

    cmd = ClusterCommand.objects.create(issuer=profile)
    cmd.save()
    profile.save()

    with open(os.path.join(CALCUS_CLUSTER_HOME, "todo", str(cmd.id)), 'w') as out:
        out.write("delete_access\n")
        out.write("{}\n".format(pk))

    return HttpResponseRedirect("/profile")

@login_required
@superuser_required
def get_pi_requests(request):
    reqs = PIRequest.objects.count()
    return HttpResponse(str(reqs))

@login_required
@superuser_required
def get_pi_requests_table(request):

    reqs = PIRequest.objects.all()

    return render(request, 'frontend/pi_requests_table.html', {
        'profile': request.user.profile,
        'reqs': reqs,
        })

@login_required
@superuser_required
def server_summary(request):
    users = Profile.objects.all()
    groups = ResearchGroup.objects.all()
    accesses = ClusterAccess.objects.all()
    return render(request, 'frontend/server_summary.html', {
        'users': users,
        'groups': groups,
        'accesses': accesses,
        })

@login_required
def add_user(request):
    if request.method == "POST":
        profile = request.user.profile

        if not profile.is_PI:
            return HttpResponse(status=403)

        username = clean(request.POST['username'])
        group_id = int(clean(request.POST['group_id']))

        try:
            group = ResearchGroup.objects.get(pk=group_id)
        except ResearchGroup.DoesNotExist:
            return HttpResponse(status=403)

        if group.PI != profile:
            return HttpResponse(status=403)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse(status=403)

        if user.profile == profile:
            return HttpResponse(status=403)

        code = clean(request.POST['code'])

        if user.profile.code != code:
            return HttpResponse(status=403)

        group.members.add(user.profile)

        return HttpResponse(status=200)

    return HttpResponse(status=403)

@login_required
def remove_user(request):
    if request.method == "POST":
        profile = request.user.profile

        if not profile.is_PI:
            return HttpResponse(status=403)

        member_id = int(clean(request.POST['member_id']))
        group_id = int(clean(request.POST['group_id']))

        try:
            group = ResearchGroup.objects.get(pk=group_id)
        except ResearchGroup.DoesNotExist:
            return HttpResponse(status=403)

        if group.PI != profile:
            return HttpResponse(status=403)

        try:
            member = Profile.objects.get(pk=member_id)
        except Profile.DoesNotExist:
            return HttpResponse(status=403)

        if member == profile:
            return HttpResponse(status=403)

        if member not in group.members.all():
            return HttpResponse(status=403)

        group.members.remove(member)

        return HttpResponse(status=200)

    return HttpResponse(status=403)

@login_required
def profile_groups(request):
    return render(request, 'frontend/profile_groups.html', {
        'profile': request.user.profile,
        })

@login_required
@superuser_required
def accept_pi_request(request, pk):

    a = PIRequest.objects.get(pk=pk)

    try:
        group = ResearchGroup.objects.get(name=a.group_name)
    except ResearchGroup.DoesNotExist:
        pass
    else:
        print("Group with that name already exists")
        return HttpResponse(status=403)
    issuer = a.issuer
    group = ResearchGroup.objects.create(name=a.group_name, PI=issuer)
    group.save()
    issuer.is_PI = True
    issuer.save()

    a.delete()

    return HttpResponse(status=200)

@login_required
@superuser_required
def deny_pi_request(request, pk):

    a = PIRequest.objects.get(pk=pk)
    a.delete()

    return HttpResponse(status=200)

@login_required
@superuser_required
def manage_pi_requests(request):
    reqs = PIRequest.objects.all()

    return render(request, 'frontend/manage_pi_requests.html', {
        'profile': request.user.profile,
        'reqs': reqs,
        })

@login_required
def conformer_table(request, pk):
    id = str(pk)
    try:
        e = Ensemble.objects.get(pk=id)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=403)
    profile = request.user.profile

    if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/conformer_table.html', {
            'profile': request.user.profile,
            'ensemble': e,
        })

@login_required
def conformer_table_post(request):
    if request.method == 'POST':
        try:
            id = int(clean(request.POST['ensemble_id']))
            p_id = int(clean(request.POST['param_id']))
        except KeyError:
            return HttpResponse(status=204)

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)
        profile = request.user.profile

        if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
            return HttpResponse(status=403)
        try:
            p = Parameters.objects.get(pk=p_id)
        except Parameters.DoesNotExist:
            return HttpResponse(status=403)

        properties = []
        energies = []
        for s in e.structure_set.all():
            try:
                prop = s.properties.get(parameters=p)
            except Property.DoesNotExist:
                energies.append([''])
            else:
                energies.append(prop.energy)

        _rel_energies = e.relative_energies(p)
        pref_units = profile.pref_units
        if pref_units == 0:
            rel_energies = ["{:.2f}".format(float(i)*HARTREE_FVAL) if i != '' else '' for i in _rel_energies]
        elif pref_units == 1:
            rel_energies = ["{:.2f}".format(float(i)*HARTREE_TO_KCAL_F) if i != '' else '' for i in _rel_energies]
        elif pref_units == 2:
            rel_energies = ["{:.5f}".format(i) if i != '' else '' for i in _rel_energies]

        weights = e.weights(p)
        data = zip(e.structure_set.all(), energies, rel_energies, weights)
        data = sorted(data, key=lambda i: i[0].number)
        return render(request, 'frontend/conformer_table.html', {
                'profile': request.user.profile,
                'data': data,
            })
    else:
        return HttpResponse(status=403)

@login_required
def icon(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    icon_file = os.path.join(CALCUS_RESULTS_HOME, id, "icon.svg")

    if os.path.isfile(icon_file):
        with open(icon_file, 'rb') as f:
            response = HttpResponse(content=f)
            response['Content-Type'] = 'image/svg+xml'
            return response
    else:
        return HttpResponse(status=204)

@login_required
def uvvis(request, pk):
    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
        return HttpResponse(status=403)

    spectrum_file = os.path.join(CALCUS_RESULTS_HOME, str(pk), "uvvis.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@login_required
def get_calc_data(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    profile = request.user.profile

    if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    analyse_opt(calc.id)###

    multi_xyz = ""
    RMSD = "Frame,RMSD\n"
    for f in calc.calculationframe_set.all():
        multi_xyz += f.xyz_structure
        RMSD += "{},{}\n".format(f.number, f.RMSD)

    return HttpResponse(multi_xyz + ';' + RMSD)

@login_required
@throttle(zone='load_remote_log')
def get_calc_data_remote(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=403)

    profile = request.user.profile

    if calc.order.author != profile:
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    if calc.parameters.software == "Gaussian":
        try:
            os.remove(os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc.log"))
        except OSError:
            pass

        cmd = ClusterCommand.objects.create(issuer=profile)

        with open(os.path.join(CALCUS_CLUSTER_HOME, "todo", str(cmd.id)), 'w') as out:
            out.write("load_log\n{}\n{}\n".format(calc.id, calc.order.resource.id))

        ind = 0
        while not os.path.isfile(os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc.log")) and ind < 60:
            print("Waiting for log")
            time.sleep(1)
            ind += 1

        if not os.path.isfile(os.path.join(CALCUS_SCR_HOME, str(calc.id), "calc.log")):
            return HttpResponse(status=404)
    else:
        print("Not implemented")
        return HttpResponse(status=403)

    analyse_opt(calc.id)###

    multi_xyz = ""
    RMSD = "Frame,RMSD\n"
    for f in calc.calculationframe_set.all():
        multi_xyz += f.xyz_structure
        RMSD += "{},{}\n".format(f.number, f.RMSD)

    return HttpResponse(multi_xyz + ';' + RMSD)

def get_calc_frame(request, cid, fid):
    try:
        calc = Calculation.objects.get(pk=cid)
    except Calculation.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if not can_view_calculation(calc, profile):
        return HttpResponse(status=403)

    if calc.status == 0:
        return HttpResponse(status=204)

    #multi_xyz, RMSD = analyse_opt(calc.id)
    #s_xyz = multi_xyz.split('\n')
    #natoms = int(s_xyz[0])
    #xyz = '\n'.join(s_xyz[(fid-1)*(natoms+2):fid*(natoms+2)])
    #return HttpResponse(xyz)
    xyz = calc.calculationframe_set.get(number=fid).xyz_structure
    return HttpResponse(xyz)

@login_required
def get_cube(request):
    if request.method == 'POST':
        id = int(clean(request.POST['id']))
        orb = int(clean(request.POST['orb']))
        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
            return HttpResponse(status=403)

        if orb == 0:
            cube_file = "in-HOMO.cube"
        elif orb == 1:
            cube_file = "in-LUMO.cube"
        elif orb == 2:
            cube_file = "in-LUMOA.cube"
        elif orb == 3:
            cube_file = "in-LUMOB.cube"
        else:
            return HttpResponse(status=204)
        spectrum_file = os.path.join(CALCUS_RESULTS_HOME, str(id), cube_file)

        if os.path.isfile(spectrum_file):
            with open(spectrum_file, 'r') as f:
                lines = f.readlines()
            return HttpResponse(''.join(lines))
        else:
            return HttpResponse(status=204)
    return HttpResponse(status=204)

@login_required
def enso_nmr(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    if not calc.has_nmr:
        return HttpResponse(status=403)
    spectrum_file = os.path.join(CALCUS_RESULTS_HOME, id, "nmr.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)
@login_required
def nmr(request):
    if request.method != 'POST':
        return HttpResponse(status=404)

    if 'id' in request.POST.keys():
        try:
            e = Ensemble.objects.get(pk=int(clean(request.POST['id'])))
        except Ensemble.DoesNotExist:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)
    if 'p_id' in request.POST.keys():
        try:
            params = Parameters.objects.get(pk=int(clean(request.POST['p_id'])))
        except Parameters.DoesNotExist:
            return HttpResponse(status=404)
    else:
        return HttpResponse(status=404)

    if 'nucleus' in request.POST.keys():
        nucleus = clean(request.POST['nucleus'])
    else:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not profile_intersection(profile, e.parent_molecule.project.author):
        return HttpResponse(status=403)

    if not e.has_nmr(params):
        return HttpResponse(status=204)

    shifts = e.weighted_nmr_shifts(params)

    if nucleus == 'H':
        content = "Shift,Intensity\n-10,0\n0,0\n"
    else:
        content = "Shift,Intensity\n-200,0\n0,0\n"

    for shift in shifts:
        if shift[1] == nucleus:
            if len(shift) == 4:
                content += "{},{}\n".format(-(shift[3]-0.001), 0)
                content += "{},{}\n".format(-shift[3], 1)
                content += "{},{}\n".format(-(shift[3]+0.001), 0)

    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
    return response

@login_required
def ir_spectrum(request, pk):
    id = str(pk)
    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
        return HttpResponse(status=403)

    spectrum_file = os.path.join(CALCUS_RESULTS_HOME, id, "IR.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@login_required
def vib_table(request, pk):
    id = str(pk)
    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
        return HttpResponse(status=403)

    vib_file = os.path.join(CALCUS_RESULTS_HOME, id, "vibspectrum")
    orca_file = os.path.join(CALCUS_RESULTS_HOME, id, "orcaspectrum")

    if os.path.isfile(vib_file):
        with open(vib_file) as f:
            lines = f.readlines()

        vibs = []
        for line in lines:
            if len(line.split()) > 4 and line[0] != '#':
                sline = line.split()
                try:
                    a = float(sline[1])
                    if a == 0.:
                        continue
                except ValueError:
                    pass
                vib = float(line[20:33].strip())
                vibs.append(vib)

        formatted_vibs = []

        for ind in range(math.ceil(len(vibs)/3)):
            formatted_vibs.append([
                [vibs[3*ind], 3*ind],
                [vibs[3*ind+1] if 3*ind+1 < len(vibs) else '', 3*ind+1],
                [vibs[3*ind+2] if 3*ind+2 < len(vibs) else '', 3*ind+2]
                    ])

        return render(request, 'frontend/vib_table.html', {
                    'profile': request.user.profile,
                    'vibs': formatted_vibs
                })
    elif os.path.isfile(orca_file):
        with open(orca_file) as f:
            lines = f.readlines()

        vibs = []
        for line in lines:
            vibs.append(line.strip())

        formatted_vibs = []

        for ind in range(math.ceil(len(vibs)/3)):
            formatted_vibs.append([
                [vibs[3*ind], 3*ind],
                [vibs[3*ind+1] if 3*ind+1 < len(vibs) else '', 3*ind+1],
                [vibs[3*ind+2] if 3*ind+2 < len(vibs) else '', 3*ind+2]
                    ])

        return render(request, 'frontend/vib_table.html', {
                    'profile': request.user.profile,
                    'vibs': formatted_vibs
                })

    else:
        return HttpResponse(status=204)

@login_required
def apply_pi(request):
    if request.method == 'POST':
        profile = request.user.profile

        if profile.is_PI:
            return render(request, 'frontend/apply_pi.html', {
                'profile': request.user.profile,
                'message': "You are already a PI!",
            })
        group_name = clean(request.POST['group_name'])
        req = PIRequest.objects.create(issuer=profile, group_name=group_name, date_issued=timezone.now())
        return render(request, 'frontend/apply_pi.html', {
            'profile': request.user.profile,
            'message': "Your request has been received.",
        })
    else:
        return HttpResponse(status=403)

@login_required
def info_table(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/info_table.html', {
            'profile': request.user.profile,
            'calculation': calc,
        })

@login_required
def status(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/status.html', {
            'calculation': calc,
        })

@login_required
def next_step(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/next_step.html', {
            'calculation': calc,
        })


@login_required
def download_structures(request, ee):
    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_ensemble(e, profile):
        return HttpResponse(status=404)

    structs = ""
    for s in e.structure_set.all():
        if s.xyz_structure == "":
            structs += "1\nMissing Structure\nC 0 0 0"
            print("Missing structure! ({}, {})".format(profile.username, ee))
        structs += s.xyz_structure

    response = HttpResponse(structs)
    response['Content-Type'] = 'text/plain'
    response['Content-Disposition'] = 'attachment; filename={}.xyz'.format(ee)
    return response

@login_required
def download_structure(request, ee, num):
    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_ensemble(e, profile):
        return HttpResponse(status=404)

    try:
        s = e.structure_set.get(number=num)
    except Structure.DoesNotExist:
        return HttpResponse(status=404)

    response = HttpResponse(s.xyz_structure)
    response['Content-Type'] = 'text/plain'
    response['Content-Disposition'] = 'attachment; filename={}_conf{}.xyz'.format(ee, num)
    return response

def gen_3D(request):
    if request.method == 'POST':
        mol = request.POST['mol']
        clean_mol = clean(mol)

        t = time.time()
        with open("/tmp/{}.mol".format(t), 'w') as out:
            out.write(clean_mol)

        system("babel -imol /tmp/{}.mol -oxyz /tmp/{}.xyz -h --gen3D".format(t, t), force_local=True)
        with open("/tmp/{}.xyz".format(t)) as f:
            lines = f.readlines()
        if ''.join(lines).strip() == '':
            return HttpResponse(status=404)

        return HttpResponse(lines)
    return HttpResponse(status=403)

@login_required
def rename_molecule(request):
    if request.method == 'POST':
        id = int(clean(request.POST['id']))

        try:
            mol = Molecule.objects.get(pk=id)
        except Molecule.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if mol.project.author != profile:
            return HttpResponse(status=403)

        if 'new_name' in request.POST.keys():
            name = clean(request.POST['new_name'])

        mol.name = name
        mol.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)

@login_required
def rename_project(request):
    if request.method == 'POST':
        id = int(clean(request.POST['id']))

        try:
            proj = Project.objects.get(pk=id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if proj.author != profile:
            return HttpResponse(status=403)

        if 'new_name' in request.POST.keys():
            name = clean(request.POST['new_name'])

        proj.name = name
        proj.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)

@login_required
def toggle_private(request):
    if request.method == 'POST':
        id = int(clean(request.POST['id']))

        try:
            proj = Project.objects.get(pk=id)
        except Project.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if proj.author != profile:
            return HttpResponse(status=403)

        if 'val' in request.POST.keys():
            try:
                val = int(clean(request.POST['val']))
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
    if request.method == 'POST':
        id = int(clean(request.POST['id']))

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if e.parent_molecule.project.author != profile:
            return HttpResponse(status=403)

        if 'val' in request.POST.keys():
            try:
                val = int(clean(request.POST['val']))
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
    if request.method == 'POST':
        id = int(clean(request.POST['id']))

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if e.parent_molecule.project.author != profile:
            return HttpResponse(status=403)

        if 'new_name' in request.POST.keys():
            name = clean(request.POST['new_name'])

        e.name = name
        e.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)

@login_required
def get_structure(request):
    if request.method == 'POST':
        try:
            id = int(clean(request.POST['id']))
        except ValueError:
            return HttpResponse(status=404)

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if not can_view_ensemble(e, profile):
            return HttpResponse(status=403)

        structs = e.structure_set.all()

        if len(structs) == 0:
            return HttpResponse(status=204)

        if 'num' in request.POST.keys():
            num = int(clean(request.POST['num']))
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
    if request.method == 'POST':
        url = clean(request.POST['id'])
        try:
            id = int(url.split('/')[-1])
        except ValueError:
            return HttpResponse(status=404)

        try:
            calc = Calculation.objects.get(pk=id)
        except Calculation.DoesNotExist:
            return HttpResponse(status=404)

        profile = request.user.profile

        if not can_view_calculation(calc, profile):
            return HttpResponse(status=403)

        num = request.POST['num']
        expected_file = os.path.join(CALCUS_RESULTS_HOME, str(id), "freq_{}.xyz".format(num))
        if os.path.isfile(expected_file):
            with open(expected_file) as f:
                lines = f.readlines()

            return HttpResponse(''.join(lines))
        else:
            return HttpResponse(status=204)

@login_required
def get_scan_animation(request):
    if request.method == 'POST':
        url = clean(request.POST['id'])
        id = int(url.split('/')[-1])

        try:
            calc = Calculation.objects.get(pk=id)
        except Calculation.DoesNotExist:
            return HttpResponse(status=404)

        profile = request.user.profile

        if not can_view_calculation(calc, profile):
            return HttpResponse(status=403)

        type = calc.type

        if type != 5:
            return HttpResponse(status=403)

        expected_file = os.path.join(CALCUS_RESULTS_HOME, id, "xtbscan.xyz")
        if os.path.isfile(expected_file):
            with open(expected_file) as f:
                lines = f.readlines()

            inds = []
            num_atoms = lines[0]

            for ind, line in enumerate(lines):
                if line == num_atoms:
                    inds.append(ind)

            inds.append(len(lines)-1)
            xyz_files = []
            for ind, _ in enumerate(inds[1:]):
                xyz = ""
                for _ind in range(inds[ind-1], inds[ind]):
                    if lines[_ind].strip() != '':
                        xyz += lines[_ind].strip() + '\\n'
                xyz_files.append(xyz)
            return render(request, 'frontend/scan_animation.html', {
                'xyz_files': xyz_files[1:]
                })
        else:
            return HttpResponse(status=204)

@login_required
def get_details_sections(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_calculation(calc, profile):
        return HttpResponse(status=403)

    return render(request, 'frontend/details_sections.html', {
            'calculation': calc
        })

@login_required
def download_log(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_calculation(calc, profile):
        return HttpResponse(status=403)

    if calc.status == 2 or calc.status == 3:
        dir = os.path.join(CALCUS_RESULTS_HOME, str(pk))
    elif calc.status == 1:
        dir = os.path.join(CALCUS_SCR_HOME, str(pk))
    elif calc.status == 0:
        return HttpResponse(status=204)

    logs = glob.glob(dir + '/*.out')
    logs += glob.glob(dir + '/*.log')

    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zip:
        for f in logs:
            zip.write(f, "{}_".format(calc.id) + basename(f))

    response = HttpResponse(mem.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="calc_{}.zip"'.format(calc.id)
    return response

@login_required
def log(request, pk):
    LOG_HTML = """
    <label class="label">{}</label>
    <textarea class="textarea" style="height: 300px;" readonly>
    {}
    </textarea>
    """

    response = ''

    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_calculation(calc, profile):
        return HttpResponse(status=403)

    if calc.status == 2 or calc.status == 3:
        dir = os.path.join(CALCUS_RESULTS_HOME, str(pk))
    elif calc.status == 1:
        dir = os.path.join(CALCUS_SCR_HOME, str(pk))
    elif calc.status == 0:
        return HttpResponse(status=204)

    for out in glob.glob(dir + '/*.out'):
        out_name = out.split('/')[-1]
        with open(out) as f:
            lines = f.readlines()
        response += LOG_HTML.format(out_name, ''.join(lines))

    for log in glob.glob(dir + '/*.log'):
        log_name = log.split('/')[-1]
        with open(log) as f:
            lines = f.readlines()
        response += LOG_HTML.format(log_name, ''.join(lines))

    return HttpResponse(response)

@login_required
def manage_access(request, pk):
    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access.owner != profile:
        return HttpResponse(status=403)

    return render(request, 'frontend/manage_access.html', {
            'profile': request.user.profile,
            'access': access,
        })

@login_required
def owned_accesses(request):
    return render(request, 'frontend/owned_accesses.html', {
            'profile': request.user.profile,
        })

@login_required
def profile(request):
    return render(request, 'frontend/profile.html', {
            'profile': request.user.profile,
        })

@login_required
def update_preferences(request):
    if request.method == 'POST':
        profile = request.user.profile

        if 'pref_units' not in request.POST.keys():
            return HttpResponse(status=204)

        units = clean(request.POST['pref_units'])
        try:
            unit_code = profile.INV_UNITS[units]
        except KeyError:
            return HttpResponse(status=204)

        profile.pref_units = unit_code
        profile.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=404)

@login_required
def launch(request):
    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'procs': BasicStep.objects.all(),
        })

@login_required
def launch_pk(request, pk):

    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if not can_view_ensemble(e, profile):
        return HttpResponse(status=403)

    init_params = e.structure_set.all()[0].properties.all()[0].parameters

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'ensemble': e,
            'procs': BasicStep.objects.all(),
            'init_params_id': init_params.id,
        })

@login_required
def launch_frame(request, cid, fid):

    try:
        calc = Calculation.objects.get(pk=cid)
    except Calculation.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if not can_view_calculation(calc, profile):
        return HttpResponse(status=403)

    init_params = calc.order.parameters

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'calc': calc,
            'frame_id': fid,
            'procs': BasicStep.objects.all(),
            'init_params_id': init_params.id,
        })


@login_required
def launch_structure_pk(request, ee, pk):

    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if not can_view_ensemble(e, profile):
        return HttpResponse(status=403)

    try:
        s = e.structure_set.get(number=pk)
    except Structure.DoesNotExist:
        return redirect('/home/')

    init_params = s.properties.all()[0].parameters
    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'structure': s,
            'procs': BasicStep.objects.all(),
            'init_params': init_params,
        })

@login_required
def launch_project(request, pk):
    try:
        proj = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if not can_view_project(proj, profile):
        return HttpResponse(status=403)

    if proj.preset is not None:
        init_params_id = proj.preset.id

        return render(request, 'frontend/launch.html', {
                'proj': proj,
                'profile': request.user.profile,
                'procs': BasicStep.objects.all(),
                'init_params_id': init_params_id,
            })
    else:
        return render(request, 'frontend/launch.html', {
                'proj': proj,
                'profile': request.user.profile,
                'procs': BasicStep.objects.all(),
            })

@login_required
def delete_preset(request, pk):
    try:
        p = Preset.objects.get(pk=pk)
    except Preset.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_preset(p, profile):
        return HttpResponse(status=403)

    p.delete()
    return HttpResponse("Preset deleted")

@login_required
def launch_presets(request):
    profile = request.user.profile

    presets = profile.preset_set.all()
    return render(request, 'frontend/launch_presets.html', { 'presets': presets })

@login_required
def load_preset(request, pk):
    try:
        p = Preset.objects.get(pk=pk)
    except Preset.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_preset(p, profile):
        return HttpResponse(status=403)

    return render(request, 'frontend/load_params.js', {
            'params': p.params,
        })

@login_required
def load_params_ensemble(request, pk):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_ensemble(e, profile):
        return HttpResponse(status=403)

    params = e.structure_set.all()[0].properties.all()[0].parameters

    return render(request, 'frontend/load_params.js', {
            'params': params,
        })

@login_required
def load_params_structure(request, pk):
    try:
        s = Structure.objects.get(pk=pk)
    except Structure.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile

    if not can_view_structure(s, profile):
        return HttpResponse(status=403)

    params = s.properties.all()[0].parameters

    return render(request, 'frontend/load_params.js', {
            'params': params,
        })

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
        self.data = None

def get_csv(proj, profile, scope="all", details="full"):
    pref_units = profile.pref_units
    units = profile.pref_units_name

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
    csv = ""

    molecules = list(proj.molecule_set.all())
    for mol in molecules:
        ensembles = mol.ensemble_set.all()
        for e in ensembles:
            if scope == "flagged":
                if not e.flagged:
                    continue

            if details == "full":
                summ = e.ensemble_summary
            else:
                summ = e.ensemble_short_summary

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

    if details == 'full':
        csv += "Parameters,Molecule,Ensemble,Structure\n"
        for p_name in summary.keys():
            p = summary[p_name]
            csv += "{},\n".format(p_name)
            for mol in p.molecules.values():
                csv += ",{},\n".format(mol.name)
                csv += ",,,Number,Degeneracy,Energy,Relative Energy,Weight,Free Energy,\n"
                for e in mol.ensembles.values():
                    csv += ",,{},\n".format(e.name)
                    nums, degens, energies, free_energies, rel_energies, weights, w_e, w_f_e = e.data
                    for n, d, en, f_en, r_el, w in zip(nums, degens, energies, free_energies, rel_energies, weights):
                        csv += structure_str.format(n, d, en*CONVERSION, r_el*CONVERSION, w, f_en*CONVERSION)
    csv += "\n\n"
    csv += "SUMMARY\n"
    csv += "Method,Molecule,Ensemble,Weighted Energy,Weighted Free Energy,\n"
    for p_name in summary.keys():
        p = summary[p_name]
        csv += "{},\n".format(p_name)
        for mol in p.molecules.values():
            csv += ",{},\n".format(mol.name)
            for e in mol.ensembles.values():
                if details == "full":
                    arr_ind = 6
                else:
                    arr_ind = 0

                _w_e = e.data[arr_ind]
                if _w_e != '-':
                    w_e = ensemble_str.format(_w_e*CONVERSION)

                _w_f_e = e.data[arr_ind+1]
                if _w_f_e != '-':
                    w_f_e = ensemble_str.format(_w_f_e*CONVERSION)

                csv += ",,{},{},{}\n".format(e.name, w_e, w_f_e)

    return csv

def download_project_csv(proj, profile, scope, details):

    csv = get_csv(proj, profile, scope, details)

    proj_name = proj.name.replace(' ', '_')
    response = HttpResponse(csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}.csv'.format(proj_name)
    return response

@login_required
def cancel_calc(request):

    if request.method != "POST":
        return HttpResponse(status=403)

    profile = request.user.profile

    if 'id' in request.POST.keys():
        try:
            id = int(clean(request.POST['id']))
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if profile != calc.order.author:
        return HttpResponse(status=403)

    if calc.status == 0 or calc.status == 1:
        if is_test:
            cancel(calc.id)
        else:
            cancel.delay(calc.id)

    return HttpResponse(status=200)

def download_project_logs(proj, profile, scope, details):

    tmp_dir = "/tmp/{}_{}_{}".format(profile.username, proj.author.username, time.time())
    os.mkdir(tmp_dir)
    for mol in sorted(proj.molecule_set.all(), key=lambda l: l.name):
        for e in mol.ensemble_set.all():
            if scope == 'flagged' and not e.flagged:
                continue
            e_dir = os.path.join(tmp_dir, str(e.id) + '_' + e.name.replace(' ', '_'))
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
                        log_name = e.name + '_' + calc.parameters.file_name + '_conf{}'.format(s.number)
                    elif details == "full":
                        log_name = e.name + '_' + calc.step.name + '_' + calc.parameters.file_name + '_conf{}'.format(s.number)

                    log_name = log_name.replace(' ', '_')
                    try:
                        copyfile(os.path.join(CALCUS_RESULTS_HOME, str(calc.id), "calc.out"), os.path.join(e_dir, log_name + '.log'))
                    except FileNotFoundError:
                        print("Calculation not found: {}".format(calc.id))
                    if calc.parameters.software == 'xtb':#xtb logs don't contain the structure
                        with open(os.path.join(e_dir, log_name + '.xyz'), 'w') as out:
                            out.write(s.xyz_structure)

    for d in glob.glob("{}/*/".format(tmp_dir)):
        if len(os.listdir(d)) == 0:
            os.rmdir(d)

    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zip:
        for d in glob.glob("{}/*/".format(tmp_dir)):
            for f in glob.glob("{}*".format(d)):
                zip.write(f, os.path.join(proj.name.replace(' ', '_'), *f.split('/')[3:]))

    response = HttpResponse(mem.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="{}_logs.zip"'.format(proj.name.replace(' ', '_'))
    return response

@login_required
def download_project_post(request):
    if 'id' in request.POST.keys():
        try:
            id = int(clean(request.POST['id']))
        except ValueError:
            return error(request, "Invalid project")
    else:
        return HttpResponse(status=403)

    if 'data' in request.POST.keys():
        data = clean(request.POST['data'])
        if data not in ['summary', 'logs']:
            return error(request, "Invalid data type requested")
    else:
        return error(request, "No data type requested")

    if 'scope' in request.POST.keys():
        scope = clean(request.POST['scope'])
        if scope not in ['all', 'flagged']:
            return error(request, "Invalid scope")
    else:
        return error(request, "No scope given")

    if 'details' in request.POST.keys():
        details = clean(request.POST['details'])
        if data == 'summary' and details not in ['full', 'summary']:
            return error(request, "Invalid details level")
        if data == 'logs' and details not in ['full', 'freq']:
            return error(request, "Invalid details level")
    else:
        return error(request, "No details level given")

    try:
        proj = Project.objects.get(pk=id)
    except Project.DoesNotExist:
        return error(request, "Invalid project")

    profile = request.user.profile

    if not profile_intersection(proj.author, profile):
        return HttpResponseRedirect("/home/")

    if data == 'summary':
        return download_project_csv(proj, profile, scope, details)
    elif data == 'logs':
        return download_project_logs(proj, profile, scope, details)

@login_required
def download_project(request, pk):
    try:
        proj = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return HttpResponse(status=403)

    profile = request.user.profile

    if not profile_intersection(proj.author, profile):
        return HttpResponseRedirect("/home/")

    return render(request, 'frontend/download_project.html', {'proj': proj})


@login_required
def restart_calc(request):
    if request.method != "POST":
        return HttpResponse(status=403)

    profile = request.user.profile

    if 'id' in request.POST.keys():
        try:
            id = int(clean(request.POST['id']))
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if profile != calc.order.author:
        return HttpResponse(status=403)

    if calc.status != 3:
        return HttpResponse(status=204)

    scr_dir = os.path.join(CALCUS_SCR_HOME, str(calc.id))
    res_dir = os.path.join(CALCUS_RESULTS_HOME, str(calc.id))

    try:
        rmtree(scr_dir)
    except FileNotFoundError:
        pass
    try:
        rmtree(res_dir)
    except FileNotFoundError:
        pass

    calc.status = 0
    calc.save()

    if calc.local:
        t = run_calc.s(calc.id).set(queue='comp')
        res = t.apply_async()
        calc.task_id = res
        calc.save()
    else:
        cmd = ClusterCommand.objects.create(issuer=calc.order.author)
        cmd.save()
        with open(os.path.join(CALCUS_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
            out.write("launch\n")
            out.write("{}\n".format(calc.id))
            out.write("{}\n".format(calc.order.resource.id))

    return HttpResponse(status=200)

@login_required
def refetch_calc(request):
    if request.method != "POST":
        return HttpResponse(status=403)

    profile = request.user.profile

    if 'id' in request.POST.keys():
        try:
            id = int(clean(request.POST['id']))
        except ValueError:
            return HttpResponse(status=404)

    try:
        calc = Calculation.objects.get(pk=id)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    if profile != calc.order.author:
        return HttpResponse(status=403)

    if calc.status != 3:
        return HttpResponse(status=204)

    if calc.local:
        return HttpResponse(status=204)

    calc.status = 1
    calc.save()

    cmd = ClusterCommand.objects.create(issuer=calc.order.author)
    cmd.save()
    with open(os.path.join(CALCUS_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
        out.write("launch\n")
        out.write("{}\n".format(calc.id))
        out.write("{}\n".format(calc.order.resource.id))

    return HttpResponse(status=200)

@login_required
def ensemble_map(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile
    if not can_view_molecule(mol, profile):
        return redirect('/home/')
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
        if e.flagged:
            border_text = """, "bcolor": "black", "bwidth": 2"""
        else:
            border_text = ""
        nodes += """{{ "data": {{"id": "{}", "name": "{}", "href": "/ensemble/{}", "color": "{}"{}}} }},""".format(e.id, e.name, e.id, e.get_node_color, border_text)
    nodes = nodes[:-1]

    edges = ""
    for e in mol.ensemble_set.all():
        if e.origin != None:
            edges += """{{ "data": {{"source": "{}", "target": "{}"}} }},""".format(e.origin.id, e.id)
    edges = edges[:-1]
    response = HttpResponse(json.format(nodes, edges), content_type='text/json')

    return HttpResponse(response)

@login_required
def analyse(request, project_id):
    profile = request.user.profile

    try:
        proj = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return HttpResponse(status=403)

    if not can_view_project(proj, profile):
        return HttpResponse(status=403)

    csv = get_csv(proj, profile)
    js_csv = []
    for ind1, line in enumerate(csv.split('\n')):
        for ind2, el in enumerate(line.split(',')):
            js_csv.append([el, ind1, ind2])
    l = len(csv.split('\n')) + 5
    return render(request, 'frontend/analyse.html', {'data': js_csv, 'len': l, 'proj': proj})

@login_required
def calculationorder(request, pk):
    try:
        order = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile
    if not can_view_order(order, profile):
        return HttpResponse(status=404)

    return render(request, 'frontend/calculationorder.html', {'order': order})

@login_required
def calculation(request, pk):
    try:
        calc = Calculation.objects.get(pk=pk)
    except Calculation.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile
    if not can_view_calculation(calc, profile):
        return HttpResponse(status=404)

    return render(request, 'frontend/calculation.html', {'calc': calc})

@login_required
def see(request, pk):
    try:
        order = CalculationOrder.objects.get(pk=pk)
    except CalculationOrder.DoesNotExist:
        return HttpResponse(status=404)

    profile = request.user.profile
    if profile != order.author:
        return HttpResponse(status=404)

    order.see()

    return HttpResponse(status=200)

def handler404(request, *args, **argv):
    return render(request, 'error/404.html', {
            })

def handler403(request, *args, **argv):
    return render(request, 'error/403.html', {
            })

def handler400(request, *args, **argv):
    return render(request, 'error/400.html', {
            })

def handler500(request, *args, **argv):
    return render(request, 'error/500.html', {
            })
