from taskboard.data import AppDbContext
from taskboard.seeders.todo_seeder import seed as seed_todos


def seed(db: AppDbContext) -> None:
    seed_todos(db)
