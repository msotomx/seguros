from django.db import models

# Create your models here.
# ---------------------------------------------------------------------
# Base / Utilidades
# ---------------------------------------------------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


class MoneyMixin(models.Model):
    # Si manejas multi-moneda, agrega moneda. Si no, puedes fijarla a MXN.
    moneda = models.CharField(max_length=3, default="MXN", db_index=True)

    class Meta:
        abstract = True
