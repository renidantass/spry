from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from spry.cli import _run_seed
from spry.orm import DbContext, dbset, key


@dataclass(slots=True)
class SeedTodo:
    id: int | None = key()
    title: str = ""


class SeedContext(DbContext):
    todos = dbset(SeedTodo)


def seed_data(db: SeedContext) -> None:
    db.todos.add(SeedTodo(title="seeded"))


class CliTests(unittest.TestCase):
    def test_seed_command_executes_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "seed.db"
            _run_seed(__name__ + ":seed_data", __name__ + ":SeedContext", str(db_path))

            db = SeedContext(str(db_path))
            try:
                self.assertEqual(db.todos.count(), 1)
                self.assertEqual(db.todos.all()[0].title, "seeded")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
