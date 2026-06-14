from spry import AppBuilder

from auth_api.models import AppDbContext


def cors_dev(context, next_handler):
    response = next_handler()
    response.headers[\"Access-Control-Allow-Origin\"] = \"*\"
    response.headers[\"Access-Control-Allow-Methods\"] = \"GET, POST, PUT, DELETE, OPTIONS\"
    response.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization\"
    return response


def create_app():
    builder = AppBuilder()
    builder.use(cors_dev)
    builder.add_db_context(AppDbContext)
    builder.add_jwt_auth(secret_key=\"change-me-in-production\")
    builder.add_rate_limiter(max_requests=60, window=60)

    app = builder.build()

    scope = app.create_scope()
    try:
        db = scope.resolve(AppDbContext)
        db.ensure_created()
    finally:
        scope.dispose()

    return app
