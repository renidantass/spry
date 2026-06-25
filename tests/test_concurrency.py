from __future__ import annotations

import threading
import unittest


class LoginTrackerConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        from spry.auth import LoginTracker
        self.tracker = LoginTracker(max_attempts=100, lockout_minutes=60)

    def test_concurrent_record_failure(self):
        errors = []
        barrier = threading.Barrier(50)

        def record(uid: int) -> None:
            barrier.wait()
            try:
                for _ in range(10):
                    self.tracker.record_failure(f"user{uid}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        # Each of 50 users got exactly 10 failures
        for i in range(50):
            self.assertEqual(self.tracker.remaining_attempts(f"user{i}"), 90)

    def test_concurrent_is_locked(self):
        for i in range(3):
            self.tracker.record_failure("victim")

        errors = []
        barrier = threading.Barrier(20)

        def check() -> None:
            barrier.wait()
            try:
                locked = self.tracker.is_locked("victim")
                self.assertFalse(locked)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_concurrent_reset(self):
        for i in range(30):
            self.tracker.record_failure("reset_me")

        barrier = threading.Barrier(10)

        def do_reset() -> None:
            barrier.wait()
            self.tracker.reset("reset_me")

        threads = [threading.Thread(target=do_reset) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # After reset, remaining should be back to max
        self.assertEqual(self.tracker.remaining_attempts("reset_me"), 100)


class SessionStoreConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        from spry.session import SessionStore
        self.store = SessionStore(ttl=3600)

    def test_concurrent_set_and_get(self):
        errors = []
        barrier = threading.Barrier(50)

        def worker(sid: str) -> None:
            barrier.wait()
            try:
                self.store.set(sid, {"data": sid})
                result = self.store.get(sid)
                assert result is not None and result["data"] == sid
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"sid{i}",)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_concurrent_delete_and_exists(self):
        for i in range(20):
            self.store.set(f"del{i}", {"i": i})

        errors = []
        barrier = threading.Barrier(20)

        def deleter(i: int) -> None:
            barrier.wait()
            try:
                self.store.delete(f"del{i}")
                self.assertFalse(self.store.exists(f"del{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=deleter, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_concurrent_touch(self):
        self.store.set("touch_me", {"val": 1})
        barrier = threading.Barrier(30)

        def do_touch() -> None:
            barrier.wait()
            self.store.touch("touch_me")

        threads = [threading.Thread(target=do_touch) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        data = self.store.get("touch_me")
        self.assertIsNotNone(data)
        self.assertEqual(data["val"], 1)


class TokenBucketConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        from spry.throttling import TokenBucket
        self.bucket = TokenBucket(max_requests=50, window=60)

    def test_concurrent_is_allowed_respects_limit(self):
        barrier = threading.Barrier(100)
        allowed = []
        errors = []
        lock = threading.Lock()

        def try_allow() -> None:
            barrier.wait()
            try:
                if self.bucket.is_allowed("shared"):
                    with lock:
                        allowed.append(True)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=try_allow) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(allowed), 50)

    def test_concurrent_remaining_does_not_mutate(self):
        for _ in range(10):
            self.bucket.is_allowed("counter")

        barrier = threading.Barrier(30)
        errors = []

        def check() -> None:
            barrier.wait()
            try:
                rem = self.bucket.remaining("counter")
                self.assertGreaterEqual(rem, 0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
