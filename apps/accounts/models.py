from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"

    email = models.EmailField("correo", unique=True)
    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.ADMIN)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def is_admin(self):
        return self.is_active and self.role == self.Role.ADMIN
