import sys
sys.path.append('c:/Users/Arch Office/Downloads/ecommerce')

import unittest
from fastapi.testclient import TestClient
from main import app, calculate_blind_config
from database import SessionLocal, get_db
from models import Product, Order, OrderItem, StoreSetting, Offer, OrderStatus

class TestEcommerceApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_storefront_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AeroShield", response.text)

    def test_quote_calculator_view(self):
        response = self.client.get("/quote?product_id=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Customize Quote & Sections", response.text)
        
        # Test invalid product_id
        response = self.client.get("/quote?product_id=999")
        self.assertEqual(response.status_code, 404)

    def test_price_calculation_api(self):
        # Valid calculation
        payload = {
            "product_id": 1,
            "width_ft": 5.0,
            "height_ft": 6.0,
            "quantity": 1
        }
        response = self.client.post("/api/calculate-price", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_price", data)
        self.assertIn("roll_used", data)
        self.assertIn("panels_count", data)

        # Invalid width
        payload["width_ft"] = 0.5
        response = self.client.post("/api/calculate-price", json=payload)
        self.assertEqual(response.status_code, 400)

        # Invalid quantity
        payload["width_ft"] = 5.0
        payload["quantity"] = 0
        response = self.client.post("/api/calculate-price", json=payload)
        self.assertEqual(response.status_code, 422) # Pydantic validation error

    def test_checkout_api(self):
        payload = {
            "customer_name": "Test Customer",
            "email": "test@example.com",
            "phone": "9876543210",
            "shipping_address": "123 Test Street, Test City",
            "coupon_code": "SUPER15",
            "items": [
                {
                    "product_id": 1,
                    "section_name": "Balcony Front",
                    "width_ft": 5.0,
                    "height_ft": 6.0,
                    "color": "Transparent Clear",
                    "quantity": 1
                }
            ]
        }
        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("order_id", data)
        self.assertIn("total_price", data)

        # Test invalid coupon
        payload["coupon_code"] = "INVALIDCOUPON"
        response = self.client.post("/api/checkout", json=payload)
        self.assertEqual(response.status_code, 200) # Should succeed but not apply discount

    def test_admin_validations(self):
        # Test product update with invalid price
        payload = {
            "name": "Classic Clear PVC Blind",
            "article_code": "PVC-CLR-120",
            "base_price": -10.0,
            "colors": "Transparent Clear",
            "description": "Some description"
        }
        response = self.client.post("/api/admin/product/1/update", data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Base price must be a positive number", response.json()["detail"])

        # Test product create with invalid price
        create_payload = payload.copy()
        create_payload["article_code"] = "PVC-NEW-999"
        response = self.client.post("/api/admin/product/create", data=create_payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Base price must be a positive number", response.json()["detail"])

        # Test offer update with invalid discount percent
        offer_payload = {
            "title": "Super Offer 15% Off",
            "discount_percent": 150.0,
            "code": "SUPER15",
            "description": "Get 15% off today",
            "is_active": 1
        }
        response = self.client.post("/api/admin/offers/update", data=offer_payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Discount percentage must be between 0% and 100%", response.json()["detail"])
        
    def test_admin_dashboard(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Manufacturing & Management Desk", response.text)

if __name__ == "__main__":
    import sys
    with open("c:/Users/Arch Office/Downloads/ecommerce/scratch/test_output.log", "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f
        unittest.main()
