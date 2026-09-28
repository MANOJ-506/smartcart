# 🚀 SmartCart Deployment Guide for Render.com

This step-by-step guide is designed for beginners to deploy the **SmartCart** Flask web application to [Render.com](https://render.com) using **Gunicorn**.

---

## 📋 Prerequisites

1. A **GitHub account** with the SmartCart repository.
2. A free account on **[Render.com](https://dashboard.render.com)**.
3. (Optional) **Gmail App Password** for sending OTP emails.
4. (Optional) **Razorpay Test Keys** for online payments.

---

## 🛠️ Step 1: Push Project to GitHub

Before creating the service on Render, ensure all deployment changes and `.gitignore` are pushed to your GitHub repository:

```bash
# Navigate to your smartcart project folder
cd smartcart

# Check git status
git status

# Stage all updated files
git add .

# Commit changes
git commit -m "Prepare SmartCart for Render deployment with Gunicorn and secure config"

# Push to your main branch
git push origin main
```

> **Note:** `.gitignore` will ensure your virtual environment (`venv/`), `.env`, and local SQLite database (`*.db`) are not uploaded to GitHub.

---

## 🌐 Step 2: Create a Web Service on Render

1. Log in to **[Render Dashboard](https://dashboard.render.com/)**.
2. Click the **"New +"** button at the top right and select **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and click **Next**.
4. Connect your GitHub account and select your repository: `smartcart` (or `MANOJ-506/smartcart`).
5. Configure the deployment settings exactly as follows:

| Setting | Value | Description |
| :--- | :--- | :--- |
| **Name** | `smartcart` | Service identifier on Render |
| **Region** | *Choose closest to you* (e.g., Singapore / Oregon / Frankfurt) | Server region |
| **Branch** | `main` | Production branch |
| **Root Directory** | *Leave blank* (if files are in root of repo) | Project root |
| **Runtime** | `Python 3` | Language runtime |
| **Build Command** | `pip install -r requirements.txt` | Installs dependencies including Gunicorn |
| **Start Command** | `gunicorn app:app` | Starts Flask with Gunicorn WSGI server |
| **Instance Type** | `Free` | Free tier |

---

## 🔑 Step 3: Add Environment Variables in Render

Scroll down to the **"Environment Variables"** section in the Render Web Service configuration page (or click **Environment** in the left sidebar after creating) and add the following keys:

| Key | Example Value / Description | Required? |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Generate a long random string, e.g. `k9#mP2$vL8@qW5!zX`)* | **Yes** |
| `FLASK_ENV` | `production` | Optional |
| `PYTHON_VERSION` | `3.12.0` | Recommended |
| `MAIL_SERVER` | `smtp.gmail.com` | Optional (default: `smtp.gmail.com`) |
| `MAIL_PORT` | `587` | Optional (default: `587`) |
| `MAIL_USE_TLS` | `True` | Optional (default: `True`) |
| `MAIL_USE_SSL` | `False` | Optional (default: `False`) |
| `MAIL_USERNAME` | `your-email@gmail.com` | If using Gmail OTP |
| `MAIL_PASSWORD` | `your-16-char-gmail-app-password` | If using Gmail OTP |
| `MAIL_DEFAULT_SENDER` | `your-email@gmail.com` | Optional |
| `RAZORPAY_KEY_ID` | `rzp_test_...` | If using Razorpay payment |
| `RAZORPAY_KEY_SECRET` | `your-razorpay-key-secret` | If using Razorpay payment |

> 🔒 **Security Tip:** Never commit real email passwords or Razorpay secrets into GitHub. Always store them exclusively in Render Environment Variables.

---

## 🚀 Step 4: Deploy the Web Service

1. Click **"Create Web Service"** (or **"Deploy latest commit"**).
2. Render will trigger the build automatically:
   - It clones the repository.
   - It runs `pip install -r requirements.txt`.
   - It executes `gunicorn app:app`.
3. Wait until the status changes from **Building** to **"Live"** (green checkmark).

---

## 📊 Step 5: Check Deployment Logs

If you encounter any issues or want to check startup progress:
1. Open your service in the Render Dashboard.
2. Click the **"Logs"** tab on the left.
3. You should see:
   ```text
   ==> Starting service with 'gunicorn app:app'
   [INFO] Starting gunicorn 23.0.0
   [INFO] Listening at: http://0.0.0.0:10000
   [INFO] Using worker: sync
   [INFO] Booting worker with pid: ...
   ```

---

## 🧪 Step 6: Verify and Test Your Live Application

Render gives you a free HTTPS URL (e.g. `https://smartcart-xxxx.onrender.com`).

Test the following routes:

1. **Health Check**:
   - `https://your-app-url.onrender.com/health`
   - Expected response: `{"status": "ok"}`
2. **Landing Page**:
   - `https://your-app-url.onrender.com/`
3. **User Authentication & Store Flow**:
   - Register: `/user-register`
   - Login: `/user-login`
   - Products: `/user/products`
   - Cart: `/user/cart`
   - Orders: `/user/my-orders`
4. **Admin Panel**:
   - Admin Login: `/admin-login`
   - Admin Signup: `/admin-signup`
   - Dashboard: `/admin-dashboard`
   - Add Product: `/admin/add-item`
   - Item Inventory: `/admin/item-list`
5. **Invoice PDF Generation**:
   - `/user/download-invoice/<order_id>`

---

## ⚠️ Important Architecture Notes & Known Limitations

### 1. SQLite Database Ephemeral Persistence
- Render's free Web Services run in ephemeral containers.
- The SQLite database file (`smartcart.db`) initializes automatically when the application boots and persists while the container is running.
- When Render spins down free containers after inactivity or during redeployments, SQLite data may reset.
- *Recommended Next Step:* For production-scale persistent data, migrate SQLite to a managed PostgreSQL database (Render provides free/starter PostgreSQL).

### 2. File Uploads (Product & Admin Images)
- Uploaded files are saved to `static/uploads/`.
- Like SQLite, files stored on the local container disk will not persist across redeploys.
- For permanent media storage in production, consider cloud storage such as Cloudinary or AWS S3.

---

## ❓ Troubleshooting Common Errors

### `ModuleNotFoundError: No module named '...'`
- **Cause:** Missing package in `requirements.txt`.
- **Fix:** Ensure all dependencies are listed in `requirements.txt` and commit/push to GitHub.

### `Application Failed to Start` / `Gunicorn error`
- **Cause:** Syntax error or missing environment variable in `app.py`.
- **Fix:** Review Render **Logs** tab to see the exact traceback. Ensure Start Command is set to `gunicorn app:app`.

### `Unable to send OTP / Email Error`
- **Cause:** Gmail requires a 16-character **App Password** (not your regular Gmail password). 2-Step Verification must be enabled in your Google account.
- **Fix:** Generate an App Password in [Google Account Security](https://myaccount.google.com/apppasswords) and update `MAIL_PASSWORD` in Render environment variables.
- *Note:* In development/demo mode without email keys, OTP codes are logged directly to the server console in Render logs.

### `Razorpay Signature / Key Error`
- **Cause:** Missing or incorrect `RAZORPAY_KEY_ID` or `RAZORPAY_KEY_SECRET`.
- **Fix:** Verify your Test API Keys from the Razorpay Dashboard and paste them into Render's Environment Variables tab.

### `Static files (CSS/JS/Images) not loading`
- **Cause:** Broken relative links.
- **Fix:** SmartCart templates use Flask's `url_for('static', filename='...')` which resolves static URLs automatically.
