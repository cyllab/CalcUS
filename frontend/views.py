from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.views import generic

from django.http import HttpResponseForbidden
from django.core.files.storage import FileSystemStorage

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser

from .models import Calculation, Profile, Project, ClusterAccess, ClusterPersonalKey, ClusterCommand
from django.contrib.auth.models import User

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.decorators import user_passes_test

from django.shortcuts import render
from django.template import RequestContext

import bleach
import os
import shutil
import glob
import random
import string

from .forms import UserCreateForm

from django.utils import timezone

from .tasks import geom_opt, conf_search, uvvis_simple, nmr_enso

from django.views.decorators.csrf import csrf_exempt

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']
LAB_KEY_HOME = os.environ['LAB_KEY_HOME']
LAB_CLUSTER_HOME = os.environ['LAB_CLUSTER_HOME']

KEY_SIZE = 32

class IndexView(generic.ListView):
    template_name = 'frontend/list.html'
    context_object_name = 'latest_frontend'
    paginate_by = '5'

    def get_queryset(self, *args, **kwargs):
        if isinstance(self.request.user, AnonymousUser):
            return []

        try:
            page = int(self.request.GET.get('page'))
        except KeyError:
            page = 0

        self.request.session['previous_page'] = page
        proj = self.request.GET.get('project')

        if proj == "All projects":
            return sorted(self.request.user.profile.calculation_set.all(), key=lambda d: d.date, reverse=True)
        else:
            return sorted(self.request.user.profile.calculation_set.filter(project__name=proj), key=lambda d: d.date, reverse=True)


def index(request, page=1):
    return render(request, 'frontend/index.html', {"page": page})


class DetailView(generic.DetailView):
    model = Calculation
    template_name = 'frontend/details.html'

    def get_queryset(self):
        return Calculation.objects.filter(date__lte=timezone.now(), author__user=self.request.user)


def smart_index(request):
    if 'previous_page' in request.session:
        a = request.session['previous_page']
        print(a)
        return redirect('{a}/')
    else:
        redirect('')

is_admin = lambda u: u.is_superuser == True


class RegisterView(generic.CreateView):
    form_class = UserCreateForm
    template_name = 'registration/signup.html'
    model = Profile
    success_url = '/accounts/login/'

def please_register(request):
        return render(request, 'frontend/please_register.html', {})

def submit_calculation(request):
    if isinstance(request.user, AnonymousUser):
        return please_register()

    name = request.POST['calc_name']
    type = Calculation.CALC_TYPES[request.POST['calc_type']]
    project = request.POST['calc_project']
    charge = request.POST['calc_charge']
    solvent = request.POST['calc_solvent']

    profile, created = Profile.objects.get_or_create(user=request.user)

    if project == "New Project":
        new_project_name = request.POST['new_project_name']
        #if new_project_name in profile.project_set:
            #project_obj = profile.project_set
        project_obj = Project.objects.create(name=new_project_name)
        profile.project_set.add(project_obj)
    else:
        #try:
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

    drawing = True

    if len(request.FILES) == 1:
        drawing = False
        in_file = request.FILES['file_structure']
        filename, ext = in_file.name.split('.')
        fs = FileSystemStorage()

        if ext in ['mol2', 'mol', 'xyz', 'sdf']:
            _ = fs.save(os.path.join(t, 'initial.{}'.format(ext)), in_file)
    else:
        mol = request.POST['structure']
        with open(os.path.join(scr, 'initial.mol'), 'w') as out:
            out.write(mol)

    if type == 0:
        geom_opt.delay(t, drawing, charge, solvent)
    elif type == 1:
        conf_search.delay(t, drawing, charge, solvent)
    elif type == 2:
        uvvis_simple.delay(t, drawing, charge, solvent)
    elif type == 3:
        nmr_enso.delay(t, drawing, charge, solvent)

    return redirect("/details/{}".format(t))

def delete(request, pk):
    if isinstance(request.user, AnonymousUser):
        return please_register()

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

