SECRET_KEY = "abc@123"   # used for sessions

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "smartcart.db")

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'deadzonelocator@gmail.com'
MAIL_PASSWORD = 'iqog zgwj skhc mrek' 
ADMIN_UPLOAD_FOLDER = 'static/uploads/admin_profiles'
RAZORPAY_KEY_ID = "rzp_test_TcCRgwOZoFQtQR"
RAZORPAY_KEY_SECRET = "zS9uQETivXJp1xbBP86HkBMo"



