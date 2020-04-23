from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib.auth.models import User

class LoginView(TemplateView):

    template_name = 'registration/login.html'

    def post(self, request, **kwargs):

        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

        return render(request, self.template_name)


class LogoutView(TemplateView):

    template_name = 'front/index.html'

    def get(self, request, **kwargs):
        logout(request)
        return render(request, self.template_name)
