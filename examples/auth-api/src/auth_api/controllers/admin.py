from auth_api.data import AppDbContext
from spry.auth import authorize
from spry.routing import controller, get


@controller("/admin")
class AdminController:
    def __init__(self, db: AppDbContext) -> None:
        self.db = db

    @get("/users")
    @authorize(roles=["admin"])
    def list_users(self):
        return self.db.users.all()
