from spry.app import AppBuilder
from taskboard.data import AppDbContext


def create_app():
    builder = AppBuilder()
    builder.add_db_context(AppDbContext)
    builder.discover_controllers("taskboard")
    app = builder.build()

    scope = app.create_scope()
    try:
        db = scope.resolve(AppDbContext)
        db.ensure_created()
    finally:
        scope.dispose()

    return app
