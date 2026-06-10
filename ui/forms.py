from django import forms
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import datetime
from django import forms

from .forms_mixins import BootstrapFormMixin
from autos.models import Vehiculo, VehiculoCatalogo
from crm.models import Cliente
from cotizador.models import Cotizacion


class VehiculoFromCatalogoForm(forms.ModelForm):
    """
    Form mínimo para crear un Vehiculo a partir del catálogo
    durante el wizard de cotización.
    """

    # Campo auxiliar (no es FK directa en Vehiculo)
    catalogo_id = forms.ModelChoiceField(
        queryset=VehiculoCatalogo.objects.filter(is_active=True),
        label="Versión",
        required=True,
    )

    class Meta:
        model = Vehiculo   # 🔴 ESTA LÍNEA ES LA CLAVE
        fields = [
            "tipo_uso",
            "placas",
            "vin",
            "color",
            "valor_comercial",
        ]

class VehiculoFromCatalogoForm2(BootstrapFormMixin, forms.ModelForm):
    catalogo_id = forms.IntegerField()
    tipo_uso = forms.ChoiceField(choices=Vehiculo.TipoUso.choices)
    placas = forms.CharField(required=False, max_length=20)
    vin = forms.CharField(required=False, max_length=40)
    color = forms.CharField(required=False, max_length=40)
    valor_comercial = forms.DecimalField(required=False, max_digits=14, decimal_places=2)

class ClienteQuickCreateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "nombre_comercial",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "rfc",
            "telefono_principal",
            "email_principal",
            "origen",
            "notas",
        ]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_cliente",
            "nombre_comercial",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "contacto_nombre",
            "contacto_email",
            "contacto_telefono",
            "rfc",
            "curp",
            "email_principal",
            "telefono_principal",
            "estatus",
            "origen",
            "portal_activo",
            "user_portal",
            "owner",
            "notas",
        ]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "estatus": forms.Select(attrs={"class": "form-select"}),
            "portal_activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notas": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap para inputs estándar
        for name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ["CheckboxInput", "Select"]:
                field.widget.attrs.setdefault("class", "form-control")

        # Placeholders útiles (opcional)
        self.fields["nombre_comercial"].widget.attrs.setdefault("placeholder", "Ej. Ferretería López SA de CV")
        self.fields["nombre"].widget.attrs.setdefault("placeholder", "Ej. Juan")
        self.fields["apellido_paterno"].widget.attrs.setdefault("placeholder", "Ej. Pérez")
        self.fields["email_principal"].widget.attrs.setdefault("placeholder", "correo@dominio.com")
        self.fields["telefono_principal"].widget.attrs.setdefault("placeholder", "10 dígitos")

    def clean(self):
        cleaned = super().clean()

        tipo = (cleaned.get("tipo_cliente") or "").strip()

        # Normaliza strings (evita "   ")
        def norm(v):
            return (v or "").strip()

        nombre_comercial = norm(cleaned.get("nombre_comercial"))
        nombre = norm(cleaned.get("nombre"))
        ap_pat = norm(cleaned.get("apellido_paterno"))
        rfc = norm(cleaned.get("rfc"))
        curp = norm(cleaned.get("curp"))

        # Re-asigna normalizados
        cleaned["nombre_comercial"] = nombre_comercial
        cleaned["nombre"] = nombre
        cleaned["apellido_paterno"] = ap_pat
        cleaned["rfc"] = rfc
        cleaned["curp"] = curp

        # Validación por tipo
        if tipo == Cliente.TipoCliente.EMPRESA:
            if not nombre_comercial:
                self.add_error("nombre_comercial", "Para Empresa, el nombre comercial es obligatorio.")

            # Opcional: exigir RFC a empresas
            # (descomenta si lo quieres obligatorio)
            # if not rfc:
            #     self.add_error("rfc", "Para Empresa, el RFC es obligatorio.")

            # Recomendación: para empresa, nombre/apellidos pueden quedar vacíos.
            # No los forzamos.

        elif tipo == Cliente.TipoCliente.PERSONA:
            if not nombre:
                self.add_error("nombre", "Para Persona, el nombre es obligatorio.")
            if not ap_pat:
                self.add_error("apellido_paterno", "Para Persona, el apellido paterno es obligatorio.")

            # Opcional: exigir CURP a persona
            # (descomenta si lo quieres obligatorio)
            # if not curp:
            #     self.add_error("curp", "Para Persona, la CURP es obligatoria.")

            # Recomendación: nombre_comercial puede quedar vacío.

        else:
            # Si por alguna razón llega vacío/incorrecto
            self.add_error("tipo_cliente", "Selecciona el tipo de cliente.")

        return cleaned

