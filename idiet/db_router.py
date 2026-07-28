from .db_context import ALLOWED_DATABASE_ALIASES, get_database_alias


class EnvironmentDatabaseRouter:
    """Mantiene todas las operaciones de una petición en el mismo entorno."""

    def db_for_read(self, model, **hints):
        return get_database_alias()

    def db_for_write(self, model, **hints):
        instance = hints.get("instance")
        if instance is not None and instance._state.db:
            return instance._state.db
        return get_database_alias()

    def allow_relation(self, obj1, obj2, **hints):
        database_1 = obj1._state.db or get_database_alias()
        database_2 = obj2._state.db or get_database_alias()
        return database_1 == database_2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db in ALLOWED_DATABASE_ALIASES
