from __future__ import annotations

import unittest
from dataclasses import dataclass

from spry.openapi import OpenApiBuilder
from spry.routing import extract_controller_routes, controller, get, post


@controller("/users")
class UsersController:
    @get("/")
    def list(self):
        """List all users."""
        pass

    @get("/{id:int}")
    def get_by_id(self):
        """Get user by ID."""
        pass

    @post("/")
    def create(self, payload: "CreateUser"):
        """Create a new user."""
        pass


@dataclass
class CreateUser:
    name: str = ""
    email: str = ""


class OpenApiTests(unittest.TestCase):
    def setUp(self):
        routes = extract_controller_routes(UsersController)
        self.builder = OpenApiBuilder(title="Test API", version="1.0.0")
        self.builder.add_routes(routes)

    def test_build_spec(self):
        spec = self.builder.build()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertEqual(spec["info"]["title"], "Test API")

    def test_has_paths(self):
        spec = self.builder.build()
        self.assertIn("/users", spec["paths"])

    def test_has_operations(self):
        spec = self.builder.build()
        path = spec["paths"]["/users"]
        self.assertIn("get", path)
        self.assertIn("post", path)

    def test_operation_ids(self):
        spec = self.builder.build()
        path = spec["paths"]["/users"]
        self.assertEqual(path["get"]["operationId"], "list")
        self.assertEqual(path["post"]["operationId"], "create")

    def test_descriptions_from_docstrings(self):
        spec = self.builder.build()
        path = spec["paths"]["/users"]
        self.assertIn("List all users", path["get"]["description"])

    def test_path_parameters(self):
        spec = self.builder.build()
        users_path = spec["paths"].get("/users", {})
        get_by_id_path = spec["paths"].get("/users/{id}", {})
        if get_by_id_path and "get" in get_by_id_path:
            params = get_by_id_path["get"].get("parameters", [])
            param_names = [p["name"] for p in params]
            self.assertIn("id", param_names)

    def test_schemas_generated(self):
        spec = self.builder.build()
        schemas = spec.get("components", {}).get("schemas", {})
        self.assertIn("CreateUser", schemas)

    def test_schema_properties(self):
        spec = self.builder.build()
        schema = spec["components"]["schemas"]["CreateUser"]
        self.assertIn("properties", schema)
        self.assertIn("name", schema["properties"])
        self.assertIn("email", schema["properties"])
