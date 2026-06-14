from spry import DbContext, PasswordHasher

from auth_api.models import User


def seed(db: DbContext) -> None:
    if db.users.all():
        return
    hasher = PasswordHasher()
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hasher.hash("admin123"),
        role="admin",
    )
    user = User(
        username="user1",
        email="user1@example.com",
        password_hash=hasher.hash("user123"),
        role="user",
    )
    db.users.add(admin)
    db.users.add(user)
    db.save_changes()
    print(f"Seeded {2} users")
