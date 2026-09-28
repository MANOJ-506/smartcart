import os

# Base Directory (Absolute path to project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file (Fail-safe: works with or without python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key, val = key.strip(), val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass

# Flask Secret Key for session signing
SECRET_KEY = os.environ.get("SECRET_KEY", "smartcart-default-session-secret-change-in-production")

# Database Path (SQLite)
# NOTE: SQLite database files on Render's free/starter instances are ephemeral across restarts/redeploys.
# Suitable for testing/demos; for long-term persistent production data, migrate to PostgreSQL.
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "smartcart.db"))

# Flask-Mail / SMTP Configuration
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").strip().lower() in ["true", "1", "yes", "on"]
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False").strip().lower() in ["true", "1", "yes", "on"]
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", os.environ.get("MAIL_USERNAME") or "smartcart.app@gmail.com")

# Upload Folders (Absolute paths)
# NOTE: Uploaded files stored on Render's ephemeral disk reset upon service restarts/redeploys.
ADMIN_UPLOAD_FOLDER = os.environ.get(
    "ADMIN_UPLOAD_FOLDER",
    os.path.join(BASE_DIR, "static", "uploads", "admin_profiles")
)
PRODUCT_UPLOAD_FOLDER = os.environ.get(
    "PRODUCT_UPLOAD_FOLDER",
    os.path.join(BASE_DIR, "static", "uploads", "product_images")
)

# Razorpay Payment Gateway Keys
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
