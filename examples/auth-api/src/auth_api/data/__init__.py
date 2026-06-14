from spry.orm import DbContext

from auth_api.models import User


class AppDbContext(DbContext):
    __models__ = [User]
