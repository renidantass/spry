from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from typing import Any, get_args, get_origin, get_type_hints

from spry.http import Response
from spry.routing import RouteDefinition

logger = logging.getLogger("spry.openapi")


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Spry API - Swagger UI</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({{
  url: '/openapi.json',
  dom_id: '#swagger-ui',
  presets: [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset
  ],
  layout: 'StandaloneLayout'
}})
</script>
</body>
</html>"""


class OpenApiBuilder:
    def __init__(self, title: str = "Spry API", version: str = "0.1.0", description: str = ""):
        self.title = title
        self.version = version
        self.description = description
        self._routes: list[RouteDefinition] = []
        self._schemas: dict[str, dict[str, Any]] = {}
        self._seen_schemas: set[type] = set()

    def add_routes(self, routes: list[RouteDefinition]) -> None:
        self._routes = routes

    def build(self) -> dict[str, Any]:
        paths: dict[str, Any] = {}
        for route in self._routes:
            self._add_path(route, paths)

        return {
            "openapi": "3.1.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": paths,
            "components": {
                "schemas": self._schemas,
            },
        }

    def _add_path(self, route: RouteDefinition, paths: dict[str, Any]) -> None:
        path_key = route.path
        if path_key not in paths:
            paths[path_key] = {}

        handler = self._resolve_handler(route)
        if handler is None:
            logger.warning("OpenAPI: no handler resolved for route %s %s", route.method, route.path)
            return

        doc = self._extract_doc(handler)
        operation_id = self._resolve_operation_id(route, handler)
        parameters = self._extract_parameters(route, handler)
        request_body = self._extract_request_body(handler)
        responses = self._extract_responses(handler)

        method = route.method.lower()
        paths[path_key][method] = {
            "operationId": operation_id,
            "summary": doc["summary"],
            "description": doc["description"],
            "parameters": parameters,
            **({"requestBody": request_body} if request_body else {}),
            "responses": responses,
        }

    def _resolve_handler(self, route: RouteDefinition) -> Any:
        if route.function_handler is not None:
            return route.function_handler
        if route.controller_type is not None and route.handler_name is not None:
            attr = getattr(route.controller_type, route.handler_name, None)
            if attr is not None:
                return getattr(route.controller_type, route.handler_name)
        return None

    def _extract_doc(self, handler: Any) -> dict[str, str]:
        doc = (handler.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else handler.__name__
        return {"summary": summary, "description": doc}

    def _resolve_operation_id(self, route: RouteDefinition, handler: Any) -> str:
        if route.handler_name:
            return route.handler_name
        return getattr(handler, "__name__", "handler")

    def _extract_parameters(self, route: RouteDefinition, handler: Any) -> list[dict[str, Any]]:
        parameters: list[dict[str, Any]] = []
        sig = inspect.signature(handler)
        try:
            hints = get_type_hints(handler)
        except Exception:
            hints = {}
            logger.debug("Failed to resolve type hints in _extract_parameters", exc_info=True)

        for name, param in sig.parameters.items():
            if name == "self" or name == "request":
                continue
            annotation = hints.get(name, param.annotation)

            if name in route.parameter_names:
                parameters.append(self._make_param(name, "path", annotation, True))
            elif self._is_dataclass_type(annotation):
                pass
            elif annotation is not inspect._empty:
                parameters.append(self._make_param(name, "query", annotation, False))

        return parameters

    def _make_param(self, name: str, location: str, annotation: Any, required: bool) -> dict[str, Any]:
        schema = self._type_to_schema(annotation)
        return {
            "name": name,
            "in": location,
            "required": required,
            "schema": schema,
        }

    def _extract_request_body(self, handler: Any) -> dict[str, Any] | None:
        sig = inspect.signature(handler)
        try:
            hints = get_type_hints(handler)
        except Exception:
            hints = {}
            logger.debug("Failed to resolve type hints in _extract_request_body", exc_info=True)

        for name, param in sig.parameters.items():
            if name == "self" or name == "request":
                continue
            annotation = hints.get(name, param.annotation)
            if self._is_dataclass_type(annotation):
                body_schema = self._get_or_create_schema(annotation)
                return {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{annotation.__name__}"}
                        }
                    },
                }
        return None

    def _extract_responses(self, handler: Any) -> dict[str, Any]:
        return {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                    }
                },
            },
            "400": {"description": "Bad request"},
            "422": {"description": "Validation error"},
        }

    def _is_dataclass_type(self, annotation: Any) -> bool:
        if isinstance(annotation, type) and is_dataclass(annotation):
            return True
        origin = get_origin(annotation)
        return origin is not None and isinstance(origin, type) and is_dataclass(origin)

    def _get_or_create_schema(self, model_type: type[Any]) -> dict[str, Any]:
        if model_type in self._seen_schemas:
            return self._schemas.get(model_type.__name__, {})
        self._seen_schemas.add(model_type)
        schema = self._build_dataclass_schema(model_type)
        self._schemas[model_type.__name__] = schema
        return schema

    def _build_dataclass_schema(self, model_type: type[Any]) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []

        type_hints = {}
        try:
            type_hints = get_type_hints(model_type)
        except Exception:
            type_hints = {}
            logger.debug("Failed to resolve type hints for dataclass %s", model_type, exc_info=True)

        for f in fields(model_type):
            annotation = type_hints.get(f.name, f.type)
            is_required = True
            if f.default is not field(default=None).default or f.default_factory is not field(default_factory=None).default_factory:
                is_required = False

            unwrapped, nullable = self._unwrap_optional(annotation)
            prop = self._type_to_schema(unwrapped)
            if nullable:
                prop["nullable"] = True

            properties[f.name] = prop
            if is_required:
                required.append(f.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    def _type_to_schema(self, annotation: Any) -> dict[str, Any]:
        if annotation is inspect._empty or annotation is type(None):
            return {}

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is list:
            item_type = args[0] if args else Any
            return {
                "type": "array",
                "items": self._type_to_schema(item_type),
            }

        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "additionalProperties": self._type_to_schema(value_type),
            }

        if origin is tuple:
            return {"type": "array"}

        if isinstance(annotation, type) and is_dataclass(annotation):
            self._get_or_create_schema(annotation)
            return {"$ref": f"#/components/schemas/{annotation.__name__}"}

        mapping = {
            str: {"type": "string"},
            int: {"type": "integer", "format": "int32"},
            float: {"type": "number", "format": "double"},
            bool: {"type": "boolean"},
            datetime: {"type": "string", "format": "date-time"},
            date: {"type": "string", "format": "date"},
            bytes: {"type": "string", "format": "binary"},
            Any: {},
        }

        for py_type, schema in mapping.items():
            if annotation is py_type:
                return schema

        return {"type": "string"}

    def _unwrap_optional(self, annotation: Any) -> tuple[Any, bool]:
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is not None and type(None) in args:
            inner = [a for a in args if a is not type(None)]
            return (inner[0] if inner else Any, True)
        return (annotation, False)


def make_openapi_response(app: Any) -> Response:
    openapi = getattr(app, "_openapi_spec", None)
    if openapi is None:
        return Response.json({"error": "OpenAPI spec not available"}, 404)
    return Response.json(openapi)


def make_swagger_ui_response() -> Response:
    return Response.html(SWAGGER_UI_HTML)
