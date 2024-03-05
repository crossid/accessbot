import unittest

from app.id import generate
from app.models import Org, User
from app.models_facade import UserStore
from app.user_store_factory import create_user_store


class CustomUserStore(UserStore):
    def get_by_email(self, email: str):
        return User(id=generate(), email=email)

    def list_orgs_for_user(self, user_id: str) -> list[Org]:
        return []


class TestUserStore(unittest.TestCase):
    def test_create_user_store_by_class(self):
        store = create_user_store(fqdn_class=f"{__name__}.CustomUserStore")
        u = store.get_by_email("john@acme.io")
        self.assertEqual(u.email, "john@acme.io")
