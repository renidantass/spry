import unittest
from dataclasses import dataclass, field, fields

from spry.validation import ValidationError, bind_payload, bind_value
from spry.validators import Email, MaxLength, MinLength, Range, Regex, Required, validate_model


class ValidationTests(unittest.TestCase):
    def test_bind_payload_success(self):
        @dataclass
        class User:
            name: str = ""
            age: int = 0

        u = bind_payload(User, {"name": "Alice", "age": 30})
        self.assertEqual(u.name, "Alice")
        self.assertEqual(u.age, 30)

    def test_bind_payload_missing_required(self):
        @dataclass
        class User:
            name: str = ""
            email: str = field(default_factory=str)

        u = bind_payload(User, {"name": "Bob"})
        self.assertEqual(u.name, "Bob")
        self.assertEqual(u.email, "")

    def test_bind_payload_type_coercion(self):
        @dataclass
        class Item:
            count: int = 0
            price: float = 0.0
            active: bool = False

        u = bind_payload(Item, {"count": "42", "price": "9.99", "active": "true"})
        self.assertEqual(u.count, 42)
        self.assertEqual(u.price, 9.99)
        self.assertTrue(u.active)

    def test_bind_payload_type_error(self):
        @dataclass
        class Item:
            count: int = 0

        with self.assertRaises((ValidationError, ValueError)):
            bind_payload(Item, {"count": "not_a_number"})

    def test_bind_value_int(self):
        self.assertEqual(bind_value(int, "42", path="x"), 42)
        with self.assertRaises(ValidationError):
            bind_value(int, "abc", path="x")

    def test_bind_value_float(self):
        self.assertEqual(bind_value(float, "3.14", path="x"), 3.14)

    def test_bind_value_bool(self):
        self.assertTrue(bind_value(bool, "true", path="x"))
        self.assertFalse(bind_value(bool, "false", path="x"))
        self.assertTrue(bind_value(bool, True, path="x"))

    def test_bind_value_list(self):
        result = bind_value(list[int], ["1", "2", "3"], path="x")
        self.assertEqual(result, [1, 2, 3])

    def test_bind_value_optional(self):
        result = bind_value(int | None, None, path="x")
        self.assertIsNone(result)
        result = bind_value(int | None, "42", path="x")
        self.assertEqual(result, 42)

    def test_nested_dataclass(self):
        @dataclass
        class Address:
            city: str = ""
            zip: str = ""

        @dataclass
        class User:
            name: str = ""
            address: Address | None = None

        u = bind_payload(User, {"name": "Alice", "address": {"city": "NYC", "zip": "10001"}})
        self.assertIsInstance(u.address, Address)
        self.assertEqual(u.address.city, "NYC")


class ValidateHelperTests(unittest.TestCase):
    def test_validate_basic(self):
        from dataclasses import dataclass

        from spry.validation import validate

        @dataclass
        class Model:
            name: str = validate(Required(), MinLength(3))

        m = Model(name="foo")
        self.assertEqual(m.name, "foo")
        meta = fields(Model)[0].metadata
        self.assertIn("validate", meta)
        self.assertEqual(len(meta["validate"]), 2)

    def test_validate_with_default(self):
        from dataclasses import dataclass, fields

        from spry.validation import validate

        @dataclass
        class Model:
            name: str = validate(MinLength(2), default="ab")

        m = Model()
        self.assertEqual(m.name, "ab")
        self.assertEqual(len(fields(Model)[0].metadata["validate"]), 1)

    def test_validate_with_default_factory(self):
        from dataclasses import dataclass, fields

        from spry.validation import validate

        @dataclass
        class Model:
            tags: list[str] = validate(default_factory=list)

        m = Model()
        self.assertEqual(m.tags, [])
        self.assertEqual(fields(Model)[0].metadata, {})

    def test_validate_no_validators(self):
        from dataclasses import dataclass, fields

        from spry.validation import validate

        @dataclass
        class Model:
            name: str = validate(default="x")

        m = Model()
        self.assertEqual(m.name, "x")
        self.assertEqual(fields(Model)[0].metadata, {})

    def test_snake_case_factories(self):
        from spry.validators import email, max_length, min_length, range_validator, regex, required

        self.assertIsInstance(required(), Required)
        self.assertIsInstance(min_length(3), MinLength)
        self.assertIsInstance(max_length(10), MaxLength)
        self.assertIsInstance(email(), Email)
        self.assertIsInstance(regex(r"^a"), Regex)
        self.assertIsInstance(range_validator(1, 10), Range)


class ValidatorsTests(unittest.TestCase):
    def test_required_validator(self):
        v = Required()
        self.assertIsNotNone(v.validate(None, "name"))
        self.assertIsNotNone(v.validate("", "name"))
        self.assertIsNone(v.validate("valid", "name"))

    def test_min_length_validator(self):
        v = MinLength(3)
        self.assertIsNotNone(v.validate("ab", "name"))
        self.assertIsNone(v.validate("abcd", "name"))

    def test_max_length_validator(self):
        v = MaxLength(5)
        self.assertIsNotNone(v.validate("toolong", "name"))
        self.assertIsNone(v.validate("short", "name"))

    def test_email_validator(self):
        v = Email()
        self.assertIsNone(v.validate("user@example.com", "email"))
        self.assertIsNotNone(v.validate("invalid", "email"))

    def test_regex_validator(self):
        v = Regex(r"^[A-Z][a-z]+$")
        self.assertIsNone(v.validate("Hello", "name"))
        self.assertIsNotNone(v.validate("hello", "name"))

    def test_range_validator(self):
        v = Range(min_val=18, max_val=120)
        self.assertIsNotNone(v.validate(15, "age"))
        self.assertIsNone(v.validate(25, "age"))
        self.assertIsNotNone(v.validate(150, "age"))

    def test_validate_model(self):
        @dataclass
        class User:
            name: str = field(default="x", metadata={"validate": [Required(), MinLength(3)]})
            email: str = field(default="x", metadata={"validate": [Email()]})

        u = User(name="A", email="bad")
        errors = validate_model(u)
        self.assertGreater(len(errors), 0)
        codes = [e["code"] for e in errors]
        self.assertIn("minlength", codes)
        self.assertIn("email", codes)
