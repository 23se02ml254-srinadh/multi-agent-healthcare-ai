import sys
import os
import time
import json
import uuid
import unittest
import requests
from io import BytesIO

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)

from app import app
from database.db import db
from database.models import User, ChatMessage, MedicalReport, DiseasePrediction, Recommendation

class TestFullSystemIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.test_email = f"test_integration_{uuid.uuid4().hex[:6]}@example.com"
        cls.test_password = "SecureTestPassword123!"
        cls.test_username = f"testuser_{uuid.uuid4().hex[:6]}"
        cls.auth_token = None
        cls.test_session_id = str(uuid.uuid4())
        cls.results = []

    def record_result(self, test_name, status, duration, details=None):
        self.results.append({
            'test': test_name,
            'status': status,
            'duration_seconds': round(duration, 4),
            'details': details or {}
        })

    def test_01_database_connectivity_and_schema(self):
        """Test PostgreSQL connectivity and all expected table schemas"""
        t0 = time.time()
        with app.app_context():
            try:
                user_count = User.query.count()
                chat_count = ChatMessage.query.count()
                report_count = MedicalReport.query.count()
                duration = time.time() - t0
                self.record_result("PostgreSQL Connectivity & Tables", "PASS", duration, {
                    "users": user_count,
                    "chat_messages": chat_count,
                    "medical_reports": report_count
                })
                self.assertIsNotNone(user_count)
            except Exception as e:
                self.record_result("PostgreSQL Connectivity & Tables", "FAIL", time.time() - t0, {"error": str(e)})
                raise e

    def test_02_health_endpoint(self):
        """Test /health endpoint"""
        t0 = time.time()
        res = self.client.get('/health')
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and data.get('status') == 'healthy'
        self.record_result("Health API Endpoint (/health)", "PASS" if passed else "FAIL", duration, data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data.get('status'), 'healthy')

    def test_03_user_registration(self):
        """Test user registration endpoint /api/auth/register"""
        t0 = time.time()
        payload = {
            'email': self.test_email,
            'password': self.test_password,
            'username': self.test_username,
            'first_name': 'Test',
            'last_name': 'User'
        }
        res = self.client.post('/api/auth/register', json=payload)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code in [201, 409]
        self.record_result("User Registration API (/api/auth/register)", "PASS" if passed else "FAIL", duration, {
            'status_code': res.status_code,
            'email': self.test_email
        })
        self.assertEqual(res.status_code, 201)

    def test_04_user_login(self):
        """Test user login endpoint /api/auth/login and JWT token issuance"""
        t0 = time.time()
        payload = {
            'email': self.test_email,
            'password': self.test_password
        }
        res = self.client.post('/api/auth/login', json=payload)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and 'access_token' in data
        if passed:
            TestFullSystemIntegration.auth_token = data['access_token']
        self.record_result("User Login & JWT Issuance (/api/auth/login)", "PASS" if passed else "FAIL", duration, {
            'status_code': res.status_code,
            'token_issued': bool(data.get('access_token'))
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('access_token', data)

    def test_05_authenticated_me_endpoint(self):
        """Test protected /api/auth/me endpoint using JWT"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        res = self.client.get('/api/auth/me', headers=headers)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and data.get('email') == self.test_email
        self.record_result("JWT Auth Protected Endpoint (/api/auth/me)", "PASS" if passed else "FAIL", duration, {
            'email': data.get('email') if data else None
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(data.get('email'), self.test_email)

    def test_06_google_oauth_client_id_endpoint(self):
        """Test Google OAuth client ID endpoint /api/auth/google/client-id"""
        t0 = time.time()
        res = self.client.get('/api/auth/google/client-id')
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and 'client_id' in data
        self.record_result("Google OAuth Client ID API (/api/auth/google/client-id)", "PASS" if passed else "FAIL", duration, {
            'client_id_configured': bool(data.get('client_id'))
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('client_id', data)

    def test_07_google_oauth_redirect_login_endpoint(self):
        """Test Google OAuth redirect initiation /api/auth/google/login"""
        t0 = time.time()
        res = self.client.get('/api/auth/google/login')
        duration = time.time() - t0
        passed = res.status_code in [302, 200]
        self.record_result("Google OAuth Redirect Initiation (/api/auth/google/login)", "PASS" if passed else "FAIL", duration, {
            'status_code': res.status_code,
            'redirect_location': res.headers.get('Location', '')[:60] + '...' if res.headers.get('Location') else None
        })
        self.assertEqual(res.status_code, 302)
        self.assertIn('accounts.google.com', res.headers.get('Location', ''))

    def test_08_chat_multi_agent_processing(self):
        """Test Multi-Agent Chat interaction (/api/chat)"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        payload = {
            'message': 'I have a high fever, chills, and productive cough for the last 3 days.',
            'session_id': self.test_session_id
        }
        res = self.client.post('/api/chat', headers=headers, json=payload)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and 'response' in data and len(data.get('agent_results', {})) > 0
        self.record_result("Multi-Agent Chat Pipeline (/api/chat)", "PASS" if passed else "FAIL", duration, {
            'response_length': len(data.get('response', '')),
            'agents_invoked': list(data.get('agent_results', {}).keys())
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('response', data)
        self.assertGreater(len(data.get('agent_results', {})), 0)

    def test_09_chat_history_retrieval(self):
        """Test Chat History retrieval (/api/chat/history)"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        res = self.client.get(f"/api/chat/history?session_id={self.test_session_id}", headers=headers)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and isinstance(data, list) and len(data) >= 2
        self.record_result("Chat History Retrieval (/api/chat/history)", "PASS" if passed else "FAIL", duration, {
            'messages_count': len(data) if isinstance(data, list) else 0
        })
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(data), 2)

    def test_10_chat_sessions_listing(self):
        """Test Chat Sessions listing (/api/chat/sessions)"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        res = self.client.get('/api/chat/sessions', headers=headers)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and isinstance(data, list) and len(data) > 0
        self.record_result("Chat Sessions Listing (/api/chat/sessions)", "PASS" if passed else "FAIL", duration, {
            'sessions_count': len(data) if isinstance(data, list) else 0
        })
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(data), 0)

    def test_11_report_upload_and_summarization(self):
        """Test Medical Report Upload and AI Summarization (/api/reports/upload)"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        report_content = (
            "DIAGNOSTIC LABORATORY REPORT\n"
            "Patient Name: John Doe\n"
            "Test: Comprehensive Metabolic Panel & Lipid Profile\n"
            "Total Cholesterol: 260 mg/dL (Reference: <200 mg/dL) - HIGH\n"
            "Triglycerides: 210 mg/dL (Reference: <150 mg/dL) - HIGH\n"
            "HDL Cholesterol: 38 mg/dL (Reference: >40 mg/dL) - LOW\n"
            "LDL Cholesterol: 180 mg/dL (Reference: <100 mg/dL) - HIGH\n"
            "Fasting Glucose: 138 mg/dL (Reference: 70-99 mg/dL) - HIGH\n"
            "HbA1c: 6.8% (Reference: <5.7%) - HIGH\n"
            "Impression: Dyslipidemia and Type 2 Diabetes pattern."
        )
        file_data = {
            'file': (BytesIO(report_content.encode('utf-8')), 'test_lab_report.txt'),
            'session_id': self.test_session_id,
            'message': 'Please summarize this lab report and highlight high risks.'
        }
        res = self.client.post('/api/reports/upload', headers=headers, data=file_data, content_type='multipart/form-data')
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and 'report' in data and 'chat_response' in data
        self.record_result("Medical Report Upload & Summarization (/api/reports/upload)", "PASS" if passed else "FAIL", duration, {
            'status_code': res.status_code,
            'report_id': data.get('report', {}).get('id') if data else None,
            'abnormal_count': len(data.get('report', {}).get('abnormal_values', [])) if data else 0
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('report', data)
        self.assertIn('chat_response', data)

    def test_12_chat_session_deletion(self):
        """Test Chat Session Deletion (/api/chat/session/<id>)"""
        t0 = time.time()
        headers = {'Authorization': f"Bearer {TestFullSystemIntegration.auth_token}"}
        res = self.client.delete(f"/api/chat/session/{self.test_session_id}", headers=headers)
        duration = time.time() - t0
        data = res.get_json()
        passed = res.status_code == 200 and data.get('deleted_count', 0) > 0
        self.record_result("Chat Session Deletion (/api/chat/session/<id>)", "PASS" if passed else "FAIL", duration, data)
        self.assertEqual(res.status_code, 200)

    @classmethod
    def tearDownClass(cls):
        # Save integration results
        results_file = os.path.join(os.path.dirname(__file__), 'integration_test_results.json')
        with open(results_file, 'w') as f:
            json.dump(cls.results, f, indent=2)
        print("\n==================================================")
        print("          INTEGRATION TEST SUMMARY")
        print("==================================================")
        for r in cls.results:
            print(f"[{r['status']}] {r['test']} ({r['duration_seconds']}s)")
        print(f"Full results saved to: {results_file}")

if __name__ == '__main__':
    unittest.main()
