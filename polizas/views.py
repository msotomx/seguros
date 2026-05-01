from django.views import View
from django.views.generic import CreateView, UpdateView

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from polizas.models import Endoso, Poliza
from polizas.services import crear_endoso
from polizas.forms import EndosoForm
from django.contrib import messages
from polizas.services import crear_endoso, editar_endoso, eliminar_endoso


class EndosoCreateView(CreateView):
    model = Endoso
    form_class = EndosoForm
    template_name = "ui/polizas/endoso_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.poliza = get_object_or_404(Poliza, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["fecha"] = timezone.localdate().strftime("%Y-%m-%d")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["poliza"] = self.poliza
        return context

    def form_valid(self, form):
        crear_endoso(
            poliza=self.poliza,
            tipo_endoso=form.cleaned_data["tipo_endoso"],
            descripcion=form.cleaned_data.get("descripcion"),
            prima_ajuste=form.cleaned_data.get("prima_ajuste"),
            fecha=form.cleaned_data.get("fecha"),
            documento=form.cleaned_data.get("documento"),
            usuario=self.request.user,
        )

        return redirect(reverse("ui:poliza_detail", kwargs={"pk": self.poliza.pk}))


class EndosoUpdateView(UpdateView):
    model = Endoso
    form_class = EndosoForm
    template_name = "ui/polizas/endoso_form.html"
    context_object_name = "endoso"

    def get_queryset(self):
        return Endoso.objects.select_related("poliza", "documento")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["poliza"] = self.object.poliza
        context["modo"] = "editar"
        context["titulo"] = "Editar endoso"
        return context

    def form_valid(self, form):
        editar_endoso(
            endoso=self.object,
            tipo_endoso=form.cleaned_data["tipo_endoso"],
            descripcion=form.cleaned_data.get("descripcion"),
            prima_ajuste=form.cleaned_data.get("prima_ajuste"),
            fecha=form.cleaned_data.get("fecha"),
            documento=form.cleaned_data.get("documento"),
            usuario=self.request.user,
        )
        messages.success(self.request, "El endoso se actualizó correctamente.")
        return redirect("ui:poliza_detail", pk=self.object.poliza.pk)


class EndosoDeleteView(View):
    def post(self, request, pk):
        endoso = get_object_or_404(Endoso.objects.select_related("poliza"), pk=pk)
        poliza_id = endoso.poliza_id
        eliminar_endoso(endoso=endoso, usuario=request.user)
        messages.success(request, "El endoso se eliminó correctamente.")
        return redirect("ui:poliza_detail", pk=poliza_id)
