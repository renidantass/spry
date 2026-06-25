from auth_api.models import User
from spry.orm import DbContext


class AppDbContext(DbContext):
    models = [User]
