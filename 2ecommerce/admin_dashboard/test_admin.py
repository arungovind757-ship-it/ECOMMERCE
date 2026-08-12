import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add admin dir to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from main import app

class TestAdminApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_admin_dashboard(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Manufacturing & Management Desk", response.text)

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

    def test_update_order_status(self):
        from database import SessionLocal
        from models import Order, OrderStatus
        db = SessionLocal()
        order = Order(
            customer_name="Test Customer",
            email="test@example.com",
            phone="9876543210",
            shipping_address="Test Address",
            total_amount=1200.0,
            status=OrderStatus.PENDING
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        order_id = order.id
        db.close()

        payload = {
            "status": "In Production"
        }
        response = self.client.post(f"/api/admin/order/{order_id}/status", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["new_status"], "In Production")

if __name__ == "__main__":
    unittest.main()
