from spry import AppBuilder

from taskboard.models import AppDbContext


def create_app():
    builder = AppBuilder()
    builder.add_db_context(AppDbContext)
    app = builder.build()

    scope = app.create_scope()
    try:
        db = scope.resolve(AppDbContext)
        db.ensure_created()
    finally:
        scope.dispose()

    return app