from datetime import timedelta

class CotizacionDatosForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ["vigencia_desde", "vigencia_hasta", "forma_pago_preferida", "notas"]

        widgets = {
            "vigencia_desde": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "vigencia_hasta": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
            "forma_pago_preferida": forms.Select(attrs={"class": "form-select"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vigencia_desde"].input_formats = ["%Y-%m-%d"]
        self.fields["vigencia_hasta"].input_formats = ["%Y-%m-%d"]
#        self.fields["forma_pago_preferida"].widget.attrs.update({
#            "class": "form-select"
#        })

        # Solo en GET (no bound) y solo si vienen vacías en la instancia
        if not self.is_bound:
            today = timezone.localdate()

            if not self.instance.vigencia_desde:
                self.initial.setdefault("vigencia_desde", today)

            if not self.instance.vigencia_hasta:
                self.initial.setdefault("vigencia_hasta", today + timedelta(days=365))

            if not (self.instance.forma_pago_preferida or "").strip():
                self.initial.setdefault("forma_pago_preferida", "CONTADO")
    
    def clean(self):
        cleaned = super().clean()
        d = cleaned.get("vigencia_desde")
        h = cleaned.get("vigencia_hasta")
        if d and h and h <= d:
            self.add_error("vigencia_hasta", "La vigencia hasta debe ser mayor a la vigencia desde.")
        return cleaned

    @staticmethod
    def initial_defaults():
        today = timezone.localdate()
        return {
            "vigencia_desde": today,
            "vigencia_hasta": today + timedelta(days=365),
            "forma_pago_preferida": "CONTADO",
        }


# AUTOS - MARCAS, SUBMARCAS, CATALOGO DE VEHICULOS, VEHICULOS

from autos.models import Marca, SubMarca, VehiculoCatalogo, Vehiculo

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Toyota"}),
        }


class SubMarcaForm(forms.ModelForm):
    class Meta:
        model = SubMarca
        fields = ["marca", "nombre"]
        widgets = {
            "marca": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Corolla"}),
        }


class VehiculoCatalogoForm(forms.ModelForm):

    class Meta:
        model = VehiculoCatalogo
        fields = [
            "marca",
            "submarca",
            "anio",
            "version",
            "clave_amis",
            "tipo_vehiculo",
            "valor_referencia",
        ]

        widgets = {
            "marca": forms.Select(attrs={"class": "form-select"}),
            "submarca": forms.Select(attrs={"class": "form-select"}),
            "anio": forms.Select(attrs={"class": "form-select"}),
            "version": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. GLI 2.0 Turbo DSG, LE CVT, XLE, LT..."
                }
            ),
            "clave_amis": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_vehiculo": forms.TextInput(attrs={"class": "form-control"}),
            "valor_referencia": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lista de años
        current_year = datetime.now().year

        YEARS = [
            (y, y)
            for y in range(current_year + 1, 1950 - 1, -1)
        ]

        self.fields["anio"].widget.choices = YEARS

        # Submarcas dependientes
        self.fields["submarca"].queryset = SubMarca.objects.none()

        if self.instance and self.instance.pk:
            self.fields["submarca"].queryset = SubMarca.objects.filter(
                marca=self.instance.marca
            ).order_by("nombre")

        marca_id = self.data.get("marca")

        if marca_id:
            self.fields["submarca"].queryset = SubMarca.objects.filter(
                marca_id=marca_id
            ).order_by("nombre")            
    

class VehiculoForm(forms.ModelForm):
    marca = forms.ModelChoiceField(
        queryset=Marca.objects.filter(is_active=True).order_by("nombre"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_marca_ajax"}),
        label="Marca"
    )

    submarca = forms.ModelChoiceField(
        queryset=SubMarca.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_submarca_ajax"}),
        label="Submarca"
    )

    class Meta:
        model = Vehiculo
        fields = [
            "cliente",
            "catalogo",
            "tipo_uso",
            "marca_texto",
            "submarca_texto",
            "modelo_anio",
            "version",
            "vin",
            "serie_motor",
            "placas",
            "color",
            "tipo_vehiculo",
            "valor_comercial",
            "adaptaciones",
        ]

        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "catalogo": forms.Select(attrs={"class": "form-select", "id": "id_catalogo_ajax"}),
            "tipo_uso": forms.Select(attrs={"class": "form-select"}),
            "marca_texto": forms.HiddenInput(attrs={"id": "id_marca_texto"}),
            "submarca_texto": forms.HiddenInput(attrs={"id": "id_submarca_texto"}),
            "version": forms.HiddenInput(attrs={"id": "id_version"}),
            "tipo_vehiculo": forms.HiddenInput(attrs={"id": "id_tipo_vehiculo"}),
            "modelo_anio": forms.Select(attrs={"class": "form-select", "id": "id_modelo_anio"}),
            "vin": forms.TextInput(attrs={"class": "form-control"}),
            "serie_motor": forms.TextInput(attrs={"class": "form-control"}),
            "placas": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "valor_comercial": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "id": "id_valor_comercial"}),
            "adaptaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = datetime.now().year
        years = [(y, y) for y in range(current_year + 1, 1950 - 1, -1)]
        self.fields["modelo_anio"].widget.choices = years

        self.fields["catalogo"].queryset = VehiculoCatalogo.objects.filter(
            is_active=True
        ).select_related("marca", "submarca").order_by("-anio", "marca__nombre", "submarca__nombre")

        # Editar vehículo existente
        if self.instance and self.instance.pk and self.instance.catalogo:
            catalogo = self.instance.catalogo

            self.fields["marca"].initial = catalogo.marca_id
            self.fields["submarca"].queryset = SubMarca.objects.filter(
                marca=catalogo.marca,
                is_active=True
            ).order_by("nombre")
            self.fields["submarca"].initial = catalogo.submarca_id

        # POST con marca seleccionada
        marca_id = self.data.get("marca")
        if marca_id:
            self.fields["submarca"].queryset = SubMarca.objects.filter(
                marca_id=marca_id,
                is_active=True
            ).order_by("nombre")


# USUARIOS

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from accounts.models import UserProfile

User = get_user_model()


class UsuarioCreateForm(forms.ModelForm):
    rol = forms.ChoiceField(
        choices=UserProfile.Rol.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = True

        if commit:
            user.save()

            rol = self.cleaned_data["rol"]
            group, _ = Group.objects.get_or_create(name=rol.title())
            user.groups.set([group])

            perfil, _ = UserProfile.objects.get_or_create(user=user)
            perfil.rol = rol
            perfil.telefono = self.cleaned_data.get("telefono", "")
            perfil.save()

        return user


class UsuarioUpdateForm(forms.ModelForm):
    rol = forms.ChoiceField(
        choices=UserProfile.Rol.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        perfil = getattr(self.instance, "perfil", None)

        if perfil:
            self.fields["rol"].initial = perfil.rol
            self.fields["telefono"].initial = perfil.telefono

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()

            rol = self.cleaned_data["rol"]
            group, _ = Group.objects.get_or_create(name=rol.title())
            user.groups.set([group])

            perfil, _ = UserProfile.objects.get_or_create(user=user)
            perfil.rol = rol
            perfil.telefono = self.cleaned_data.get("telefono", "")
            perfil.save()

        return user
    