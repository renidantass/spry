Auth API example with JWT authentication using Spry.

Demonstrates user registration, login, protected routes and role-based access control.

## Requirements

- Python 3.11+
- pip

## Local Setup

At the root of spry/, install the framework in editable mode:

`ash
pip install -e .
`

If you are inside examples/auth-api, you can use:

`ash
pip install -e ../../
`

## Structure

- main.py: simple entrypoint
- ppsettings.json: server, database and auth configuration
- src/auth_api/app.py: app bootstrap with JWT auth, CORS and rate limiting
- src/auth_api/controllers.py: AuthController (register, login, me) and AdminController
- src/auth_api/data.py: User entity, RegisterRequest, LoginRequest and AppDbContext
- src/auth_api/seed.py: initial admin/user seed

## Running

`ash
spry run --app auth_api.app:create_app
`

## Endpoints

| Method | Path | Auth Required | Description |
|---|---|---|---|
| POST | /auth/register | No | Register a new user |
| POST | /auth/login | No | Login, returns JWT token |
| GET | /auth/me | Yes | Get current user info |
| GET | /admin/users | Admin | List all users |

## Usage Examples

### Register

`ash
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"username": "johndoe", "email": "john@example.com", "password": "secret123"}'
`

### Login

`ash
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username": "admin", "password": "admin123"}'
`

### Access Protected Route

`ash
TOKEN="your-jwt-token-here"
curl http://localhost:8000/auth/me -H "Authorization: Bearer "
`

### Admin Route

`ash
TOKEN="admin-jwt-token"
curl http://localhost:8000/admin/users -H "Authorization: Bearer "
`

## Seed Data

`ash
spry seed --entry auth_api.seed:seed --context auth_api.data:AppDbContext --database auth.db
`

Seeds two users:
- dmin / dmin123 (role: admin)
- user1 / user123 (role: user)
