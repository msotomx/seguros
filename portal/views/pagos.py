# aqui va todo lo relacionado a pagos del portal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic import TemplateView

from finanzas.models import Pago
from finanzas.services.checkout import crear_checkout_pago

def pagos_portal_visibles_para_usuario(user):
    return Pago.objects.filter(
        cliente__user_portal=user,
        cliente__portal_activo=True,
    )

class PortalPagoListView(LoginRequiredMixin, ListView):
    template_name = "portal/pagos_list.html"
    context_object_name = "pagos"

    def get_queryset(self):
        return pagos_portal_visibles_para_usuario(self.request.user)


class PortalPagoDetailView(LoginRequiredMixin, DetailView):
    model = Pago
    template_name = "portal/pago_detail.html"
    context_object_name = "pago"

    def get_queryset(self):
        return pagos_portal_visibles_para_usuario(self.request.user)


class PortalPagoCheckoutView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pago = get_object_or_404(
            pagos_portal_visibles_para_usuario(request.user),
            pk=kwargs["pk"],
        )

        result = crear_checkout_pago(pago, request=request, actor=request.user)
        return redirect(result["checkout_url"])


class PortalPagoReturnView(LoginRequiredMixin, TemplateView):
    template_name = "portal/pago_checkout_return.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status"] = self.kwargs.get("status")
        return ctx

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from finanzas.models import Pago
from finanzas.services.checkout import crear_checkout_pago

def pagos_portal_visibles_para_usuario(user):
    return (
        Pago.objects
        .select_related("cliente", "poliza", "poliza__cliente", "comprobante")
        .filter(
            Q(cliente__user_portal=user, cliente__portal_activo=True) |
            Q(poliza__cliente__user_portal=user, poliza__cliente__portal_activo=True)
        )
        .distinct()
        .order_by("-fecha_programada", "-id")
    )

class PortalPagoListView(LoginRequiredMixin, ListView):
    template_name = "portal/pagos_list.html"
    context_object_name = "pagos"
    paginate_by = 20

    def get_queryset(self):
        qs = pagos_portal_visibles_para_usuario(self.request.user)

        filtro = self.request.GET.get("estatus", "").strip()
        if filtro:
            qs = qs.filter(estatus=filtro)

        solo_pendientes = self.request.GET.get("pendientes", "").strip()
        if solo_pendientes == "1":
            qs = qs.filter(
                estatus__in=[
                    Pago.Estatus.PENDIENTE,
                    Pago.Estatus.EN_PROCESO,
                    Pago.Estatus.VENCIDO,
                    Pago.Estatus.PENDIENTE_REVISION,
                    Pago.Estatus.PARCIAL,
                ]
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estatus_actual"] = self.request.GET.get("estatus", "").strip()
        context["solo_pendientes"] = self.request.GET.get("pendientes", "").strip()
        context["estatus_choices"] = Pago.Estatus.choices
        return context


class PortalPagoDetailView(LoginRequiredMixin, DetailView):
    model = Pago
    template_name = "portal/pago_detail.html"
    context_object_name = "pago"

    def get_queryset(self):
        return (
            pagos_portal_visibles_para_usuario(self.request.user)
            .prefetch_related("transacciones")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transacciones"] = self.object.transacciones.all().order_by("-created_at", "-id")
        return context


class PortalPagoCheckoutView(LoginRequiredMixin, View):
    """
    Genera el checkout del pago y redirige al usuario al provider.
    Debe invocarse por POST.
    """

    def post(self, request, *args, **kwargs):
        pago = get_object_or_404(
            pagos_portal_visibles_para_usuario(request.user),
            pk=kwargs["pk"],
        )

        try:
            result = crear_checkout_pago(
                pago=pago,
                request=request,
                actor=request.user,
            )
            return redirect(result["checkout_url"])

        except ValidationError as exc:
            if hasattr(exc, "messages") and exc.messages:
                for msg in exc.messages:
                    messages.error(request, msg)
            else:
                messages.error(request, "No fue posible iniciar el pago.")
            return redirect("portal:pago_detail", pk=pago.pk)

        except Exception:
            messages.error(
                request,
                "Ocurrió un problema al generar el enlace de pago. Intenta nuevamente.",
            )
            return redirect("portal:pago_detail", pk=pago.pk)

    def get(self, request, *args, **kwargs):
        messages.warning(request, "La acción de pago debe enviarse correctamente desde el formulario.")
        return redirect("portal:pago_detail", pk=kwargs["pk"])


class PortalPagoReturnView(LoginRequiredMixin, TemplateView):
    template_name = "portal/pago_checkout_return.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        status = self.kwargs.get("status", "")
        context["status"] = status

        if status == "success":
            context["titulo"] = "Pago enviado"
            context["mensaje"] = "Tu pago fue enviado correctamente al proveedor. Estamos validándolo."
        elif status == "pending":
            context["titulo"] = "Pago pendiente"
            context["mensaje"] = "Tu pago quedó pendiente de confirmación por parte del proveedor."
        else:
            context["titulo"] = "Pago no completado"
            context["mensaje"] = "El pago no se completó. Puedes intentarlo nuevamente."

        return context
