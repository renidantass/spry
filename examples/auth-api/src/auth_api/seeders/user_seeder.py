import logging

from auth_api.data import AppDbContext
from auth_api.models import User
from spry.auth import PasswordHasher

logger = logging.getLogger("spry.seed")


def seed(db: AppDbContext) -> None:
    if db.users.count() > 0:
        return
    hasher = PasswordHasher()
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hasher.hash_password("admin123"),
        role="admin",
    )
    user = User(
        username="user1",
        email="user1@example.com",
        password_hash=hasher.hash_password("user123"),
        role="user",
    )
    db.users.add(admin)
    db.users.add(user)
    db.save()
    logger.info("Seeded 2 users")
