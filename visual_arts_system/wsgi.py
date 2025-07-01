"""
WSGI config for visual_arts_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

settings_module = 'visual_arts_system.deployment_settings' if 'RENDER_EXTERNAL_HOSTNAME' in os.environ else 'visual_arts_system.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
