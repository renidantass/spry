from auth_api.data import AppDbContext
from auth_api.seeders.user_seeder import seed as seed_users


def seed(db: AppDbContext) -> None:
    seed_users(db)
