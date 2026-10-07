from django.test import TestCase
from django.urls import reverse

from idiet.db_context import use_database
from Users.models import User


class LoginDatabaseEnvironmentSessionTests(TestCase):
    """Regresión: `database_environment` no debe perderse cuando un mismo
    navegador (misma sesión) inicia sesión como un usuario distinto sin
    cerrar sesión antes.

    `django.contrib.auth.login()` llama a `request.session.flush()` cuando
    la sesión ya pertenece a un usuario autenticado distinto (pk diferente).
    `login_view` (Users/views.py) fija
    `request.session["database_environment"]` justo ANTES de llamar a
    `login()`, así que ese flush borra la clave sin que nadie la restaure
    después.
    """

    databases = {"default", "training"}

    def setUp(self):
        self.password_default = "ClientePass123!"
        self.password_training = "FormacionPass123!"

        # Usuario "de relleno" para que el pk del usuario de "default" no
        # coincida por casualidad con el del usuario de "training" (cada
        # base de datos de test tiene su propio autoincrement empezando en
        # 1). Así el escenario reproduce literalmente el caso del reviewer:
        # dos usuarios con pk distinta.
        User.objects.create_user(
            username="relleno@example.com",
            email="relleno@example.com",
            password="Relleno123!",
            first_name="Relleno",
            last_name="Uno",
        )

        self.user_default = User.objects.create_user(
            username="cliente@example.com",
            email="cliente@example.com",
            password=self.password_default,
            first_name="Cliente",
            last_name="Uno",
        )

        with use_database("training"):
            self.user_training = User.objects.db_manager("training").create_user(
                username="formacion@example.com",
                email="formacion@example.com",
                password=self.password_training,
                first_name="Formacion",
                last_name="Dos",
            )

        # Confirmamos que son usuarios distintos (pk distinta) para que el
        # `login()` de Django detecte el cambio de usuario y haga flush().
        self.assertNotEqual(self.user_default.pk, self.user_training.pk)

    def test_second_login_as_different_user_keeps_database_environment(self):
        login_url = reverse("login")

        first_response = self.client.post(
            login_url,
            {
                "email": "cliente@example.com",
                "password": self.password_default,
                "user_type": "clientes",
            },
        )
        self.assertRedirects(first_response, reverse("admin-home"))
        self.assertEqual(
            self.client.session.get("database_environment"),
            "default",
            "El primer login debería fijar el entorno 'default'.",
        )

        second_response = self.client.post(
            login_url,
            {
                "email": "formacion@example.com",
                "password": self.password_training,
                "user_type": "formacion",
            },
        )
        # No usamos assertRedirects (que sigue la redirección) porque el
        # login en sí ya se completa correctamente (302 a admin-home): lo
        # que se comprueba aquí es el contenido de la sesión justo después
        # del login, tal y como lo dejó `login_view`.
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(second_response.get("Location"), reverse("admin-home"))

        self.assertEqual(
            self.client.session.get("database_environment"),
            "training",
            "Tras iniciar sesión como un usuario distinto (Formación), "
            "database_environment debería ser 'training', pero "
            "auth.login() hace session.flush() y borra la clave que "
            "login_view fijó justo antes de llamar a login().",
        )


