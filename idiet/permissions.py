from django.db.models import Q
from django.shortcuts import get_object_or_404
from Clients.models import Client


def is_admin_user(user):
    """True si el usuario tiene bypass de aislamiento (staff o superuser nativos de Django)."""
    return bool(user.is_staff or user.is_superuser)


def scoped_queryset(queryset, user, owner_field='user', include_unassigned=False):
    """Filtra `queryset` por el nutricionista propietario (`owner_field`), salvo que
    `user` sea staff/superuser, en cuyo caso devuelve el queryset sin filtrar.

    Si `include_unassigned` es True, se incluyen tambien los registros sin
    propietario (`owner_field` a NULL), tratados como catalogo global creado
    por el admin del sistema y visible para todos los usuarios."""
    if is_admin_user(user):
        return queryset
    if include_unassigned:
        return queryset.filter(Q(**{owner_field: user}) | Q(**{f'{owner_field}__isnull': True}))
    return queryset.filter(**{owner_field: user})


def visible_clients(user):
    """Queryset de Client visible para `user` (todos si admin, solo los propios si no)."""
    return scoped_queryset(Client.objects.all(), user)


def get_visible_client_or_404(user, **lookup):
    """Como get_object_or_404(Client, **lookup) pero respetando ownership."""
    return get_object_or_404(visible_clients(user), **lookup)
