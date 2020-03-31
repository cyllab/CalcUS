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
from .models import Calculation, Profile, Project, ClusterAccess, ClusterCommand, Example, PIRequest, ResearchGroup
from .tasks import geom_opt, conf_search, uvvis_simple, nmr_enso, geom_opt_freq, constraint_opt, ts_freq
from .decorators import superuser_required
from .tasks import system

try:
    is_test = os.environ['LAB_TEST']
except:
    is_test = False

if is_test:
    LAB_SCR_HOME = os.environ['LAB_TEST_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_TEST_RESULTS_HOME']
else:
    LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
    LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']

LAB_KEY_HOME = os.environ['LAB_KEY_HOME']
LAB_CLUSTER_HOME = os.environ['LAB_CLUSTER_HOME']

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


        try:
            target_profile = User.objects.get(username=target_username).profile
        except User.DoesNotExist:
            return []

        if profile_intersection(self.request.user.profile, target_profile):
            hits = target_profile.calculation_set.all()
            if proj != "All projects":
                hits = hits.filter(project__name=proj)
            if type != "All calculation types":
                hits = hits.filter(type=Calculation.CALC_TYPES[type])
            if status != "All statuses":
                hits = hits.filter(status=Calculation.CALC_STATUSES[status])
            return sorted(hits, key=lambda d: d.date, reverse=True)

        else:
            return []


def index(request, page=1):
    return render(request, 'frontend/index.html', {"page": page})


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



