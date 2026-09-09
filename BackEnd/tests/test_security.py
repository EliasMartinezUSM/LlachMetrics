import unittest

from app.security import hash_password, verify_password


class PasswordSecurityTests(unittest.TestCase):
    def test_each_password_hash_uses_a_different_salt(self) -> None:
        password = "PasswordSegura123!"

        first_hash = hash_password(password)
        second_hash = hash_password(password)

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password(password, first_hash))
        self.assertTrue(verify_password(password, second_hash))
        self.assertFalse(verify_password("password-incorrecta", first_hash))


if __name__ == "__main__":
    unittest.main()