from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.views import generic

from django.http import HttpResponseForbidden

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

from .forms import UserCreateForm

from django.utils import timezone

from .tasks import geom_opt, conf_search

from django.views.decorators.csrf import csrf_exempt

LAB_SCR_HOME = os.environ['LAB_SCR_HOME']
LAB_TODO_HOME = os.environ['LAB_TODO_HOME']
LAB_RESULTS_HOME = os.environ['LAB_RESULTS_HOME']


class IndexView(generic.ListView):
    template_name = 'frontend/index.html'
    context_object_name = 'latest_frontend'
    paginate_by = '5'

    def get_queryset(self, *args, **kwargs):
        if isinstance(self.request.user, AnonymousUser):
            return []

        try:
            page = self.kwargs['page']
        except KeyError:
            page = 0
        self.request.session['previous_page'] = page
        return sorted(self.request.user.profile.calculation_set.all(), key=lambda d: d.date, reverse=True)


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

    mol = request.POST['structure']

    name = request.POST['calc_name']
    type = Calculation.CALC_TYPES[request.POST['calc_type']]
    project = request.POST['calc_project']

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


    obj = Calculation.objects.create(name=name, date=timezone.now(), type=type, status=0)

    profile.calculation_set.add(obj)
    project_obj.calculation_set.add(obj)

    t = str(obj.id)

    scr = os.path.join(LAB_SCR_HOME, t)
    os.mkdir(scr)
    with open(os.path.join(scr, 'initial.mol'), 'w') as out:
        out.write(mol)

    if type == 0:
        geom_opt.delay(t)
    elif type == 1:
        conf_search.delay(t)

    return redirect("/details/{}".format(t))

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
def download_structure(request, pk):
    if isinstance(request.user, AnonymousUser):
        return HttpResponse(status=403)

    id = str(pk)
    calc = Calculation.objects.get(pk=id)
    type = calc.type

    profile = request.user.profile

    if calc not in profile.calculation_set.all():
        return HttpResponse(status=403)

    if type == 0:
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

        if type == 0:
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
