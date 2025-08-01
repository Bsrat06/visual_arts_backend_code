"""
ASGI config for visual_arts_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

settings_module = 'visual_arts_system.deployment_settings' if 'RENDER_EXTERNAL_HOSTNAME' in os.environ else 'visual_arts_system.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module )

application = get_asgi_application()
