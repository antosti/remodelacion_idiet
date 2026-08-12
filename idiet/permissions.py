from django.shortcuts import get_object_or_404
from Clients.models import Client


def is_admin_user(user):
    """True si el usuario tiene bypass de aislamiento (staff o superuser nativos de Django)."""
    return bool(user.is_staff or user.is_superuser)


def scoped_queryset(queryset, user, owner_field='user'):
    """Filtra `queryset` por el nutricionista propietario (`owner_field`), salvo que
    `user` sea staff/superuser, en cuyo caso devuelve el queryset sin filtrar."""
    if is_admin_user(user):
        return queryset
    return queryset.filter(**{owner_field: user})


def visible_clients(user):
    """Queryset de Client visible para `user` (todos si admin, solo los propios si no)."""
    return scoped_queryset(Client.objects.all(), user)


def get_visible_client_or_404(user, **lookup):
    """Como get_object_or_404(Client, **lookup) pero respetando ownership."""
    return get_object_or_404(visible_clients(user), **lookup)