@login_required
def submit_calculation(request):
    if 'calc_name' in request.POST.keys():
        name = request.POST['calc_name']
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No calculation name"
            })

    if 'calc_type' in request.POST.keys():
        type = Calculation.CALC_TYPES[request.POST['calc_type']]
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No calculation type"
            })
    if 'calc_project' in request.POST.keys():
        project = request.POST['calc_project']
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No calculation project"
            })

    if 'calc_charge' in request.POST.keys():
        charge = request.POST['calc_charge']
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No calculation charge"
            })

    if 'calc_solvent' in request.POST.keys():
        solvent = request.POST['calc_solvent']
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No calculation solvent"
            })


    if 'calc_ressource' in request.POST.keys():
        ressource = request.POST['calc_ressource']
    else:
        return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "You have no computing ressource"
            })

    profile = request.user.profile
    if ressource != "Local":
        try:
            access = ClusterAccess.objects.get(cluster_address=ressource)
        except ClusterAccess.DoesNotExist:
            return redirect("/home/")

        if profile not in access.users and access.owner != profile:
            return redirect("/home/")
    else:
        if not profile.is_PI and profile.groups == None:
            return redirect("/home/")

    if project == "New Project":
        new_project_name = request.POST['new_project_name']
        try:
            project_obj = Project.objects.get(name=new_project_name)
        except Project.DoesNotExist:
            project_obj = Project.objects.create(name=new_project_name)
            profile.project_set.add(project_obj)
            pass
        else:
            print("Project with that name already exists")
    else:
        project_set = profile.project_set.filter(name=project)
        if len(project_set) != 1:
            print("More than one project with the same name found!")
        else:
            project_obj = project_set[0]


    obj = Calculation.objects.create(name=name, date=timezone.now(), type=type, status=0, charge=charge, solvent=solvent)

    profile.calculation_set.add(obj)
    project_obj.calculation_set.add(obj)

    project_obj.save()
    profile.save()

    t = str(obj.id)

    scr = os.path.join(LAB_SCR_HOME, t)
    os.mkdir(scr)

    print(request.POST)
    drawing = True
    if len(request.FILES) == 1:
        drawing = False
        in_file = request.FILES['file_structure']
        filename, ext = in_file.name.split('.')

        if ext in ['mol2', 'mol', 'xyz', 'sdf']:
            with open(os.path.join(LAB_SCR_HOME, t, 'initial.{}'.format(ext)), 'wb+') as out:
                for chunk in in_file.chunks():
                    out.write(chunk)
    else:
        if 'structure' in request.POST.keys():
            if 'structureB' in request.POST.keys():
                drawing = False
            else:
                drawing = True
            mol = request.POST['structure']
            with open(os.path.join(scr, 'initial.mol'), 'w') as out:
                out.write(mol)
        elif 'structureB' in request.POST.keys():
            mol = request.POST['structureB']
            with open(os.path.join(scr, 'initial_2D.mol'), 'w') as out:
                out.write(mol)
        else:
            return render(request, 'frontend/error.html', {
            'profile': request.user.profile,
            'error_message': "No input structure"
            })


    TYPE_LENGTH = {'Distance' : 2, 'Angle' : 3, 'Dihedral' : 4}
    if type == 5:
        constraints = []
        for ind in range(1, int(request.POST['constraint_num'])+1):
            try:
                mode = bleach.clean(request.POST['constraint_mode_{}'.format(ind)])
            except MultiValueDictKeyError:
                pass
            else:
                _type = bleach.clean(request.POST['constraint_type_{}'.format(ind)])
                ids = []
                for i in range(1, TYPE_LENGTH[_type]+1):
                    id = int(bleach.clean(request.POST['calc_constraint_{}_{}'.format(ind, i)]))
                    ids.append(id)

                if mode == "Freeze":
                    constraints.append([mode, ids])
                elif mode == "Scan":
                    begin = bleach.clean(request.POST['calc_scan_{}_1'.format(ind)])
                    end = float(bleach.clean(request.POST['calc_scan_{}_2'.format(ind)]))
                    steps = float(bleach.clean(request.POST['calc_scan_{}_3'.format(ind)]))
                    constraints.append([mode, [begin, end, steps], ids])
                else:
                    return HttpResponse(status=403)



    if ressource == "Local":
        if type == 0:
            geom_opt.delay(t, drawing, charge, solvent)
        elif type == 1:
            conf_search.delay(t, drawing, charge, solvent)
        elif type == 2:
            uvvis_simple.delay(t, drawing, charge, solvent)
        elif type == 3:
            nmr_enso.delay(t, drawing, charge, solvent)
        elif type == 4:
            geom_opt_freq.delay(t, drawing, charge, solvent)
        elif type == 5:
            constraint_opt.delay(t, drawing, charge, solvent, constraints)
        elif type == 6:
            ts_freq.delay(t, drawing, charge, solvent)
    else:
        cmd = ClusterCommand.objects.create(issuer=profile)
        with open(os.path.join(LAB_CLUSTER_HOME, 'todo', str(cmd.id)), 'w') as out:
            out.write("launch\n")
            out.write("{}\n".format(t))
            out.write("{}\n".format(access.id))
            out.write("{}\n".format(type))
            out.write("{}\n".format(charge))
            out.write("{}\n".format(solvent))
            out.write("{}\n".format(drawing))

    return redirect("/details/{}".format(t))

def profile_intersection(profile1, profile2):
    if profile1 == profile2:
        return True
    if profile1.groups != None:
        if profile2 in profile1.groups.members.all():
            return True
        if profile2 == profile1.groups.PI:
            return True
    if profile1.researchgroup_PI != None:
        for group in profile1.researchgroup_PI.all():
            if profile2 in group.members.all():
                return True
    return False

@login_required
def project_list(request):
    if request.method == "POST":
        target_username = bleach.clean(request.POST['user'])
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
def delete(request, pk):
    profile, created = Profile.objects.get_or_create(user=request.user)

    try:
        to_delete = profile.calculation_set.get(id=pk)
    except Calculation.DoesNotExist:
        return redirect("/home/")
    else:
        try:
            shutil.rmtree(os.path.join(LAB_SCR_HOME, str(pk)))
        except FileNotFoundError:
            pass
        try:
            shutil.rmtree(os.path.join(LAB_RESULTS_HOME, str(pk)))
        except FileNotFoundError:
            pass
        to_delete.delete()
        return redirect("/home/")

