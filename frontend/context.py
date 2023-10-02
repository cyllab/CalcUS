from django.conf import settings

import logging

logger = logging.getLogger(__name__)

from frontend import constants


def default(request):
    d = {}
    for k in [
        "IS_TEST",
        "IS_CLOUD",
        "ALLOW_LOCAL_CALC",
        "ALLOW_REMOTE_CALC",
        "ALLOW_TRIAL",
        "LOCAL_MAX_ATOMS",
        "LOCAL_ALLOWED_THEORY_LEVELS",
        "LOCAL_ALLOWED_STEPS",
    ]:
        d[k] = getattr(settings, k)

    if settings.IS_CLOUD:
        if settings.IS_TEST:
            version = "testing"
        else:
            version = "production"
        try:
            d["SUBSCRIPTION_DATA"] = constants.SUBSCRIPTION_DATA[version]
        except (NameError, AttributeError):
            logger.error(f"Could not get subscription data")

    return d
