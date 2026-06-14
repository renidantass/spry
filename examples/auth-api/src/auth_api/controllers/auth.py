from spry import PasswordHasher, Request, authorize, controller, get, post

from auth_api.data import AppDbContext
from auth_api.models import LoginRequest, RegisterRequest, User


@controller("/auth")
class AuthController:
    def __init__(self, db: AppDbContext) -> None:
        self.db = db
        self.hasher = PasswordHasher()

    @post("/register")
    def register(self, body: RegisterRequest):
        existing = self.db.users.first(username=body.username)
        if existing is not None:
            return {"error": "Username already taken"}, 409

        existing_email = self.db.users.first(email=body.email)
        if existing_email is not None:
            return {"error": "Email already registered"}, 409

        user = User(
            username=body.username,
            email=body.email,
            password_hash=self.hasher.hash_password(body.password),
            role="user",
        )
        self.db.users.add(user)
        self.db.save_changes()
        return {"message": "User created", "user": {"id": user.id, "username": user.username, "email": user.email}}, 201

    @post("/login")
    def login(self, body: LoginRequest, request: Request):
        user = self.db.users.first(username=body.username)
        if user is None or not self.hasher.verify(body.password, user.password_hash):
            return {"error": "Invalid credentials"}, 401

        token = request.services.jwt.create_token(
            {"sub": user.id, "username": user.username, "role": user.role}
        )
        return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}

    @get("/me")
    @authorize()
    def me(self, request: Request):
        user_id = request.user.id
        user = self.db.users.find(user_id)
        if user is None:
            return {"error": "User not found"}, 404
        return {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
