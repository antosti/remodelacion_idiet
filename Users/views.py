from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from idiet.db_context import ALLOWED_DATABASE_ALIASES, use_database
from Users.models import User


def normalize_environment(user_type):
    selected_environment = user_type if user_type in {"clientes", "formacion"} else "clientes"
    database_alias = "training" if selected_environment == "formacion" else "default"
    return selected_environment, database_alias


def build_reset_link(request, database_alias, user):
    uidb64 = urlsafe_base64_encode(force_bytes(f"{database_alias}:{user.pk}"))
    token = default_token_generator.make_token(user)
    path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


# Create your views here.
def login_view(request):
    selected_environment = "clientes"

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        selected_environment = request.POST.get("user_type", "clientes")
        if selected_environment not in {"clientes", "formacion"}:
            selected_environment = "clientes"
        database_alias = (
            "training" if selected_environment == "formacion" else "default"
        )

        with use_database(database_alias):
            user = authenticate(
                request,
                username=email,
                password=password
            )

            if user is not None:
                request.session["database_environment"] = database_alias
                request.database_alias = database_alias
                login(request, user)
                messages.success(request, "Inicio de sesión correcto")
                return redirect("admin-home")

        messages.error(request, "Email o contraseña incorrectos")

    return render(
        request,
        "login.html",
        {"selected_environment": selected_environment},
    )

@login_required
def logout_view(request):
    logout(request)
    return redirect("home")


def password_reset_request(request):
    selected_environment = "clientes"

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        selected_environment, database_alias = normalize_environment(request.POST.get("user_type"))

        with use_database(database_alias):
            user = User.objects.filter(email=email).first()
            if user is not None:
                reset_link = build_reset_link(request, database_alias, user)
                html_message = render_to_string(
                    "emails/password_reset_email.html",
                    {"user": user, "reset_link": reset_link},
                )
                send_mail(
                    subject="Recupera tu contraseña - iDiet",
                    message=(
                        "Para restablecer tu contraseña, accede a este enlace "
                        f"(caduca en 30 minutos): {reset_link}"
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                    html_message=html_message,
                )

        messages.success(
            request,
            "Si el correo está registrado, recibirás en breve un enlace para restablecer tu contraseña.",
        )
        return redirect("password_reset_request")

    return render(
        request,
        "password_reset_request.html",
        {"selected_environment": selected_environment},
    )


def password_reset_confirm(request, uidb64, token):
    alias = None
    pk = None
    try:
        decoded = force_str(urlsafe_base64_decode(uidb64))
        alias, pk = decoded.split(":", 1)
    except (TypeError, ValueError, UnicodeDecodeError):
        pass

    if alias not in ALLOWED_DATABASE_ALIASES:
        alias = None

    user = None
    if alias and pk:
        with use_database(alias):
            candidate = User.objects.filter(pk=pk).first()
            if candidate is not None and default_token_generator.check_token(candidate, token):
                user = candidate

    if user is None:
        return render(request, "password_reset_confirm.html", {"valid_link": False})

    if request.method == "POST":
        password1 = request.POST.get("new_password1", "")
        password2 = request.POST.get("new_password2", "")

        if not password1 or password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(
                request,
                "password_reset_confirm.html",
                {"valid_link": True, "uidb64": uidb64, "token": token},
            )

        try:
            validate_password(password1, user=user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(
                request,
                "password_reset_confirm.html",
                {"valid_link": True, "uidb64": uidb64, "token": token},
            )

        with use_database(alias):
            user.set_password(password1)
            user.save()

        messages.success(request, "Tu contraseña se ha actualizado correctamente. Ya puedes iniciar sesión.")
        return redirect("login")

    return render(
        request,
        "password_reset_confirm.html",
        {"valid_link": True, "uidb64": uidb64, "token": token},
    )

