from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("<int:pk>/actualizar/", views.ticket_update, name="update"),
    path("<int:pk>/eliminar/", views.ticket_delete, name="delete"),
    path("imagen/<int:pk>/", views.attachment_file, name="attachment"),
]
