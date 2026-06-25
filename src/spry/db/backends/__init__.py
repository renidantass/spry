from spry.db.url import DatabaseUrl, parse_database_url

_BACKENDS: dict[str, type] = {}


def register_backend(protocol: str, backend_cls: type) -> None:
    _BACKENDS[protocol] = backend_cls


def get_backend(database_url: str | DatabaseUrl) -> type:
    if isinstance(database_url, str):
        parsed = parse_database_url(database_url)
    else:
        parsed = database_url

    cls = _BACKENDS.get(parsed.protocol)
    if cls is None:
        msg = f"Unsupported database protocol '{parsed.protocol}'. "
        msg += f"Available: {', '.join(sorted(_BACKENDS))}" if _BACKENDS else "No backends registered."
        raise ValueError(msg)
    return cls()


from spry.db.backends.sqlite import SqliteBackend

register_backend("sqlite", SqliteBackend)


try:
    from spry.db.backends.postgres import PostgresBackend
    register_backend("postgresql", PostgresBackend)
except ImportError:
    pass

try:
    from spry.db.backends.mysql import MySqlBackend
    register_backend("mysql", MySqlBackend)
except ImportError:
    pass

try:
    from spry.db.backends.mariadb import MariaDBBackend
    register_backend("mariadb", MariaDBBackend)
except ImportError:
    pass

try:
    from spry.db.backends.sqlserver import SqlServerBackend
    register_backend("mssql", SqlServerBackend)
except ImportError:
    pass
