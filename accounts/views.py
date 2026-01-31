# accounts/views.py
from django.contrib.auth.views import LoginView
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

def is_internal(user) -> bool:
    return (
        user.is_authenticated and (
            user.is_superuser
            or user_in_group(user, "Admin")
            or user_in_group(user, "Supervisor")
            or user_in_group(user, "Agente")
        )
    )

class RoleBasedLoginView(LoginView):
    # Usa tu template actual
    template_name = "registration/login.html"

    def get_success_url(self):
        # 1) Respeta "next" si viene y es seguro
        next_url = self.get_redirect_url()
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url

        # 2) Si no hay next, redirige por rol
        user = self.request.user
        if is_internal(user):
            return resolve_url("ui:dashboard")       # /ui/
        return resolve_url("portal:dashboard")       # /portal/dashboard
