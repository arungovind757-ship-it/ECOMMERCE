import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add storefront dir to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from main import app

class TestStorefrontApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_storefront_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AeroShield", response.text)
        self.assertIn("Classic Clear PVC Blind", response.text)

    def test_quote_calculator_view(self):
        # Test valid product ID
        response = self.client.get("/quote?product_id=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Customize Quote & Sections", response.text)

        # Test invalid product ID
        response = self.client.get("/quote?product_id=999")
        self.assertEqual(response.status_code, 404)

    def test_price_calculation_api(self):
        # Valid test
        payload = {
            "product_id": 1,
            "width_ft": 8.0,
            "height_ft": 6.0,
            "quantity": 2
        }
        response = self.client.post("/api/calculate-price", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["roll_used"], 4.0)
        self.assertEqual(data["panels_count"], 2)
        # base_price = 120.0 (from DB pvc clear base price)
        # total_roll_width = 4.0 * 2 = 8.0
        # billable_sqft = 8.0 * 6.0 = 48.0
        # total_price = 48.0 * 120.0 * 2 = 11520.0
        self.assertEqual(data["total_price"], 11520.0)

        # Validation error test
        payload["width_ft"] = 0.5
        response = self.client.post("/api/calculate-price", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Width must be at least 1.0 ft", response.json()["detail"])

    def test_checkout_api(self):
        payload = {
            "customer_name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "shipping_address": "456 Blinds Lane, Bengaluru",
            "items": [
                {
                    "product_id": 1,
                    "section_name": "Balcony Left",
                    "width_ft": 4.5,
                    "height_ft": 7.0,
                    "color": "Transparent Clear",
                    "quantity": 1
                }
            ],
            "coupon_code": "MONSOON10"
        }
        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("order_id", data)

if __name__ == "__main__":
    unittest.main()
