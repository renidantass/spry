from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(slots=True)
class DatabaseUrl:
    protocol: str
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    database: str = ""


_PROTOCOL_MAP = {
    "sqlite": "sqlite",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pgsql": "postgresql",
    "mysql": "mysql",
    "mariadb": "mariadb",
    "mssql": "mssql",
    "sqlserver": "mssql",
}


def parse_database_url(url: str) -> DatabaseUrl:
    if "://" not in url:
        return DatabaseUrl(protocol="sqlite", database=url)

    parsed = urlparse(url)
    protocol = _PROTOCOL_MAP.get(parsed.scheme, parsed.scheme)
    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    host = parsed.hostname
    port = parsed.port
    database = parsed.path.lstrip("/") if parsed.path else ""

    if protocol == "sqlite":
        if host and host != ":memory:":
            path = f"{host}/{database}" if database else host
            return DatabaseUrl(protocol="sqlite", database=path)
        database = ":memory:" if host == ":memory:" else database
        return DatabaseUrl(protocol="sqlite", database=database)

    return DatabaseUrl(
        protocol=protocol,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )
