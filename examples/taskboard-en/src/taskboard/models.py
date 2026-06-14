from dataclasses import dataclass

from spry import DbContext, dbset, key, validate
from spry.validators import Required, MinLength


@dataclass(slots=True)
class Todo:
    id: int | None = key()
    title: str = \"\"
    done: bool = False


@dataclass(slots=True)
class CreateTodo:
    title: str = validate(Required(), MinLength(3))


class AppDbContext(DbContext):
    todos = dbset(Todo)
