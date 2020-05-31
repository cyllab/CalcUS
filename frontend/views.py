import os
import shutil
import glob
import random
import string
import bleach
import math
import time

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
from .models import Calculation, Profile, Project, ClusterAccess, ClusterCommand, Example, PIRequest, ResearchGroup, Parameters, Structure, Ensemble, Procedure, Step, BasicStep, CalculationOrder, Molecule, Property, Filter, Exercise, CompletedExercise
from .tasks import dispatcher, del_project, del_molecule, del_ensemble, BASICSTEP_TABLE, SPECIAL_FUNCTIONALS, cancel
from .decorators import superuser_required
from .tasks import system
from .constants import *

from shutil import copyfile


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
            #if unseen == "true":
            #    hits = hits.filter(unseen=True)
            return sorted(hits, key=lambda d: d.date, reverse=True)

        else:
            return []

def home(request):
    return render(request, 'frontend/home.html')

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
        })

@login_required
def projects_username(request, username):
    target_username = clean(username)

    try:
        target_profile = User.objects.get(username=target_username).profile
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if profile_intersection(request.user.profile, target_profile):
        return render(request, 'frontend/projects.html', {
                    'profile': request.user.profile,
                    'target_profile': target_profile,
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

        if profile_intersection(request.user.profile, target_profile):
            return render(request, 'frontend/project_list.html', {'projects' : target_profile.project_set.all()})

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
                        <a href="/download_project_csv/{}"><i class="fas fa-download"></i></a>
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
def get_theory_details(request):
    if request.method == 'POST':
        if 'theory' in request.POST.keys():
            theory = clean(request.POST['theory'])
        else:
            return HttpResponse(status=403)
        if 'software' in request.POST.keys():
            software = clean(request.POST['software'])
        else:
            return HttpResponse(status=403)
        return render(request, 'frontend/launch_theory_options.html', {
                'profile': request.user.profile,
                'software': software,
                'theory': theory,
            })
    else:
        return HttpResponse(status=403)

@login_required
def project_details(request, username, proj):
    target_project = clean(proj)
    target_username = clean(username)

    try:
        target_profile = User.objects.get(username=target_username).profile
    except User.DoesNotExist:
        return render(request, 'frontend/error.html', {'error_message': 'Invalid user'})

    if profile_intersection(request.user.profile, target_profile):
        try:
            project = target_profile.project_set.get(name=target_project)
        except Project.DoesNotExist:
                return render(request, 'frontend/error.html', {'error_message': 'Invalid project'})
        return render(request, 'frontend/project_details.html', {
        'molecules': project.molecule_set.all(),
        'project': project,
        })


    else:
        return render(request, 'frontend/error.html', {'error_message': 'Invalid user'})


def clean(txt):
    return bleach.clean(txt)

@login_required
def molecule(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect('/home/')

    if not profile_intersection(request.user.profile, mol.project.author):
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

    if not profile_intersection(request.user.profile, mol.project.author):
        return redirect('/home/')

    return render(request, 'frontend/ensemble_table_body.html', {'profile': request.user.profile,
        'molecule': mol})


@login_required
def ensemble(request, pk):
    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    if not profile_intersection(request.user.profile, e.parent_molecule.project.author):
        return redirect('/home/')

    return render(request, 'frontend/ensemble.html', {'profile': request.user.profile,
        'ensemble': e})

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

        if not profile_intersection(request.user.profile, e.parent_molecule.project.author):
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

        if not profile_intersection(request.user.profile, e.parent_molecule.project.author):
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

    if not profile_intersection(request.user.profile, calc.author):
        return redirect('/home/')

    return render(request, 'frontend/details.html', {'profile': request.user.profile,
        'calculation': calc})

class ExamplesView(generic.ListView):
    model = Example
    template_name = 'examples/index.html'
    context_object_name = 'examples'
    paginate_by = '5'

    def get_queryset(self):
        return Example.objects.all()

class ExerciseView(generic.ListView):
    model = Exercise
    template_name = 'exercises/index.html'
    context_object_name = 'exercises'
    paginate_by = '10'

    def get_queryset(self):
        return Exercise.objects.all()

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


@login_required
def submit_calculation(request):
    if 'calc_name' in request.POST.keys():
        name = clean(request.POST['calc_name'])
        if name.strip() == '':
            if 'starting_struct' not in request.POST.keys() and 'starting_ensemble' not in request.POST.keys():
                return error(request, "No calculation name")
    else:
        if 'starting_struct' not in request.POST.keys() and 'starting_ensemble' not in request.POST.keys():
            return error(request, "No calculation name")
        else:
            name = "Followup"

    if 'calc_type' in request.POST.keys():
        try:
            step = BasicStep.objects.get(name=clean(request.POST['calc_type']))
        except BasicStep.DoesNotExist:
            return error(request, "No such procedure")
    else:
        return error(request, "No calculation type")

    if 'calc_project' in request.POST.keys():
        project = clean(request.POST['calc_project'])
        if project.strip() == '':
            return error(request, "No calculation project")
    else:
        return error(request, "No calculation project")

    if 'calc_charge' in request.POST.keys():
        charge = clean(request.POST['calc_charge'])
        if charge.strip() == '':
            return error(request, "No calculation charge")
    else:
        return error(request, "No calculation charge")

    if 'calc_solvent' in request.POST.keys():
        solvent = clean(request.POST['calc_solvent'])
        if solvent.strip() == '':
            return error(request, "No calculation solvent")
    else:
        return error(request, "No calculation solvent")

    if 'calc_ressource' in request.POST.keys():
        ressource = clean(request.POST['calc_ressource'])
        if ressource.strip() == '':
            return error(request, "No computing resource chosen")
    else:
        return error(request, "No computing resource chosen")

    if 'calc_software' in request.POST.keys():
        software = clean(request.POST['calc_software'])
        if software.strip() == '':
            return error(request, "No software chosen")
        if software not in BASICSTEP_TABLE.keys():
            return error(request, "Invalid software chosen")
    else:
        return error(request, "No software chosen")


    if software == 'ORCA' or software == 'Gaussian':
        if 'calc_theory_level' in request.POST.keys():
            theory = clean(request.POST['calc_theory_level'])
            if theory.strip() == '':
                return error(request, "No theory level chosen")
        else:
            return error(request, "No theory level chosen")

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
                        return error(request, "No method")
                else:
                    return error(request, "No method")
                if functional not in SPECIAL_FUNCTIONALS:
                    if 'calc_basis_set' in request.POST.keys():
                        basis_set = clean(request.POST['calc_basis_set'])
                        if basis_set.strip() == '':
                            return error(request, "No basis set chosen")
                    else:
                        return error(request, "No basis set chosen")
                else:
                    basis_set = ""
        elif theory == "Semi-empirical":
            if 'calc_se_method' in request.POST.keys():
                functional = clean(request.POST['calc_se_method'])
                if functional.strip() == '':
                    return error(request, "No semi-empirical method chosen")
                basis_set = ''
            else:
                return error(request, "No semi-empirical method chosen")
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
                        return error(request, "No basis set chosen")
                else:
                    return error(request, "No basis set chosen")
        elif theory == "RI-MP2":
            functional = "RI-MP2"
            if 'calc_basis_set' in request.POST.keys():
                basis_set = clean(request.POST['calc_basis_set'])
                if basis_set.strip() == '':
                    return error(request, "No basis set chosen")
            else:
                return error(request, "No basis set chosen")
        else:
            return error(request, "Invalid theory level")

    else:
        if software == "xtb":
            functional = "GFN2-xTB"
            basis_set = "min"
        else:
            functional = ""
            basis_set = ""

    if 'calc_misc' in request.POST.keys():
        misc = clean(request.POST['calc_misc'])
    else:
        misc = ""

    if len(name) > 100:
        return error(request, "The chosen name is too long")

    if len(project) > 100:
        return error(request, "The chosen project name is too long")

    if charge not in ["-2", "-1", "0", "+1", "+2"]:
        return error(request, "Invalid charge (-2 to +2)")

    if solvent not in SOLVENT_TABLE.keys() and solvent != "Vacuum":
        return error(request, "Invalid solvent")


    if step.name not in BASICSTEP_TABLE[software].keys():
        return error(request, "Invalid calculation type")


    profile = request.user.profile
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

    if project == "New Project":
        new_project_name = clean(request.POST['new_project_name'])
        try:
            project_obj = Project.objects.get(name=new_project_name, author=profile)
        except Project.DoesNotExist:
            project_obj = Project.objects.create(name=new_project_name, author=profile)
            profile.project_set.add(project_obj)
            pass
        else:
            print("Project with that name already exists")
    else:
        try:
            project_set = profile.project_set.filter(name=project)
        except Profile.DoesNotExist:
            return error("No such project")

        if len(project_set) != 1:
            print("More than one project with the same name found!")
        else:
            project_obj = project_set[0]

    params = Parameters.objects.create(charge=charge, solvent=solvent, multiplicity=1, method=functional, basis_set=basis_set, misc=misc, software=software)
    params.save()

    obj = CalculationOrder.objects.create(name=name, date=timezone.now(), parameters=params, author=profile, step=step, project=project_obj)

    drawing = True

    if 'starting_ensemble' in request.POST.keys():
        drawing = False
        start_id = int(clean(request.POST['starting_ensemble']))
        try:
            start_e = Ensemble.objects.get(pk=start_id)
        except Ensemble.DoesNotExist:
            return error(request, "No starting ensemble found")

        start_author = start_e.parent_molecule.project.author
        if not profile_intersection(profile, start_author):
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

                    if not profile_intersection(profile, filter_parameters.property_set.all()[0].parent_structure.parent_ensemble.parent_molecule.project.author):
                        return error(request, "Invalid filter parameters")

                    filter = Filter.objects.create(type=filter_type, parameters=filter_parameters, value=filter_value)
                    obj.filter = filter
                else:
                    return error(request, "No filter parameters")


            else:
                return error(request, "Invalid filter type")


    elif 'starting_struct' in request.POST.keys():
        drawing = False
        start_id = int(clean(request.POST['starting_struct']))
        try:
            start_s = Structure.objects.get(pk=start_id)
        except Structure.DoesNotExist:
            return error(request, "No starting ensemble found")
        start_author = start_s.parent_ensemble.parent_molecule.project.author
        if not profile_intersection(profile, start_author):
            return error(request, "You do not have permission to access the starting calculation")
        obj.structure = start_s

    else:
        if len(request.FILES) == 1:
            e = Ensemble.objects.create(name="File Upload")
            obj.ensemble = e

            s = Structure.objects.create(parent_ensemble=e, number=1)

            params = Parameters.objects.create(software="Unknown", method="Unknown", basis_set="", solvation_model="", charge=charge, multiplicity="1")
            p = Property.objects.create(parent_structure=s, parameters=params, geom=True)
            p.save()
            params.save()

            drawing = False
            in_file = clean(request.FILES['file_structure'].read().decode('utf-8'))
            filename, ext = request.FILES['file_structure'].name.split('.')

            if ext == 'mol':
                s.mol_structure = in_file
            elif ext == 'xyz':
                s.xyz_structure = in_file
            elif ext == 'sdf':
                s.sdf_structure = in_file
            elif ext == 'mol2':
                s.mol2_structure = in_file
            else:
                return error(request, "Unknown file extension (Known formats: .mol, .mol2, .xyz, .sdf)")
            e.save()
            s.save()
        else:
            if 'structureB' in request.POST.keys():
                drawing = True
                e = Ensemble.objects.create(name="Drawn Structure")
                obj.ensemble = e

                s = Structure.objects.create(parent_ensemble=e, number=1)
                params = Parameters.objects.create(software="Open Babel", method="Forcefield", basis_set="", solvation_model="", charge=charge, multiplicity="1")
                p = Property.objects.create(parent_structure=s, parameters=params, geom=True)
                p.save()
                params.save()


                mol = clean(request.POST['structureB'])
                s.mol_structure = mol
            else:
                return error(request, "No input structure")

        e.save()
        s.save()

    TYPE_LENGTH = {'Distance' : 2, 'Angle' : 3, 'Dihedral' : 4}
    constraints = ""
    if 'constraint_num' in request.POST.keys():
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

    obj.constraints = constraints


    if ressource != "Local":
        obj.resource = access

    obj.save()
    profile.save()

    if not 'test' in request.POST.keys():
        dispatcher.delay(drawing, obj.id)

    return redirect("/projects/")

@login_required
def launch_software(request, software):
    _software = clean(software)
    if _software == 'xtb':
        procs = BasicStep.objects.filter(avail_xtb=True)
        return render(request, 'frontend/launch_software.html', {'procs': procs, 'software': _software})
    elif _software == 'Gaussian':
        procs = BasicStep.objects.filter(avail_Gaussian=True)
        return render(request, 'frontend/launch_software.html', {'procs': procs, 'software': _software})
    elif _software == 'ORCA':
        procs = BasicStep.objects.filter(avail_ORCA=True)
        return render(request, 'frontend/launch_software.html', {'procs': procs, 'software': _software})
    else:
        return HttpResponse(status=404)

def profile_intersection(profile1, profile2):
    if profile1 == profile2:
        return True
    if profile1.group != None:
        if profile2 in profile1.group.members.all():
            return True
        if profile2 == profile1.group.PI:
            return True
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
            rel_energies = ["{:.2f}".format(float(i)*HARTREE_FVAL) for i in _rel_energies]
        elif pref_units == 1:
            rel_energies = ["{:.2f}".format(float(i)*HARTREE_TO_KCAL_F) for i in _rel_energies]
        elif pref_units == 2:
            rel_energies = ["{:.5f}".format(i) for i in _rel_energies]

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
    calc = Calculation.objects.get(pk=id)

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
    calc = Calculation.objects.get(pk=id)

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

    if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
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

    if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
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
        print(lines)
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
        id = int(clean(request.POST['id']))

        try:
            e = Ensemble.objects.get(pk=id)
        except Ensemble.DoesNotExist:
            return HttpResponse(status=403)

        profile = request.user.profile

        if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
            return HttpResponse(status=403)

        structs = e.structure_set.all()

        if 'num' in request.POST.keys():
            num = int(clean(request.POST['num']))
            try:
                struct = structs.get(number=num)
            except Structure.DoesNotExist:
                if len(structs) == 0:
                    return HttpResponse(status=204)

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
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc.order.author != profile and not profile_intersection(profile, calc.order.author):
            return HttpResponse(status=403)

        num = request.POST['num']
        expected_file = os.path.join(CALCUS_RESULTS_HOME, id, "freq_{}.xyz".format(num))
        if os.path.isfile(expected_file):
            with open(expected_file) as f:
                lines = f.readlines()

            return HttpResponse(''.join(lines))
        else:
            return HttpResponse(status=204)

@login_required
def get_scan_animation(request):
    if request.method == 'POST':
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
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

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/details_sections.html', {
            'calculation': calc
        })

@login_required
def log(request, pk):
    LOG_HTML = """
    <label class="label">{}</label>
    <textarea class="textarea" style="height: 300px;" readonly>
    {}
    </textarea>
    """

    response = ''

    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if not profile_intersection(profile, calc.order.author):
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
        print(units)
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
            'procedures': BasicStep.objects.all(),
        })

