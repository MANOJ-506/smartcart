import sys
import unittest
import io
import re
from app import app, get_db_connection

class SmartCartComprehensiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def test_01_public_routes(self):
        routes = [
            ('/', 200, 'SmartCart'),
            ('/user-login', 200, 'Welcome Back'),
            ('/user-register', 200, 'Create Account'),
            ('/user-forgot-password', 200, 'Forgot Password'),
            ('/admin-login', 200, 'Admin Login'),
            ('/admin-signup', 200, 'Admin Registration'),
            ('/admin-forgot-password', 200, 'Admin Forgot Password'),
        ]
        for url, expected_code, content_check in routes:
            res = self.client.get(url)
            self.assertEqual(res.status_code, expected_code, f"Failed for {url}: status {res.status_code}")
            self.assertIn(content_check.encode('utf-8'), res.data, f"Content '{content_check}' not in {url}")
            print(f"[PASS] Route: {url} -> Status {res.status_code}")

    def test_02_user_forgot_password_flow(self):
        # 1. Access forgot password page
        res = self.client.get('/user-forgot-password')
        self.assertEqual(res.status_code, 200)

        # 2. Check with test user in db
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, name FROM users LIMIT 1")
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # Post email for forgot password
            with self.client.session_transaction() as sess:
                sess['user_forgot_email'] = user['email']
                sess['user_forgot_otp'] = '123456'

            # Test verify OTP page GET
            res_otp_page = self.client.get('/user-forgot-verify-otp')
            self.assertEqual(res_otp_page.status_code, 200)
            self.assertIn(b'Verify OTP', res_otp_page.data)

            # Test verify OTP POST (correct OTP)
            res_otp_post = self.client.post('/user-forgot-verify-otp', data={'otp': '123456'}, follow_redirects=True)
            self.assertEqual(res_otp_post.status_code, 200)
            self.assertIn(b'Create New Password', res_otp_post.data)

            # Test reset password POST
            res_reset = self.client.post('/user-forgot-reset-password', data={
                'password': 'NewPassword123!',
                'confirm_password': 'NewPassword123!'
            }, follow_redirects=True)
            self.assertEqual(res_reset.status_code, 200)
            self.assertIn(b'Password updated successfully', res_reset.data)
            print("[PASS] User Forgot Password Flow verified successfully")

    def test_03_admin_forgot_password_flow(self):
        # 1. Access admin forgot password page
        res = self.client.get('/admin-forgot-password')
        self.assertEqual(res.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, name FROM admin LIMIT 1")
        adm = cursor.fetchone()
        cursor.close()
        conn.close()

        if adm:
            with self.client.session_transaction() as sess:
                sess['admin_forgot_email'] = adm['email']
                sess['admin_forgot_otp'] = '654321'

            res_otp_page = self.client.get('/admin-forgot-verify-otp')
            self.assertEqual(res_otp_page.status_code, 200)
            self.assertIn(b'Verify Admin OTP', res_otp_page.data)

            res_otp_post = self.client.post('/admin-forgot-verify-otp', data={'otp': '654321'}, follow_redirects=True)
            self.assertEqual(res_otp_post.status_code, 200)
            self.assertIn(b'Set New Admin Password', res_otp_post.data)

            res_reset = self.client.post('/admin-forgot-reset-password', data={
                'password': 'AdminPassword123!',
                'confirm_password': 'AdminPassword123!'
            }, follow_redirects=True)
            self.assertEqual(res_reset.status_code, 200)
            self.assertIn(b'Password reset successfully', res_reset.data)
            print("[PASS] Admin Forgot Password Flow verified successfully")

    def test_04_user_authenticated_pages(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, email FROM users LIMIT 1")
        user = cursor.fetchone()
        cursor.execute("SELECT product_id FROM products LIMIT 1")
        prod = cursor.fetchone()
        cursor.execute("SELECT order_id FROM orders LIMIT 1")
        order = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            with self.client.session_transaction() as sess:
                sess['user_id'] = user['user_id']
                sess['user_name'] = user['name']
                sess['user_email'] = user['email']

            # Test user home
            r_home = self.client.get('/user-dashboard')
            self.assertEqual(r_home.status_code, 200)

            # Test user products
            r_prod = self.client.get('/user/products')
            self.assertEqual(r_prod.status_code, 200)

            # Test product details
            if prod:
                r_det = self.client.get(f'/user/product/{prod["product_id"]}')
                self.assertEqual(r_det.status_code, 200)

            # Test cart
            r_cart = self.client.get('/user/cart')
            self.assertEqual(r_cart.status_code, 200)

            # Test my orders
            r_orders = self.client.get('/user/my-orders')
            self.assertEqual(r_orders.status_code, 200)

            # Test invoice download if order exists
            if order:
                r_inv = self.client.get(f'/user/download-invoice/{order["order_id"]}')
                self.assertEqual(r_inv.status_code, 200)
                self.assertEqual(r_inv.content_type, 'application/pdf')
                self.assertTrue(len(r_inv.data) > 500)
                print(f"[PASS] Invoice PDF generation successful for Order #{order['order_id']} ({len(r_inv.data)} bytes)")

            print("[PASS] All User Authenticated Store pages verified successfully")

    def test_05_admin_authenticated_pages(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, name, email FROM admin LIMIT 1")
        adm = cursor.fetchone()
        cursor.execute("SELECT product_id FROM products LIMIT 1")
        prod = cursor.fetchone()
        cursor.close()
        conn.close()

        if adm:
            with self.client.session_transaction() as sess:
                sess['admin_id'] = adm['admin_id']
                sess['admin_name'] = adm['name']
                sess['admin_email'] = adm['email']

            # Admin dashboard
            r_dash = self.client.get('/admin-dashboard')
            self.assertEqual(r_dash.status_code, 200)

            # Add item page
            r_add = self.client.get('/admin/add-item')
            self.assertEqual(r_add.status_code, 200)

            # Item list page
            r_list = self.client.get('/admin/item-list')
            self.assertEqual(r_list.status_code, 200)

            # View item page
            if prod:
                r_view = self.client.get(f'/admin/view-item/{prod["product_id"]}')
                self.assertEqual(r_view.status_code, 200)

                # Update item page
                r_up = self.client.get(f'/admin/update-item/{prod["product_id"]}')
                self.assertEqual(r_up.status_code, 200)

            # Admin profile
            r_prof = self.client.get('/admin/profile')
            self.assertEqual(r_prof.status_code, 200)

            print("[PASS] All Admin Authenticated Management pages verified successfully")

if __name__ == '__main__':
    unittest.main()
