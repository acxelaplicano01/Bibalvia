from django.conf import settings

def environment(request):
    return {
        'IS_CLOUD': settings.IS_CLOUD,
        'IS_LOCAL': settings.IS_LOCAL,
    }
