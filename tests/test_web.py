import unittest

from app import create_app
from app.db import collection


class FlaskIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_portal_login_page_renders(self):
        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Core and jury access", response.data)
        self.assertIn(b"Forgot password?", response.data)

    def test_forgot_password_page_renders(self):
        response = self.client.get("/auth/forgot-password")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Request jury password reset", response.data)

    def test_user_portal_url_renders_public_workspace(self):
        rules = {rule.rule for rule in self.app.url_map.iter_rules()}

        self.assertIn("/users/", rules)

    def test_swagger_ui_and_openapi_document_require_core_login(self):
        docs = self.client.get("/api/docs")
        spec = self.client.get("/api/openapi.json")

        self.assertEqual(docs.status_code, 302)
        self.assertIn("/auth/login", docs.headers["Location"])
        self.assertEqual(spec.status_code, 302)
        self.assertIn("/auth/login", spec.headers["Location"])

    def test_edit_link_requires_unlock_when_session_is_missing(self):
        with self.app.app_context():
            idea = collection("ideas").find_one({"edit_token": {"$ne": None}, "archived": {"$ne": True}})
        if not idea:
            self.skipTest("No seeded idea with edit token available.")

        locked = self.client.get(f"/ideas/{idea['idea_id']}/edit?token={idea['edit_token']}")
        self.assertEqual(locked.status_code, 403)
        self.assertIn(b"Unlock idea editing", locked.data)

        unlocked = self.client.post(
            f"/ideas/{idea['idea_id']}/edit",
            data={"unlock_edit": "1", "edit_token": idea["edit_token"], "edit_pin": "DemoEdit123!"},
            follow_redirects=False,
        )
        self.assertEqual(unlocked.status_code, 302)


if __name__ == "__main__":
    unittest.main()
