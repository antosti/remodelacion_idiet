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
