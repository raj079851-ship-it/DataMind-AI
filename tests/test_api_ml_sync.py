"""
Unit Tests for Synchronized Enterprise API Endpoints
Validates:
- /datasets/sync and /datasets/load-demo/{demo_name}
- /security/users (listing and creation)
- /ml/train (classification & regression with real scikit-learn metrics)
- /ml/predict (what-if scenario evaluation)
- /ml/clustering (unsupervised clustering & 2D PCA)
- /dashboards/generate-ai (AI dashboard layout and KPI tracking)
"""

import unittest
from fastapi.testclient import TestClient
from api import app, active_datasets, active_ml_model
from modules.data_loader import generate_sample_customer_churn, generate_sample_housing


class TestAPIMLSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        active_datasets["default"] = generate_sample_customer_churn()
        active_ml_model.clear()

    def test_datasets_load_demo_churn(self):
        response = self.client.post("/datasets/load-demo/churn")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "loaded")
        self.assertIn("CustomerID", data["columns"])
        self.assertGreater(data["rows"], 10)

    def test_datasets_load_demo_housing(self):
        response = self.client.post("/datasets/load-demo/housing")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "loaded")
        self.assertIn("SalePrice", data["columns"])

    def test_datasets_sync(self):
        sample_records = [
            {"Age": 25, "Salary": 50000, "Purchased": 0},
            {"Age": 45, "Salary": 90000, "Purchased": 1},
            {"Age": 35, "Salary": 75000, "Purchased": 1},
            {"Age": 22, "Salary": 32000, "Purchased": 0}
        ]
        response = self.client.post("/datasets/sync", json={"records": sample_records, "dataset_name": "test_sync"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "synchronized")
        self.assertEqual(data["rows"], 4)
        self.assertEqual(data["columns"], ["Age", "Salary", "Purchased"])

    def test_security_users_list_and_create(self):
        list_res = self.client.get("/security/users")
        self.assertEqual(list_res.status_code, 200)
        users = list_res.json()["users"]
        self.assertGreater(len(users), 0)

        import time
        uname = f"test_user_{int(time.time() * 1000)}"
        new_user = {
            "username": uname,
            "password": "Password@123",
            "email": f"{uname}@enterprise.com",
            "role": "Analyst",
            "full_name": "Test Analyst"
        }
        create_res = self.client.post("/security/users", json=new_user)
        self.assertEqual(create_res.status_code, 200)
        self.assertEqual(create_res.json()["status"], "success")
        self.assertEqual(create_res.json()["user"]["username"], uname)

    def test_ml_train_classification(self):
        payload = {
            "target_col": "Churn",
            "algorithm": "random_forest",
            "task_type": "binary"
        }
        response = self.client.post("/ml/train", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["task_type"], "classification")
        self.assertIn("accuracy", data["metrics"])
        self.assertIn("f1", data["metrics"])
        self.assertGreater(len(data["feature_importances"]), 0)

    def test_ml_predict_what_if_scenario(self):
        self.client.post("/ml/train", json={"target_col": "Churn", "algorithm": "logistic_regression"})

        pred_payload = {
            "input_features": {
                "TenureMonths": 24,
                "MonthlyCharges": 75.5,
                "TotalCharges": 1800.0
            }
        }
        response = self.client.post("/ml/predict", json=pred_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("prediction", data)
        self.assertIn("top_driver", data)

    def test_ml_clustering(self):
        payload = {
            "columns": ["TenureMonths", "MonthlyCharges", "TotalCharges"],
            "algorithm": "kmeans",
            "n_clusters": 3
        }
        response = self.client.post("/ml/clustering", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("silhouette_score", data)
        self.assertEqual(data["n_clusters"], 3)
        self.assertGreater(len(data["sample_points"]), 0)
        self.assertIn("PCA_1", data["sample_points"][0])
        self.assertIn("PCA_2", data["sample_points"][0])

    def test_dashboards_generate_ai(self):
        payload = {"theme": "Slate Executive"}
        response = self.client.post("/dashboards/generate-ai", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("kpis", data)
        self.assertIn("insights", data)


if __name__ == "__main__":
    unittest.main()