@login_required
def launch_pk(request, pk):

    try:
        e = Ensemble.objects.get(pk=pk)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'ensemble': e,
            'procedures': BasicStep.objects.all(),
        })

@login_required
def launch_structure_pk(request, ee, pk):

    try:
        e = Ensemble.objects.get(pk=ee)
    except Ensemble.DoesNotExist:
        return redirect('/home/')

    profile = request.user.profile

    if e.parent_molecule.project.author != profile and not profile_intersection(profile, e.parent_molecule.project.author):
        return HttpResponse(status=403)

    try:
        s = e.structure_set.get(number=pk)
    except Structure.DoesNotExist:
        return redirect('/home/')

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'structure': s,
            'procedures': BasicStep.objects.all(),
        })

def get_csv(proj, profile):
    pref_units = profile.pref_units
    units = profile.pref_units_name

    if pref_units == 0:
        CONVERSION = HARTREE_FVAL
    elif pref_units == 1:
        CONVERSION = HARTREE_TO_KCAL_F
    elif pref_units == 2:
        CONVERSION = 1

    summary = {}
    csv = "Molecule,Ensemble,Structure\n"
    for mol in proj.molecule_set.all():
        csv += "\n\n{}\n".format(mol.name)
        for e in mol.ensemble_set.all():
            csv += "\n,{}\n".format(e.name)
            for params in e.unique_parameters:
                rel_energies = e.relative_energies(params)
                rel_energies = [float(i)*CONVERSION if i != '' else '' for i in rel_energies]
                weights = e.weights(params)
                csv += ",,{}\n".format(params)
                csv += ",,Number,Energy ({}),Relative Energy ({}), Boltzmann Weight,Free energy ({})\n".format(units, units, units)
                for s in e.structure_set.all():
                    try:
                        prop = s.properties.get(parameters=params)
                    except Property.DoesNotExist:
                        pass
                    else:
                        csv += ",,{},{},{},{},{}\n".format(s.number, prop.energy*CONVERSION, rel_energies[s.number-1], weights[s.number-1], prop.free_energy*CONVERSION)

                w_e = e.weighted_energy(params)
                if w_e != '' and w_e != '-' and w_e != 0:
                    w_e *= CONVERSION
                w_f_e = e.weighted_free_energy(params)
                if w_f_e != '' and w_f_e != '-' and w_f_e != 0:
                    w_f_e *= CONVERSION
                csv += "\n,,Ensemble Average,{},,,{}\n".format(w_e, w_f_e)
                p_name = params.__repr__()
                if p_name in summary.keys():
                    if mol.id in summary[p_name].keys():
                        summary[p_name][mol.id][e.id] = [w_e, w_f_e]
                    else:
                        summary[p_name][mol.id] = {e.id: [w_e, w_f_e]}
                else:
                    summary[p_name] = {}
                    summary[p_name][mol.id] = {e.id: [w_e, w_f_e]}


    csv += "\n\n\nSummary\n"
    csv += "Method,Molecule,Ensemble,Average Energy ({}),Average Free Energy ({})\n".format(units, units)
    for method in summary.keys():
        csv += "{}\n".format(method)
        for mol in summary[method].keys():
            mol_obj = Molecule.objects.get(pk=mol)
            csv += ",{}\n".format(mol_obj.name)
            for e in summary[method][mol].keys():
                e_obj = Ensemble.objects.get(pk=e)
                csv += ",,{},{},{}\n".format(e_obj.name, summary[method][mol][e][0], summary[method][mol][e][1])
    return csv

@login_required
def download_project_csv(request, project_id):

    profile = request.user.profile

    try:
        proj = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return HttpResponse(status=403)

    if not profile_intersection(profile, proj.author):
        return HttpResponse(status=403)

    csv = get_csv(proj, profile)

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

@login_required
def ensemble_map(request, pk):
    try:
        mol = Molecule.objects.get(pk=pk)
    except Molecule.DoesNotExist:
        return redirect('/home/')

    if not profile_intersection(request.user.profile, mol.project.author):
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
        nodes += """{{ "data": {{"id": "{}", "name": "{}", "href": "/ensemble/{}", "color": "{}"}} }},""".format(e.id, e.name, e.id, e.get_node_color)
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

    if not profile_intersection(profile, proj.author):
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
    if not profile_intersection(profile, order.author):
        return HttpResponse(status=404)

    return render(request, 'frontend/calculationorder.html', {'order': order})

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