@login_required
def add_clusteraccess(request):
    if request.method == 'POST':
        address = bleach.clean(request.POST['cluster_address'])
        username = bleach.clean(request.POST['cluster_username'])
        owner = request.user.profile

        if not owner.is_PI:
            return HttpResponse(status=403)

        try:
            existing_access = owner.clusteraccess_owner.get(cluster_address=address, cluster_username=username, owner=owner)
        except ClusterAccess.DoesNotExist:
            pass
        else:
            return HttpResponse(status=403)

        key_private_name = "{}_{}_{}".format(owner.username, username, ''.join(ch for ch in address if ch.isalnum()))
        key_public_name = key_private_name + '.pub'

        access = ClusterAccess.objects.create(cluster_address=address, cluster_username=username, private_key_path=key_private_name, public_key_path=key_public_name, owner=owner, group=owner.researchgroup_PI.all()[0])
        access.save()
        owner.save()

        key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=2048)

        public_key = key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)

        pem = key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption())
        with open(os.path.join(LAB_KEY_HOME, key_private_name), 'wb') as out:
            out.write(pem)

        with open(os.path.join(LAB_KEY_HOME, key_public_name), 'wb') as out:
            out.write(public_key)
            out.write(b' %b@calcUS' % bytes(owner.username, 'utf-8'))

        return HttpResponse(public_key.decode('utf-8'))
    else:
        return HttpResponse(status=403)

@login_required
def test_access(request):
    pk = request.POST['access_id']

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    cmd = ClusterCommand.objects.create(issuer=profile)
    cmd.save()
    profile.save()

    with open(os.path.join(LAB_CLUSTER_HOME, "todo", str(cmd.id)), 'w') as out:
        out.write("access_test\n")
        out.write("{}\n".format(pk))

    return HttpResponse(cmd.id)

@login_required
def get_command_status(request):
    pk = request.POST['command_id']

    cmd = ClusterCommand.objects.get(pk=pk)

    profile = request.user.profile
    if cmd not in profile.clustercommand_set.all():
        return HttpResponse(status=403)

    expected_file = os.path.join(LAB_CLUSTER_HOME, "done", str(cmd.id))
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

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    access.delete()
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
def add_user(request):
    if request.method == "POST":
        profile = request.user.profile

        if not profile.is_PI:
            return HttpResponse(status=403)

        username = bleach.clean(request.POST['username'])
        group_id = int(bleach.clean(request.POST['group_id']))

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

        code = bleach.clean(request.POST['code'])

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

        member_id = int(bleach.clean(request.POST['member_id']))
        group_id = int(bleach.clean(request.POST['group_id']))

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
def claimed_key_table(request):
    return render(request, 'frontend/claimed_key_table.html', {
            'profile': request.user.profile,
        })

