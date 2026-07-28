from contextlib import contextmanager
from contextvars import ContextVar


ALLOWED_DATABASE_ALIASES = {"default", "training"}
_database_alias = ContextVar("idiet_database_alias", default="default")


def get_database_alias():
    return _database_alias.get()


def set_database_alias(alias):
    if alias not in ALLOWED_DATABASE_ALIASES:
        alias = "default"
    return _database_alias.set(alias)


def reset_database_alias(token):
    _database_alias.reset(token)


@contextmanager
def use_database(alias):
    token = set_database_alias(alias)
    try:
        yield
    finally:
        reset_database_alias(token)
