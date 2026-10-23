import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production")

from fastapi import HTTPException, Response

from app.deps import get_current_user
from app.main import login, logout
from app.models import PasswordHash, User
from app.security import create_access_token, hash_password


class CookieSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User(id=7, email="usuario@ejemplo.com", full_name="Usuario")
        self.user.password = PasswordHash(id=7, hash=hash_password("ClaveSegura123!"))

    def test_login_sets_http_only_cookie_and_hides_token(self) -> None:
        db = Mock()
        db.scalar.return_value = self.user
        response = Response()
        form = Mock(username="Usuario@Ejemplo.com", password="ClaveSegura123!")

        result = login(form, response, db)

        cookie = response.headers["set-cookie"]
        self.assertIs(result, self.user)
        self.assertIn("access_token=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=lax", cookie)

    def test_login_rejects_wrong_password_without_cookie(self) -> None:
        db = Mock()
        db.scalar.return_value = self.user
        response = Response()
        form = Mock(username="usuario@ejemplo.com", password="incorrecta")

        with self.assertRaises(HTTPException) as context:
            login(form, response, db)

        self.assertEqual(context.exception.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)

    def test_current_user_is_read_from_cookie_token(self) -> None:
        db = Mock()
        db.get.return_value = self.user

        self.assertIs(get_current_user(create_access_token("7"), db), self.user)

        with self.assertRaises(HTTPException):
            get_current_user(None, db)
        with self.assertRaises(HTTPException):
            get_current_user("token-invalido", db)

    def test_logout_expires_cookie(self) -> None:
        response = Response()

        logout(response)

        cookie = response.headers["set-cookie"]
        self.assertIn('access_token=""', cookie)
        self.assertIn("Max-Age=0", cookie)
        self.assertIn("HttpOnly", cookie)


if __name__ == "__main__":
    unittest.main()

