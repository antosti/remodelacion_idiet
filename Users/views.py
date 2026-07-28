from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from idiet.db_context import use_database

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

