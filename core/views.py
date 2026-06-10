from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View

# Al entrar a la pagina de inicio
# Si el usuario esta autenticado se va al dashboard
# Si es publico o cliente, se va a la pagina de inicio de portal:cotizar

class HomeRedirectView(View):

    def get(self, request, *args, **kwargs):

        # Usuario autenticado
        if request.user.is_authenticated:
            return redirect("ui:dashboard")

        # Público / clientes
        return redirect("portal:cotizar")
    