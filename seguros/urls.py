"""
URL configuration for seguros project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import HomeRedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # UI interna
    path("ui/", include("ui.urls", namespace="ui")),

    # Auth Django (login/logout/password_reset, etc.)
    path("accounts/", include("accounts.urls")),

    # Portal Clientes
    path("portal/", include(("portal.urls", "portal"), namespace="portal")),

    # Agentes / cotizador externo
    path("agentes/", include("cotizador.urls_agentes")),

    # Documentos
    path("documentos/", include("documentos.urls", namespace="documentos")),

    # Integraciones
    path("integrations/", include("integrations.urls", namespace="integrations")),

    # Root
    path("", HomeRedirectView.as_view(), name="root"),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
