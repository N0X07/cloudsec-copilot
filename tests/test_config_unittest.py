from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import database_url_from_env


class DatabaseConfigurationTests(unittest.TestCase):
    def test_sqlite_is_the_safe_local_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(database_url_from_env(), "sqlite:///./cloudsec.db")

    def test_explicit_database_url_has_priority(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite:///./explicit.db",
                "DB_HOST": "ignored.example",
            },
            clear=True,
        ):
            self.assertEqual(database_url_from_env(), "sqlite:///./explicit.db")

    def test_rds_components_are_encoded(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "database.example",
                "DB_PORT": "5432",
                "DB_NAME": "cloudsec",
                "DB_USER": "service-user",
                "DB_PASSWORD": "p@ss/word",
            },
            clear=True,
        ):
            self.assertEqual(
                database_url_from_env(),
                "postgresql+psycopg://service-user:p%40ss%2Fword@"
                "database.example:5432/cloudsec",
            )

    def test_rds_host_requires_a_password(self) -> None:
        with patch.dict(os.environ, {"DB_HOST": "database.example"}, clear=True):
            with self.assertRaises(ValueError):
                database_url_from_env()


if __name__ == "__main__":
    unittest.main()
