from __future__ import annotations

import time
import unittest

from spry.auth import PasswordHasher, JwtAuthService, LoginTracker, UserPrincipal
from spry.http import Request, Response


class PasswordHasherTests(unittest.TestCase):
    def test_hash_and_verify(self):
        ph = PasswordHasher()
        hashed = ph.hash_password("mysecret")
        self.assertTrue(ph.verify("mysecret", hashed))
        self.assertFalse(ph.verify("wrong", hashed))

    def test_hash_format(self):
        ph = PasswordHasher()
        hashed = ph.hash_password("test")
        parts = hashed.split("$")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "pbkdf2_sha256")

    def test_verify_invalid_format(self):
        ph = PasswordHasher()
        self.assertFalse(ph.verify("x", "invalid"))
        self.assertFalse(ph.verify("x", "bad$format"))


class JwtAuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.jwt = JwtAuthService("test-secret", ttl=60)

    def test_issue_and_authenticate(self):
        token = self.jwt.issue("1", "Alice", {"role": "admin"})
        req = Request("GET", "/", {}, {"Authorization": f"Bearer {token}"}, b"", "http", "localhost")
        user = self.jwt.authenticate(req)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "1")
        self.assertEqual(user.name, "Alice")

    def test_no_auth_header(self):
        req = Request("GET", "/", {}, {}, b"", "http", "localhost")
        self.assertIsNone(self.jwt.authenticate(req))

    def test_wrong_token(self):
        req = Request("GET", "/", {}, {"Authorization": "Bearer invalid"}, b"", "http", "localhost")
        self.assertIsNone(self.jwt.authenticate(req))

    def test_expired_token(self):
        jwt = JwtAuthService("test", ttl=0)
        token = jwt.issue("1", "Bob")
        time.sleep(0.01)
        req = Request("GET", "/", {}, {"Authorization": f"Bearer {token}"}, b"", "http", "localhost")
        self.assertIsNone(jwt.authenticate(req))

    def test_tampered_token(self):
        token = self.jwt.issue("1", "Eve")
        tampered = token[:-5] + "XXXXX"
        req = Request("GET", "/", {}, {"Authorization": f"Bearer {tampered}"}, b"", "http", "localhost")
        self.assertIsNone(self.jwt.authenticate(req))


class LoginTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = LoginTracker(max_attempts=3, lockout_minutes=1)

    def test_track_attempts(self):
        self.tracker.record_failure("user1")
        self.tracker.record_failure("user1")
        self.assertEqual(self.tracker.remaining_attempts("user1"), 1)

    def test_lockout(self):
        for _ in range(3):
            self.tracker.record_failure("user1")
        self.assertTrue(self.tracker.is_locked("user1"))

    def test_remaining_returns_0_when_locked(self):
        for _ in range(3):
            self.tracker.record_failure("user1")
        self.assertEqual(self.tracker.remaining_attempts("user1"), 0)

    def test_reset(self):
        self.tracker.record_failure("user1")
        self.tracker.reset("user1")
        self.assertFalse(self.tracker.is_locked("user1"))

    def test_lockout_time_remaining(self):
        for _ in range(3):
            self.tracker.record_failure("user2")
        remaining = self.tracker.lockout_remaining_seconds("user2")
        self.assertGreater(remaining, 0)

    def test_not_locked_below_threshold(self):
        self.tracker.record_failure("user3")
        self.assertFalse(self.tracker.is_locked("user3"))


class UserPrincipalTests(unittest.TestCase):
    def test_roles_from_list(self):
        u = UserPrincipal("1", "Admin", {"roles": ["admin", "editor"]})
        self.assertIn("admin", u.roles)
        self.assertTrue(u.is_in_role("admin"))
        self.assertFalse(u.is_in_role("viewer"))

    def test_roles_from_string(self):
        u = UserPrincipal("2", "User", {"roles": "user,viewer"})
        self.assertIn("user", u.roles)
        self.assertIn("viewer", u.roles)
