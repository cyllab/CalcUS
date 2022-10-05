from django.conf import settings


def default(request):
    return {
        k: getattr(settings, k)
        for k in [
            "IS_CLOUD",
            "ALLOW_LOCAL_CALC",
            "ALLOW_REMOTE_CALC",
            "LOCAL_MAX_ATOMS",
            "LOCAL_ALLOWED_THEORY_LEVELS",
            "LOCAL_ALLOWED_STEPS",
        ]
    }
