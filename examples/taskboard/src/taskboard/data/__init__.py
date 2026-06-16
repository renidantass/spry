from spry.orm import DbContext

from taskboard.models import Todo


class AppDbContext(DbContext):
    models = [Todo]
