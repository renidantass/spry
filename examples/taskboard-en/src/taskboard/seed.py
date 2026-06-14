from spry import DbContext

from taskboard.models import Todo


def seed(db: DbContext):
    if db.todos.all():
        return
    items = [
        Todo(title=\"Learn Spry\"),
        Todo(title=\"Build an API\"),
        Todo(title=\"Write tests\"),
        Todo(title=\"Deploy to production\"),
    ]
    for item in items:
        db.todos.add(item)
    db.save_changes()
    print(f\"Seeded {len(items)} todos\")
