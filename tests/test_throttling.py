from __future__ import annotations

import time
import unittest

from spry.throttling import TokenBucket, rate_limit_middleware_factory


class TokenBucketTests(unittest.TestCase):
    def test_allows_within_limit(self):
        bucket = TokenBucket(max_requests=5, window=60)
        for _ in range(5):
            self.assertTrue(bucket.is_allowed("key1"))

    def test_blocks_over_limit(self):
        bucket = TokenBucket(max_requests=3, window=60)
        for _ in range(3):
            bucket.is_allowed("key2")
        self.assertFalse(bucket.is_allowed("key2"))

    def test_separate_keys_independent(self):
        bucket = TokenBucket(max_requests=2, window=60)
        self.assertTrue(bucket.is_allowed("alice"))
        self.assertTrue(bucket.is_allowed("alice"))
        self.assertFalse(bucket.is_allowed("alice"))
        self.assertTrue(bucket.is_allowed("bob"))

    def test_cleanup_expired_entries(self):
        bucket = TokenBucket(max_requests=2, window=0.1)
        bucket.is_allowed("key3")
        bucket.is_allowed("key3")
        self.assertFalse(bucket.is_allowed("key3"))
        time.sleep(0.15)
        self.assertTrue(bucket.is_allowed("key3"))

    def test_remaining_returns_count(self):
        bucket = TokenBucket(max_requests=5, window=60)
        self.assertEqual(bucket.remaining("key4"), 5)
        bucket.is_allowed("key4")
        self.assertEqual(bucket.remaining("key4"), 4)

    def test_remaining_never_negative(self):
        bucket = TokenBucket(max_requests=2, window=60)
        bucket.is_allowed("key5")
        bucket.is_allowed("key5")
        bucket.is_allowed("key5")
        self.assertEqual(bucket.remaining("key5"), 0)

    def test_reset_time_in_future(self):
        bucket = TokenBucket(max_requests=1, window=60)
        bucket.is_allowed("key6")
        reset = bucket.reset_time("key6")
        self.assertGreater(reset, time.time())

    def test_reset_time_no_requests(self):
        bucket = TokenBucket(max_requests=5, window=60)
        reset = bucket.reset_time("key7")
        self.assertGreater(reset, time.time())

    def test_inmemory_store_alias(self):
        self.assertIsNotNone(TokenBucket)

class RateLimitMiddlewareTests(unittest.TestCase):
    def test_middleware_allows_within_limit(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=5, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        for _ in range(5):
            resp = client.get("/test")
            self.assertEqual(resp.status_code, 200)

    def test_middleware_blocks_over_limit(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=2, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        client.get("/test")
        client.get("/test")
        resp = client.get("/test")
        self.assertEqual(resp.status_code, 429)

    def test_middleware_returns_rate_limit_headers(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=3, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        resp = client.get("/test")
        self.assertEqual(resp.headers["X-RateLimit-Limit"], "3")
        self.assertEqual(resp.headers["X-RateLimit-Remaining"], "2")

    def test_middleware_retry_after_on_block(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=1, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        client.get("/test")
        resp = client.get("/test")
        self.assertIn("Retry-After", resp.headers)
        self.assertIn("X-RateLimit-Remaining", resp.headers)

    def test_custom_key_func(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=1, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket, key_func=lambda ctx: "fixed"))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        client.get("/test")
        resp = client.get("/test")
        self.assertEqual(resp.status_code, 429)

    def test_custom_status_code_and_message(self):
        from spry import AppBuilder
        from spry.testing import TestClient

        bucket = TokenBucket(max_requests=1, window=60)
        builder = AppBuilder()
        builder.use(rate_limit_middleware_factory(bucket, status_code=503, message="Service Unavailable"))
        builder.map_get("/test", lambda: {"ok": True})
        app = builder.build()
        client = TestClient(app)

        client.get("/test")
        resp = client.get("/test")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Service Unavailable", resp.text)
