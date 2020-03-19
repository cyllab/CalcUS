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

from .models import Calculation, Profile, Project
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

from .forms import UserCreateForm

from django.utils import timezone

from .tasks import geom_opt, conf_search, uvvis_simple, nmr_enso

from django.views.decorators.csrf import csrf_exempt

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']


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

    obj = Calculation.objects.create(name=name, date=timezone.now(), type=type, status=0, charge=charge)

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
