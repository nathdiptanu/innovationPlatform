import unittest

from app import create_app


class FlaskIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_portal_login_page_renders(self):
        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Core and jury access", response.data)

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


if __name__ == "__main__":
    unittest.main()
