from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from spry import DbContext, dbset, foreign_key, key, navigation, navigation_many


@dataclass(slots=True)
class Author:
    id: int | None = key()
    name: str = ""
    posts: list["Post"] = navigation_many(lambda: Post, foreign_key="author_id")


@dataclass(slots=True)
class Post:
    author_id: int = foreign_key(Author, default=0)
    id: int | None = key()
    title: str = ""
    author: Author | None = navigation(Author, foreign_key="author_id")


class BloggingContext(DbContext):
    authors = dbset(Author)
    posts = dbset(Post)
class OrmTests(unittest.TestCase):
    def test_can_include_navigation_relations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "blog.db"
            db = BloggingContext(str(db_path))
            try:
                db.ensure_created()
                author = db.authors.add(Author(name="Ada"))
                db.posts.add(Post(title="Hello", author_id=author.id or 0))
                db.save()

                post = db.posts.first(title="Hello")
                assert post is not None
                db.posts.include(post, "author")
                self.assertIsNotNone(post.author)
                self.assertEqual(post.author.name, "Ada")

                loaded_author = db.authors.first(name="Ada")
                assert loaded_author is not None
                db.authors.include(loaded_author, "posts")
                self.assertEqual(len(loaded_author.posts), 1)
                self.assertEqual(loaded_author.posts[0].title, "Hello")
            finally:
                db.close()

    def test_foreign_key_constraint_is_enforced(self) -> None:
        db = BloggingContext(":memory:")
        try:
            db.ensure_created()
            with self.assertRaises(sqlite3.IntegrityError):
                db.posts.add(Post(title="Orphan", author_id=999))
                db.save()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
