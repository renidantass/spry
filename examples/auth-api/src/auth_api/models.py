from dataclasses import dataclass, field

from spry import DbContext, dbset, key, validate
from spry.validators import Email, MinLength, Required


@dataclass(slots=True)
class User:
    id: int | None = key()
    username: str = \"\"
    email: str = \"\"
    password_hash: str = \"\"
    role: str = \"user\"


@dataclass(slots=True)
class RegisterRequest:
    username: str = validate(Required(), MinLength(3))
    email: str = validate(Required(), Email())
    password: str = validate(Required(), MinLength(6))


@dataclass(slots=True)
class LoginRequest:
    username: str = validate(Required())
    password: str = validate(Required())


class AppDbContext(DbContext):
    users = dbset(User)
