# accounts/urls.py
from django.urls import path, include
from .views import RoleBasedLoginView
from django.contrib.auth.views import LoginView, LogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="logout"),
]
# path("login/", RoleBasedLoginView.as_view(), name="login"),
