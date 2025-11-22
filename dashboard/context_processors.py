from django.conf import settings

def environment(request):
    return {
        'IS_LOCAL': settings.IS_LOCAL,
        'IS_CLOUD': settings.IS_CLOUD,
        'ENVIRONMENT': settings.ENVIRONMENT,
    }
