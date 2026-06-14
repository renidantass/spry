from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from spry.routing import _compile_path, _normalize_path, _combine_paths
from spry.routing import extract_controller_routes, create_function_route, controller, get, post


class RoutingTests(unittest.TestCase):
    def test_normalize_path(self):
        self.assertEqual(_normalize_path("/"), "/")
        self.assertEqual(_normalize_path("//"), "/")
        self.assertEqual(_normalize_path("/api/v1"), "/api/v1")
        self.assertEqual(_normalize_path("api/v1/"), "/api/v1")

    def test_compile_path_simple(self):
        pattern, names = _compile_path("/users/{id}")
        self.assertEqual(names, ("id",))
        m = pattern.fullmatch("/users/42")
        self.assertIsNotNone(m)
        self.assertEqual(m.groupdict(), {"id": "42"})

    def test_compile_path_int(self):
        pattern, names = _compile_path("/users/{id:int}")
        self.assertEqual(names, ("id",))
        m = pattern.fullmatch("/users/42")
        self.assertIsNotNone(m)
        m2 = pattern.fullmatch("/users/abc")
        self.assertIsNone(m2)

    def test_compile_path_uuid(self):
        pattern, names = _compile_path("/items/{uid:uuid}")
        self.assertEqual(names, ("uid",))
        m = pattern.fullmatch("/items/550e8400-e29b-41d4-a716-446655440000")
        self.assertIsNotNone(m)
        m2 = pattern.fullmatch("/items/not-a-uuid")
        self.assertIsNone(m2)

    def test_compile_path_slug(self):
        pattern, names = _compile_path("/posts/{slug}")
        self.assertEqual(names, ("slug",))
        m = pattern.fullmatch("/posts/my-post-title")
        self.assertIsNotNone(m)
        self.assertEqual(m.groupdict(), {"slug": "my-post-title"})

    def test_combine_paths(self):
        self.assertEqual(_combine_paths("/api", "/v1"), "/api/v1")
        self.assertEqual(_combine_paths("/", "/users"), "/users")
        self.assertEqual(_combine_paths("/api", "/"), "/api")

    def test_controller_routes(self):
        @controller("/api")
        class TestCtrl:
            @get("/items")
            def list(self):
                pass
            @post("/items")
            def create(self):
                pass

        routes = extract_controller_routes(TestCtrl)
        self.assertEqual(len(routes), 2)
        methods = {r.method for r in routes}
        self.assertIn("GET", methods)
        self.assertIn("POST", methods)
        paths = {r.path for r in routes}
        self.assertIn("/api/items", paths)

    def test_function_route(self):
        def handler():
            pass
        route = create_function_route("GET", "/health", handler)
        self.assertEqual(route.method, "GET")
        self.assertEqual(route.path, "/health")
        self.assertIs(route.function_handler, handler)

    def test_route_match(self):
        @controller("/users")
        class UCtrl:
            @get("/{id:int}")
            def by_id(self):
                pass

        routes = extract_controller_routes(UCtrl)
        self.assertEqual(len(routes), 1)
        route = routes[0]
        result = route.match("GET", "/users/42")
        self.assertIsNotNone(result)
        self.assertEqual(result, {"id": "42"})
        self.assertIsNone(route.match("POST", "/users/42"))
        self.assertIsNone(route.match("GET", "/users/abc"))
