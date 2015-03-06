import os

from barrel import cooper
from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangocon.settings.local")

username = os.environ.get('BARREL_USER')
password = os.environ.get('BARREL_PASS')

application = get_wsgi_application()

if len(username) and len(password):

    auth_decorator = cooper.basicauth(
        users=[(username, password), ],
        realm='Password Protected'
    )

    application = auth_decorator(application)
