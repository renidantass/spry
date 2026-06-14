from dataclasses import dataclass

from spry.orm import key
from spry.validation import validate
from spry.validators import MinLength, Required


@dataclass(slots=True)
class Todo:
    id: int | None = key()
    title: str = ""
    done: bool = False


@dataclass(slots=True)
class CreateTodo:
    title: str = validate(Required(), MinLength(3))
