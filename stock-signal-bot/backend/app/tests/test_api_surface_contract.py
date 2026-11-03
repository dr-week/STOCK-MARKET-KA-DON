import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestApiSurfaceContract(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_health_and_frontend_api_routes_are_published(self):
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        schema = self.client.get("/openapi.json")
        self.assertEqual(schema.status_code, 200)
        paths = schema.json()["paths"]
        self.assertIn("/api/scan", paths)
        self.assertIn("/api/stock/{symbol}", paths)

    def test_local_frontend_origin_is_allowed_by_api_cors(self):
        response = self.client.get(
            "/health",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5173",
        )


if __name__ == "__main__":
    unittest.main()
