from spry import AppBuilder

from taskboard.data import AppDbContext


def server_header(context, next_handler):
    response = next_handler()
    response.headers.setdefault("X-Powered-By", "Spry")
    return response


def create_app():
    builder = AppBuilder()
    builder.use(server_header)
    builder.add_db_context(AppDbContext)
    app = builder.build()

    scope = app.create_scope()
    try:
        db = scope.resolve(AppDbContext)
        db.ensure_created()
    finally:
        scope.dispose()

    return app