class PurgeUserDataTests(TestCase):
    """Borrado en bloque de los datos de un nutricionista (solo admins)."""

    def setUp(self):
        from datetime import date, datetime, timezone
        from decimal import Decimal

        from Appointments.models import Appointment
        from Dishes.models import Dish, DishProduct
        from FoodGroup.models import FoodGroup
        from Menus.models import Menu, MenuIntake
        from Menus.tests import make_client, make_dish, make_nutri, make_product
        from Intakes.models import Intake
        from Plantillas.models import Rule, Template, TemplateIntake
        from Products.models import ProductInactive
        from SuperGroup.models import SuperGroup

        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com', password='x', is_staff=True,
        )
        self.nutri_a = make_nutri('purge_a@example.com')
        self.nutri_b = make_nutri('purge_b@example.com')

        intake = Intake.objects.filter(status=True).first()
        shared_product = make_product('Arroz', kcal=350, prot=7, fat=1, carb=78)
        self.shared_dish = make_dish('Arroz blanco', Dish.DishType.MAIN, shared_product)
        food_group = FoodGroup.objects.create(name='Purga test')
        super_group = SuperGroup.objects.create(name='Purga SG')

        for nutri in (self.nutri_a, self.nutri_b):
            client = make_client(nutri)
            Appointment.objects.create(
                user=nutri, client=client,
                start_date=datetime(2026, 9, 1, 10, tzinfo=timezone.utc),
                end_date=datetime(2026, 9, 1, 11, tzinfo=timezone.utc),
            )
            own_product = make_product(f'Prod {nutri.id}', kcal=100, prot=1, fat=1, carb=1)
            own_product.user = nutri
            own_product.save()
            own_dish = make_dish(f'Plato {nutri.id}', Dish.DishType.MAIN, own_product, user=nutri)
            menu = Menu.objects.create(user=nutri, client=client, date_ini=date(2026, 9, 1), date_fin=date(2026, 9, 1))
            MenuIntake.objects.create(
                menu=menu, dish=own_dish, intake=intake, quantity=100, kcal=Decimal('100'),
                menu_day=0, intake_alias='Desayuno',
            )
            template = Template.objects.create(user=nutri, name='T', daily_kcal=0, duration=7)
            TemplateIntake.objects.create(
                template=template, dish=self.shared_dish, intake=intake, quantity=100,
                kcal=Decimal('350'), menu_day=0, intake_alias='Desayuno',
            )
            Rule.objects.create(
                user=nutri, super_group=super_group, min=1, max=2,
                frequency=Rule.Frequency.DAILY, level=1,
            )
            ProductInactive.objects.create(user=nutri, product=shared_product)
            food_group.users.add(nutri)

        self.food_group = food_group
        self.url = reverse('purge_user_data', args=[self.nutri_a.id])

    def _owned_counts(self, user):
        from Appointments.models import Appointment
        from Clients.models import Client
        from Dishes.models import Dish
        from Menus.models import Menu
        from Plantillas.models import Rule, Template
        from Products.models import Product, ProductInactive

        return [
            model.objects.filter(user=user).count()
            for model in (Client, Appointment, Menu, Template, Rule, Dish, Product, ProductInactive)
        ]

    def test_admin_purges_all_data_of_nutri_keeping_account_and_others(self):
        b_before = self._owned_counts(self.nutri_b)
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {'confirm_email': 'PURGE_A@example.com'})

        self.assertRedirects(response, reverse('list_users'))
        self.assertEqual(self._owned_counts(self.nutri_a), [0] * 8)
        self.assertTrue(User.objects.filter(id=self.nutri_a.id).exists())
        self.assertFalse(self.food_group.users.filter(id=self.nutri_a.id).exists())
        # Datos de B y catalogo compartido intactos.
        self.assertEqual(self._owned_counts(self.nutri_b), b_before)
        self.assertTrue(self.food_group.users.filter(id=self.nutri_b.id).exists())
        self.shared_dish.refresh_from_db()

    def test_get_shows_summary_without_deleting(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'purge_a@example.com')
        self.assertEqual(
            {item['key']: item['count'] for item in response.context['summary']}['clients'], 1,
        )
        self.assertEqual(response.context['foreign_rows'], 0)
        self.assertEqual(self._owned_counts(self.nutri_a), [1] * 8)

    def test_wrong_email_deletes_nothing(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {'confirm_email': 'purge_b@example.com'})

        self.assertRedirects(response, self.url)
        self.assertEqual(self._owned_counts(self.nutri_a), [1] * 8)

    def test_non_admin_gets_403_and_deletes_nothing(self):
        self.client.force_login(self.nutri_b)

        self.assertEqual(self.client.get(reverse('list_users')).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {'confirm_email': 'purge_a@example.com'}).status_code, 403)
        self.assertEqual(self._owned_counts(self.nutri_a), [1] * 8)

    def test_cannot_purge_admin_user(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('purge_user_data', args=[self.admin.id]))

        self.assertEqual(response.status_code, 404)

    def test_users_nav_link_only_for_admins(self):
        self.client.force_login(self.admin)
        list_response = self.client.get(reverse('list_users'))
        self.assertContains(list_response, 'purge_a@example.com')
        self.assertNotContains(list_response, '>admin@example.com<')
        self.assertContains(list_response, 'href="%s"' % reverse('list_users'))

        self.client.force_login(self.nutri_b)
        response = self.client.get(reverse('list_active_clients'))
        self.assertNotContains(response, 'href="%s"' % reverse('list_users'))

    def test_summary_warns_about_other_users_rows_using_nutri_dishes(self):
        from decimal import Decimal

        from Dishes.models import Dish
        from Menus.models import Menu, MenuIntake

        dish_a = Dish.objects.get(user=self.nutri_a)
        menu_b = Menu.objects.get(user=self.nutri_b)
        MenuIntake.objects.create(
            menu=menu_b, dish=dish_a, intake=MenuIntake.objects.first().intake, quantity=50,
            kcal=Decimal('50'), menu_day=0, intake_alias='Merienda',
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.context['foreign_rows'], 1)
        self.assertContains(response, 'otros usuarios')