def add_clusteraccess(request):
    if request.method == 'POST':
        address = bleach.clean(request.POST['cluster_address'])
        username = bleach.clean(request.POST['cluster_username'])
        owner = request.user.profile

        #existing_accesses = owner.clusteraccess_owner
        #for f in existing_accesses
        #print(existing_accesses)

        key_private_name = "{}_{}_{}".format(owner.username, username, ''.join(ch for ch in address if ch.isalnum()))
        key_public_name = key_private_name + '.pub'

        access = ClusterAccess.objects.create(cluster_address=address, cluster_username=username, private_key_path=key_private_name, public_key_path=key_public_name, owner=owner)
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

@csrf_exempt
def generate_keys(request):
    if request.method == 'POST':
        if isinstance(request.user, AnonymousUser):
            return HttpResponse(status=403)

        access_id = request.POST['access_id']
        num = int(request.POST['num'])

        if num < 1 or num > 10:
            return HttpResponse(status=403)

        access = ClusterAccess.objects.get(pk=access_id)

        profile = request.user.profile

        if access not in profile.clusteraccess_owner.all():
            return HttpResponse(status=403)

        keys = ""
        for i in range(int(num)):
            key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(KEY_SIZE))
            a = ClusterPersonalKey.objects.create(key=key, issuer=profile, date_issued=timezone.now(), access=access)
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)

@csrf_exempt
def claim_key(request):
    if request.method == 'POST':
        if isinstance(request.user, AnonymousUser):
            return HttpResponse(status=403)

        key = request.POST['key']

        try:
            key_obj = ClusterPersonalKey.objects.get(key=key)
        except ClusterPersonalKey.DoesNotExist:
            return HttpResponse("Invalid key")

        if key_obj.claimer is not None:
            return HttpResponse("Invalid key")

        profile = request.user.profile

        keys_owned = profile.clusterpersonalkey_claimer.all()
        for key in keys_owned:
            if key.access.cluster_address == key_obj.access.cluster_address and key.access.cluster_username == key_obj.access.cluster_username:
                return HttpResponse("You already have access to this cluster with this username")

        if key_obj.issuer == profile:
            return HttpResponse("You have issued this key")

        key_obj.claimer = profile
        key_obj.save()

        return HttpResponse("Key claimed")
    else:
        return HttpResponse(status=403)

@csrf_exempt
def test_access(request):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    pk = request.POST['access_id']

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all() and access not in [i.access for i in profile.clusterpersonalkey_claimer]:
        return HttpResponse(status=403)

    cmd = ClusterCommand.objects.create(issuer=profile)

    with open(os.path.join(LAB_CLUSTER_HOME, "todo", str(cmd.id)), 'w') as out:
        out.write("access_test\n")
        out.write("{}\n".format(pk))

    return HttpResponse(cmd.id)

@csrf_exempt
def get_command_status(request):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

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

def delete_access(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    access.delete()
    return HttpResponseRedirect("/profile")

@csrf_exempt
def delete_key(request):
    if request.method == 'POST':
        if isinstance(request.user, AnonymousUser):
            return HttpResponse(status=403)

        access_id = request.POST['access_id']
        key_id = request.POST['key_id']

        access = ClusterAccess.objects.get(pk=access_id)

        profile = request.user.profile

        if access not in profile.clusteraccess_owner.all():
            return HttpResponse(status=403)

        key = ClusterPersonalKey.objects.get(pk=key_id)
        if key not in access.clusterpersonalkey_set.all():
            return HttpResponse(status=403)

        key.delete()
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)

@csrf_exempt
def claimed_key_table(request):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    profile = request.user.profile

    return render(request, 'frontend/claimed_key_table.html', {
            'profile': request.user.profile,
        })

