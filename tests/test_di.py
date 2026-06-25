from __future__ import annotations

import unittest

from spry.di import ServiceCollection


class DiTests(unittest.TestCase):
    def test_singleton(self):
        col = ServiceCollection()
        col.add_singleton(str, instance="singleton")
        provider = col.build_provider()
        self.assertEqual(provider.resolve(str), "singleton")
        self.assertIs(provider.resolve(str), provider.resolve(str))

    def test_scoped(self):
        col = ServiceCollection()
        col.add_scoped(dict, factory=lambda r: {"id": id(r)})
        provider = col.build_provider()
        scope1 = provider.create_scope()
        scope2 = provider.create_scope()
        d1 = scope1.resolve(dict)
        d2 = scope2.resolve(dict)
        self.assertIsNot(d1, d2)

    def test_transient(self):
        col = ServiceCollection()
        col.add_transient(list, factory=lambda r: [id(r)])
        provider = col.build_provider()
        scope = provider.create_scope()
        l1 = scope.resolve(list)
        l2 = scope.resolve(list)
        self.assertIsNot(l1, l2)

    def test_auto_wiring(self):
        col = ServiceCollection()
        col.add_singleton(dict, instance={"role": "admin"})
        class Service:
            def __init__(self, config: dict) -> None:
                self.config = config
        col.add_transient(Service)
        provider = col.build_provider()
        scope = provider.create_scope()
        s = scope.resolve(Service)
        self.assertIsInstance(s, Service)
        self.assertEqual(s.config, {"role": "admin"})

    def test_dispose_calls_close(self):
        class Disposable:
            def __init__(self):
                self.closed = False
            def close(self):
                self.closed = True

        col = ServiceCollection()
        col.add_scoped(Disposable)
        provider = col.build_provider()
        scope = provider.create_scope()
        d = scope.resolve(Disposable)
        scope.dispose()
        self.assertTrue(d.closed)

    def test_scoped_raises_at_provider_level(self):
        col = ServiceCollection()
        col.add_scoped(dict)
        provider = col.build_provider()
        with self.assertRaises(RuntimeError):
            provider.resolve(dict)
