from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView, DetailView

from cotizador.models import Cotizacion


class AgenteCotizacionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "cotizador.view_cotizacion"
    template_name = "cotizador/agentes/cotizacion_list.html"
    context_object_name = "cotizaciones"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            Cotizacion.objects
            .select_related(
                "cliente",
                "vehiculo",
                "vehiculo__catalogo",
                "vehiculo__catalogo__marca",
                "vehiculo__catalogo__submarca",
            )
            .order_by("-created_at")
        )

        # Si quieres que cada agente vea solo lo suyo, descomenta:
        # qs = qs.filter(Q(owner=self.request.user) | Q(created_by=self.request.user))

        # Filtro por búsqueda (folio, cliente, email, placas, etc.)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(folio__icontains=q)
                | Q(cliente__nombre_comercial__icontains=q)
                | Q(cliente__nombre__icontains=q)
                | Q(cliente__apellido_paterno__icontains=q)
                | Q(cliente__email_principal__icontains=q)
                | Q(vehiculo__placas__icontains=q)
            )

        # Filtro por estatus
        estatus = (self.request.GET.get("estatus") or "").strip()
        if estatus:
            qs = qs.filter(estatus=estatus)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["estatus"] = (self.request.GET.get("estatus") or "").strip()
        ctx["estatus_choices"] = Cotizacion.Estatus.choices
        return ctx


class AgenteCotizacionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "cotizador.view_cotizacion"
    template_name = "cotizador/agentes/cotizacion_detail.html"
    context_object_name = "cotizacion"

    def get_queryset(self):
        qs = Cotizacion.objects.select_related(
            "cliente",
            "vehiculo",
            "vehiculo__catalogo",
            "vehiculo__catalogo__marca",
            "vehiculo__catalogo__submarca",
        )

        # Si quieres restringir por agente:
        # qs = qs.filter(Q(owner=self.request.user) | Q(created_by=self.request.user))

        return qs

    def get_object(self, queryset=None):
        folio = self.kwargs["folio"]
        return self.get_queryset().get(folio=folio)

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordResetForm
from django.shortcuts import redirect
from django.views import View

from cotizador.models import Cotizacion


class AgenteConvertirClientePortalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "cotizador.change_cotizacion"  # o usa un permiso custom si quieres

    def post(self, request, folio):
        try:
            cotizacion = Cotizacion.objects.select_related("cliente").get(folio=folio)
        except Cotizacion.DoesNotExist:
            messages.error(request, "No se encontró la cotización.")
            return redirect("cotizador_agentes:cotizacion_list")

        cliente = cotizacion.cliente

        # Validaciones mínimas
        email = (cliente.email_principal or "").strip().lower()
        if not email:
            messages.error(request, "Este cliente no tiene email principal. Captúralo para poder crear acceso al portal.")
            return redirect("cotizador_agentes:cotizacion_detail", folio=folio)

        if cliente.user_portal_id:
            messages.info(request, "Este cliente ya tiene acceso al portal.")
            return redirect("cotizador_agentes:cotizacion_detail", folio=folio)

        User = get_user_model()

        # Crear o reutilizar usuario por email (username=email)
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "is_active": True,
            },
        )

        # Asegura email + activo (por si existía)
        if not user.email:
            user.email = email
        if not user.is_active:
            user.is_active = True
        user.save()

        # Asignar al grupo "Portal" (debe existir)
        portal_group, _ = Group.objects.get_or_create(name="Portal")
        user.groups.add(portal_group)

        # Ligar al cliente
        cliente.user_portal = user
        cliente.portal_activo = True
        cliente.save(update_fields=["user_portal", "portal_activo"])

        # Enviar correo para establecer contraseña (usa el flujo estándar de reset)
        form = PasswordResetForm(data={"email": email})
        if form.is_valid():
            # Debe existir tu template registration/password_reset_email.html (recomendado)
            form.save(
                request=request,
                use_https=request.is_secure(),
                from_email=None,  # usa DEFAULT_FROM_EMAIL
                email_template_name="registration/password_reset_email.html",
                subject_template_name="registration/password_reset_subject.txt",
            )
            messages.success(request, f"Acceso creado. Se envió correo de activación a {email}.")
        else:
            messages.success(request, "Acceso creado, pero no se pudo enviar el correo de activación.")

        return redirect("cotizador_agentes:cotizacion_detail", folio=folio)