@csrf_exempt
def conformer_table(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type
    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    if type != 1:
        return HttpResponse(status=403)

    return render(request, 'frontend/conformer_table.html', {
            'profile': request.user.profile,
            'calculation': calc,
        })

@csrf_exempt
def icon(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    icon_file = os.path.join(LAB_RESULTS_HOME, id, "icon.svg")

    if os.path.isfile(icon_file):
        with open(icon_file, 'rb') as f:
            response = HttpResponse(content=f)
            response['Content-Type'] = 'image/svg+xml'
            return response
    else:
        return HttpResponse(status=204)

@csrf_exempt
def uvvis(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    spectrum_file = os.path.join(LAB_RESULTS_HOME, id, "uvvis.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@csrf_exempt
def nmr(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    spectrum_file = os.path.join(LAB_RESULTS_HOME, id, "nmr.csv")

    if os.path.isfile(spectrum_file):
        with open(spectrum_file, 'rb') as f:
            response = HttpResponse(f, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}.csv'.format(id)
            return response
    else:
        return HttpResponse(status=204)


@csrf_exempt
def info_table(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/info_table.html', {
            'profile': request.user.profile,
            'calculation': calc,
        })

@csrf_exempt
def status(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/status.html', {
            'calculation': calc,
        })

@csrf_exempt
def download_structure(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    if type == 0 or type == 2:
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "xtbopt.mol")
    elif type == 1:
        expected_file = os.path.join(LAB_RESULTS_HOME, id, "crest_conformers.mol")

    if os.path.isfile(expected_file):
        with open(expected_file, 'rb') as f:
            response = HttpResponse(f.read())
            response['Content-Type'] = 'text/plain'
            response['Content-Disposition'] = 'attachment; filename={}.mol'.format(id)
            return response
    else:
        return HttpResponse(status=204)

@csrf_exempt
def get_structure(request):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    if request.method == 'POST':
        url = request.POST['id']
        id = url.split('/')[-1]

        calc = Calculation.objects.get(pk=id)

        profile = request.user.profile

        if calc not in profile.calculation_set.all():
            return HttpResponse(status=403)

        type = calc.type

        if type == 0 or type == 2 or type == 3:
            expected_file = os.path.join(LAB_RESULTS_HOME, id, "xtbopt.mol")
            if os.path.isfile(expected_file):
                with open(expected_file) as f:
                    lines = f.readlines()
                return HttpResponse(lines)
            else:
                return HttpResponse(status=204)
        if type == 1:
            num = request.POST['num']
            expected_file = os.path.join(LAB_RESULTS_HOME, id, "conf{}.mol".format(num))
            if os.path.isfile(expected_file):
                with open(expected_file) as f:
                    lines = f.readlines()
                return HttpResponse(lines)
            else:
                return HttpResponse(status=204)


def log(request, pk):
    LOG_HTML = """
    <label class="label">{}</label>
    <textarea class="textarea" readonly>
    {}
    </textarea>
    """

    response = ''

    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    for out in glob.glob(os.path.join(LAB_RESULTS_HOME, str(pk)) + '/*.out'):
        out_name = out.split('/')[-1]
        with open(out) as f:
            lines = f.readlines()
        response += LOG_HTML.format(out_name, ''.join(lines))

    return HttpResponse(response)

def manage_access(request, pk):
    if isinstance(request.user, AnonymousUser):
        return please_register(request)

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/manage_access.html', {
            'profile': request.user.profile,
            'access': access,
        })

def key_table(request, pk):
    if isinstance(request.user, AnonymousUser):
        return please_register(request)

    access = ClusterAccess.objects.get(pk=pk)

    profile = request.user.profile

    if access not in profile.clusteraccess_owner.all():
        return HttpResponse(status=403)

    return render(request, 'frontend/key_table.html', {
            'profile': request.user.profile,
            'access': access,
        })

def profile(request):
    if isinstance(request.user, AnonymousUser):
        return please_register(request)

    return render(request, 'frontend/profile.html', {
            'profile': request.user.profile,
        })

def launch(request):
    if isinstance(request.user, AnonymousUser):
        return please_register(request)

    return render(request, 'frontend/launch.html', {
            'profile': request.user.profile,
        })

def launch_pk(request, pk):
    if isinstance(request.user, AnonymousUser):
        return please_register(request)

    calc = Calculation.objects.get(pk=pk)

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
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
