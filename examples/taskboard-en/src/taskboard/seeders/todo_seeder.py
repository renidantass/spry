import logging

from taskboard.data import AppDbContext
from taskboard.models import Todo

logger = logging.getLogger("spry.seed")


def seed(db: AppDbContext) -> None:
    if db.todos.count() > 0:
        return
    items = [
        Todo(title="Learn Spry"),
        Todo(title="Build an API"),
        Todo(title="Write tests"),
        Todo(title="Deploy to production"),
    ]
    for item in items:
        db.todos.add(item)
    db.save()
    logger.info("Seeded %d todos", len(items))
