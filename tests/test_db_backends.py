from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from spry.orm import DbContext, dbset, key, DatabaseMigrator
from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(slots=True)
class Item:
    id: int | None = key()
    name: str = ""
    price: float = 0.0
    status: Status = Status.ACTIVE


class TestDb(DbContext):
    items = dbset(Item)


@unittest.skipIf(True, "Requires testcontainers (Docker)")
class DatabaseBackendIntegrationTests(unittest.TestCase):
    def test_postgres(self):
        import psycopg2  # noqa: F401
        self._test_crud("postgresql://postgres:postgres@localhost:5432/test")

    def test_mysql(self):
        import pymysql  # noqa: F401
        self._test_crud("mysql://root:root@localhost:3306/test")

    def _test_crud(self, url):
        db = TestDb(url)
        db.ensure_created()
        try:
            item = Item(name="test", price=100.0)
            db.items.add(item)
            db.save()
            self.assertIsNotNone(item.id)
            found = db.items.find(item.id)
            self.assertEqual(found.name, "test")
            found.name = "updated"
            db.items.update(found)
            db.save()
            self.assertEqual(db.items.find(item.id).name, "updated")
            db.items.remove(item.id)
            db.save()
            self.assertIsNone(db.items.find(item.id))
        finally:
            db.close()


class DatabaseBackendSQLiteTests(unittest.TestCase):
    def test_sqlite_memory_crud(self):
        db = TestDb(":memory:")
        db.ensure_created()
        item = Item(name="mem", price=50.0)
        db.items.add(item)
        db.save()
        self.assertIsNotNone(item.id)
        found = db.items.find(item.id)
        self.assertEqual(found.name, "mem")
        db.close()

    def test_sqlite_file_crud(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = TestDb(db_path)
            db.ensure_created()
            item = Item(name="file", price=25.0)
            db.items.add(item)
            db.save()
            found = db.items.find(item.id)
            self.assertEqual(found.name, "file")
            found.name = "changed"
            db.items.update(found)
            db.save()
            self.assertEqual(db.items.find(item.id).name, "changed")
            total = db.items.sum("price")
            self.assertIsNotNone(total)
            count = db.items.count()
            self.assertEqual(count, 1)
            page = db.items.paginate(page=1, per_page=10)
            self.assertEqual(len(page.items), 1)
            self.assertEqual(page.total, 1)
            db.items.remove(item.id)
            db.save()
            self.assertIsNone(db.items.find(item.id))
            db.close()
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_enum_crud(self):
        db = TestDb(":memory:")
        db.ensure_created()
        item = Item(name="enum_test", status=Status.ACTIVE)
        db.items.add(item)
        db.save()
        found = db.items.find(item.id)
        self.assertEqual(found.status, Status.ACTIVE)
        db.close()

    def test_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            mig_path = DatabaseMigrator.create_migration(TestDb, "initial", tmp)
            self.assertTrue(mig_path.exists())
            content = mig_path.read_text()
            self.assertIn("CREATE TABLE", content)
