from app.include.Spartacus import Database as SpartacusDatabase
from app.utils.auth_methods import uses_iam_auth
from django.test import SimpleTestCase


class UsesIamAuthTests(SimpleTestCase):
    def test_empty_credentials(self):
        self.assertFalse(uses_iam_auth(None))
        self.assertFalse(uses_iam_auth({}))

    def test_without_a_region(self):
        self.assertFalse(uses_iam_auth({"access_key_id": "key-id"}))

    def test_with_a_region(self):
        self.assertTrue(uses_iam_auth({"aws_region": "us-east-1"}))


class PostgreSQLGetPasswordTests(SimpleTestCase):
    def test_returns_the_stored_password(self):
        connection = SpartacusDatabase.PostgreSQL(
            "db.example.com", 5432, "postgres", "postgres", "stored-password"
        )

        self.assertEqual(connection.GetPassword(), "stored-password")
        self.assertIn("password='stored-password'", connection.GetConnectionString())
