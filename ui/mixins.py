from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages

class SupervisorRequiredMixin(UserPassesTestMixin):
    """
    Permite acceso solo a usuarios en grupo Supervisor o Admin
    """

    def test_func(self):
        user = self.request.user

        return (
            user.is_superuser
            or user.groups.filter(name__in=["Supervisor", "Admin"]).exists()
        )


class SupervisorRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        user = self.request.user
        return (
            user.is_superuser
            or user.groups.filter(name__in=["Supervisor", "Admin"]).exists()
        )

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permisos para acceder a esta sección.")
        return redirect("ui:dashboard")
