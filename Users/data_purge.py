"""Borrado en bloque de todos los datos de un nutricionista (accion solo para
admins, ver Users.views.purge_user_data_view). La cuenta del usuario se
conserva; lo compartido (Product/Dish con user=NULL) y lo de otros
nutricionistas no se toca, salvo filas que referencien platos/alimentos
propios del usuario (ver `foreign_rows`), que caen en cascada."""
from django.db import transaction

from Appointments.models import Appointment
from Clients.models import Client
from Dishes.models import Dish, DishProduct
from FoodGroup.models import FoodGroup
from Menus.models import Menu, MenuIntake
from Plantillas.models import Rule, Template, TemplateIntake
from Products.models import Product, ProductInactive

# (clave, etiqueta, funcion -> queryset propio del usuario), en el orden en
# que se muestran y se borran (de hijos a padres).
_OWNED = [
    ('appointments', 'Citas', lambda user: Appointment.objects.filter(user=user)),
    ('menus', 'Dietas', lambda user: Menu.objects.filter(user=user)),
    ('clients', 'Clientes', lambda user: Client.objects.filter(user=user)),
    ('templates', 'Plantillas', lambda user: Template.objects.filter(user=user)),
    ('rules', 'Reglas', lambda user: Rule.objects.filter(user=user)),
    ('dishes', 'Platos propios', lambda user: Dish.objects.filter(user=user)),
    ('products', 'Alimentos propios', lambda user: Product.objects.filter(user=user)),
    ('inactive_products', 'Alimentos marcados como inactivos', lambda user: ProductInactive.objects.filter(user=user)),
]


def foreign_rows(user):
    """Filas de OTROS usuarios que se borrarian en cascada por usar platos o
    alimentos propios de `user` (solo posible si un admin los uso)."""
    return (
        MenuIntake.objects.filter(dish__user=user).exclude(menu__user=user).count()
        + TemplateIntake.objects.filter(dish__user=user).exclude(template__user=user).count()
        + DishProduct.objects.filter(product__user=user).exclude(dish__user=user).count()
    )


def user_data_summary(user):
    """Lista de {'key', 'label', 'count'} con lo que se borraria."""
    return [
        {'key': key, 'label': label, 'count': queryset(user).count()}
        for key, label, queryset in _OWNED
    ]


def purge_user_data(user):
    """Borra todos los datos de `user` en una transaccion y devuelve el
    resumen previo al borrado. El propio usuario no se borra."""
    with transaction.atomic():
        summary = user_data_summary(user)
        for _key, _label, queryset in _OWNED:
            queryset(user).delete()
        FoodGroup.users.through.objects.filter(user=user).delete()
    return summary
