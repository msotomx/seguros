# accounts/urls.py
from django.urls import path, include
from .views import RoleBasedLoginView

urlpatterns = [
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    # Todo lo demás (logout, password_reset, etc.) lo deja Django
    path("", include("django.contrib.auth.urls")),
]
