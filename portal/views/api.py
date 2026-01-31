from django.http import JsonResponse
from django.views import View

from autos.models import SubMarca, VehiculoCatalogo


class SubmarcasPorMarcaView(View):
    def get(self, request):
        marca_id = request.GET.get("marca_id")
        qs = SubMarca.objects.filter(marca_id=marca_id, is_active=True).order_by("nombre")
        data = [{"id": x.id, "nombre": x.nombre} for x in qs]
        return JsonResponse({"results": data})


class CatalogoPorFiltroView(View):
    def get(self, request):
        marca_id = request.GET.get("marca_id")
        submarca_id = request.GET.get("submarca_id")
        anio = request.GET.get("anio")

        qs = VehiculoCatalogo.objects.all()

        if marca_id:
            qs = qs.filter(marca_id=marca_id)
        if submarca_id:
            qs = qs.filter(submarca_id=submarca_id)
        if anio:
            qs = qs.filter(anio=anio)

        qs = qs.order_by("version")

        data = [{"id": x.id, "label": (x.version or "Sin versión")} for x in qs]
        return JsonResponse({"results": data})
