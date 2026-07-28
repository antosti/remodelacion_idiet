from .db_context import reset_database_alias, set_database_alias


class DatabaseEnvironmentMiddleware:
    """Selecciona la base antes de que AuthenticationMiddleware cargue al usuario."""

    session_key = "database_environment"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        alias = request.session.get(self.session_key, "default")
        token = set_database_alias(alias)
        request.database_alias = alias
        try:
            return self.get_response(request)
        finally:
            reset_database_alias(token)
