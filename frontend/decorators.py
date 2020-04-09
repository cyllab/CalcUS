from .models import Profile
from django.http import HttpResponse, HttpResponseRedirect

def superuser_required(func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return func(request, *args, **kwargs)
        else:
            return HttpResponse(status=403)
    return wrapper