@login_required
def conformer_table(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type
    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    if type != 1:
        return HttpResponse(status=403)

    return render(request, 'frontend/conformer_table.html', {
            'profile': request.user.profile,
            'calculation': calc,
        })

@login_required
def icon(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    icon_file = os.path.join(LAB_RESULTS_HOME, id, "icon.svg")

    if os.path.isfile(icon_file):
        with open(icon_file, 'rb') as f:
            response = HttpResponse(content=f)
            response['Content-Type'] = 'image/svg+xml'
            return response
    else:
        return HttpResponse(status=204)

@login_required
def uvvis(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    if type != 2:
        return HttpResponse(status=403)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    spectrum_file = os.path.join(LAB_RESULTS_HOME, id, "uvvis.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@login_required
def nmr(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    if type != 3:
        return HttpResponse(status=403)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    spectrum_file = os.path.join(LAB_RESULTS_HOME, id, "nmr.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@login_required
def ir_spectrum(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    if type != 4 and type != 6:
        return HttpResponse(status=403)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    spectrum_file = os.path.join(LAB_RESULTS_HOME, id, "IR.csv")

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

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    vib_file = os.path.join(LAB_RESULTS_HOME, id, "vibspectrum")

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
                [vibs[3*ind+1] if 3*ind+2 < len(vibs) else '', 3*ind+1],
                [vibs[3*ind+2] if 3*ind+3 < len(vibs) else '', 3*ind+2]
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
        group_name = bleach.clean(request.POST['group_name'])
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
def download_structure(request, pk):
    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    if type == 1:
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "crest_conformers.xyz")
    elif type == 6:
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "ts.xyz")
    else:
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "xtbopt.xyz")

    if os.path.isfile(expected_file):
        with open(expected_file, 'rb') as f:
            response = HttpResponse(f.read())
            response['Content-Type'] = 'text/plain'
            response['Content-Disposition'] = 'attachment; filename={}.xyz'.format(id)
            return response
    else:
        return HttpResponse(status=204)

def gen_3D(request):
    if request.method == 'POST':
        mol = request.POST['mol']
        clean_mol = bleach.clean(mol)

        t = time.time()
        with open("/tmp/{}.mol".format(t), 'w') as out:
            out.write(clean_mol)

        system("babel -imol /tmp/{}.mol -oxyz /tmp/{}.xyz -h --gen3D".format(t, t), force_local=True)
        with open("/tmp/{}.xyz".format(t)) as f:
            lines = f.readlines()
        return HttpResponse(lines)
    return HttpResponse(status=403)

@login_required
def get_structure(request):
    if request.method == 'POST':
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
            return HttpResponse(status=403)

        type = calc.type

        if type == 0 or type == 2 or type == 3 or type == 4 or type == 5:
            expected_file = os.path.join(LAB_RESULTS_HOME, id, "xtbopt.xyz")
            if os.path.isfile(expected_file):
                with open(expected_file) as f:
                    lines = f.readlines()
                return HttpResponse(lines)
            else:
                return HttpResponse(status=204)
        elif type == 1:
            num = bleach.clean(request.POST['num'])
            expected_file = os.path.join(LAB_RESULTS_HOME, id, "conf{}.xyz".format(num))
            if os.path.isfile(expected_file):
                with open(expected_file) as f:
                    lines = f.readlines()
                return HttpResponse(lines)
            else:
                return HttpResponse(status=204)
        elif type == 6:
            expected_file = os.path.join(LAB_RESULTS_HOME, id, "ts.xyz")
            if os.path.isfile(expected_file):
                with open(expected_file) as f:
                    lines = f.readlines()
                return HttpResponse(lines)
            else:
                return HttpResponse(status=204)

@login_required
def get_vib_animation(request):
    if request.method == 'POST' or True:
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
            return HttpResponse(status=403)

        type = calc.type

        if type != 4 and type != 6:
            return HttpResponse(status=403)

        num = request.POST['num']
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "freq_{}.xyz".format(num))
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
            return render(request, 'frontend/vib_animation.html', {
                'xyz_files': xyz_files[1:]
                })
        else:
            return HttpResponse(status=204)

@login_required
def get_scan_animation(request):
    if request.method == 'POST' or True:
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
            return HttpResponse(status=403)

        type = calc.type

        if type != 5:
            return HttpResponse(status=403)

        expected_file = os.path.join(LAB_RESULTS_HOME, id, "xtbscan.xyz")
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
def log(request, pk):
    LOG_HTML = """
    <label class="label">{}</label>
    <textarea class="textarea" readonly>
    {}
    </textarea>
    """

    response = ''

    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    for out in glob.glob(os.path.join(LAB_RESULTS_HOME, str(pk)) + '/*.out'):
        out_name = out.split('/')[-1]
        with open(out) as f:
            lines = f.readlines()
        response += LOG_HTML.format(out_name, ''.join(lines))

    return HttpResponse(response)

@login_required
def manage_access(request, pk):
    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/manage_access.html', {
            'profile': request.user.profile,
            'access': access,
        })

@login_required
def key_table(request, pk):
    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/key_table.html', {
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
def launch(request):
    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
        })

@login_required
def launch_pk(request, pk):

    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if calc not in profile.calculation_set.all() and not profile_intersection(profile, calc.author):
        return HttpResponse(status=403)

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
            'calculation': calc,
        })

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
