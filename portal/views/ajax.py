from django.http import JsonResponse

from autos.models import SubMarca, VehiculoCatalogo


def portal_ajax_submarcas_por_marca(request):
    marca_id = request.GET.get("marca_id")

    submarcas = SubMarca.objects.filter(
        marca_id=marca_id,
        is_active=True
    ).order_by("nombre")

    data = [
        {
            "id": s.id,
            "nombre": s.nombre,
        }
        for s in submarcas
    ]

    return JsonResponse({"results": data})


def portal_ajax_catalogos_por_submarca(request):
    submarca_id = request.GET.get("submarca_id")
    anio = request.GET.get("anio")

    qs = VehiculoCatalogo.objects.filter(
        submarca_id=submarca_id,
        is_active=True,
    ).select_related("marca", "submarca").order_by("-anio", "version")

    if anio:
        qs = qs.filter(anio=anio)

    data = [
        {
            "id": v.id,
            "label": str(v),
        }
        for v in qs
    ]

    return JsonResponse({"results": data})
