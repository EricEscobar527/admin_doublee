from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.app_list, name="list"),
    path("nueva/", views.app_create, name="create"),
    path("<int:pk>/editar/", views.app_edit, name="edit"),
    path("<int:pk>/eliminar/", views.app_delete, name="delete"),
    path("<int:pk>/regenerar-token/", views.app_regenerate_token, name="regenerate_token"),
]
