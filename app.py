
# =========================================================
# IMPORTS
# =========================================================

from flask import Flask, render_template, request, redirect, session, flash,make_response
from flask_mail import Mail, Message
import sqlite3
import bcrypt
import random
import config
import razorpay
import traceback
from utils.pdf_generator import generate_pdf



# =========================================================
# FLASK APPLICATION SETUP
# =========================================================

app = Flask(__name__)

# Secret key is used for Flask sessions
app.secret_key = config.SECRET_KEY


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD

# Initialize Flask-Mail
mail = Mail(app)
app.config['ADMIN_UPLOAD_FOLDER'] = config.ADMIN_UPLOAD_FOLDER



# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    """
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Initializes the SQLite database with the required schema if tables do not exist.
    Safe to run multiple times without data loss or dropping tables.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        profile_image TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_verified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        price REAL NOT NULL,
        image TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        customer_name TEXT,
        customer_phone TEXT,
        shipping_address TEXT,
        shipping_city TEXT,
        shipping_state TEXT,
        shipping_pincode TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()


# Ensure database tables exist on startup
init_db()
razorpay_client = razorpay.Client(
    auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET)
)


# =========================================================
# HOME / LANDING PAGE
# =========================================================

@app.route('/')
def index():
    return render_template('index.html')


# =========================================================
# ADMIN SIGNUP
# =========================================================

@app.route('/admin-signup', methods=['GET', 'POST'])
def admin_signup():

    # -----------------------------------------------------
    # Display signup form
    # -----------------------------------------------------

    if request.method == 'GET':
        return render_template('admin/admin_signup.html')


    # -----------------------------------------------------
    # Get signup details from form
    # -----------------------------------------------------

    name = request.form['name']
    email = request.form['email']


    # -----------------------------------------------------
    # Check whether email already exists
    # -----------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT admin_id FROM admin WHERE email = ?",
        (email,)
    )

    existing_admin = cursor.fetchone()

    cursor.close()
    conn.close()


    # -----------------------------------------------------
    # Stop registration if email already exists
    # -----------------------------------------------------

    if existing_admin:
        flash(
            "This email is already registered. Please login instead.",
            "danger"
        )

        return redirect('/admin-signup')


    # -----------------------------------------------------
    # Store signup details temporarily in session
    # -----------------------------------------------------

    session['signup_name'] = name
    session['signup_email'] = email


    # -----------------------------------------------------
    # Generate and store OTP
    # -----------------------------------------------------

    otp = random.randint(100000, 999999)

    session['otp'] = otp


    # -----------------------------------------------------
    # Send OTP to user's email
    # -----------------------------------------------------

    message = Message(
        subject="SmartCart Admin OTP",
        sender=config.MAIL_USERNAME,
        recipients=[email]
    )

    message.body = (
        f"Your OTP for SmartCart Admin Registration is: {otp}"
    )

    mail.send(message)


    # -----------------------------------------------------
    # Redirect user to OTP verification page
    # -----------------------------------------------------

    flash("OTP sent to your email!", "success")

    return redirect('/verify-otp')


# =========================================================
# OTP VERIFICATION PAGE
# =========================================================

@app.route('/verify-otp', methods=['GET'])
def verify_otp_get():

    return render_template('admin/verify_otp.html')


# =========================================================
# VERIFY OTP AND CREATE ADMIN
# =========================================================

@app.route('/verify-otp', methods=['POST'])
def verify_otp_post():

    # -----------------------------------------------------
    # Get OTP and password from form
    # -----------------------------------------------------

    user_otp = request.form['otp']
    password = request.form['password']


    # -----------------------------------------------------
    # Verify OTP
    # -----------------------------------------------------

    if str(session.get('otp')) != str(user_otp):

        flash("Invalid OTP. Try again!", "danger")

        return redirect('/verify-otp')


    # -----------------------------------------------------
    # Hash password using bcrypt
    # -----------------------------------------------------

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


    # -----------------------------------------------------
    # Insert admin details into database
    # -----------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO admin (name, email, password)
        VALUES (?, ?, ?)
        """,
        (
            session['signup_name'],
            session['signup_email'],
            hashed_password
        )
    )

    conn.commit()

    cursor.close()
    conn.close()


    # -----------------------------------------------------
    # Clear temporary signup information from session
    # -----------------------------------------------------

    session.pop('otp', None)
    session.pop('signup_name', None)
    session.pop('signup_email', None)


    # -----------------------------------------------------
    # Registration successful
    # -----------------------------------------------------

    flash("Admin Registered Successfully!", "success")

    return redirect('/admin-signup')


# =================================================================
# ROUTE 4: ADMIN LOGIN PAGE (GET + POST)
# =================================================================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    # Show login page
    if request.method == 'GET':
        return render_template("admin/admin_login.html")

    # POST → Validate login
    email = request.form['email']
    password = request.form['password']

    # Step 1: Check if admin email exists
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE email=?", (email,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin is None:
        flash("Email not found! Please register first.", "danger")
        return redirect('/admin-login')

    # Step 2: Compare entered password with hashed password
    stored_hashed_password = admin['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        flash("Incorrect password! Try again.", "danger")
        return redirect('/admin-login')

    # Step 5: If login success → Create admin session
    session['admin_id'] = admin['admin_id']
    session['admin_name'] = admin['name']
    session['admin_email'] = admin['email']

    flash("Login Successful!", "success")
    return redirect('/admin-dashboard')


# =================================================================
# ADMIN FORGOT PASSWORD - REQUEST OTP
# =================================================================
@app.route('/admin-forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'GET':
        return render_template('admin/forgot_password.html')

    email = request.form.get('email', '').strip().lower()
    if not email:
        flash("Email address is required!", "danger")
        return redirect('/admin-forgot-password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id FROM admin WHERE email=?", (email,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if not admin:
        flash("No admin account found with that email address.", "danger")
        return redirect('/admin-forgot-password')

    otp = str(random.randint(100000, 999999))
    session['admin_forgot_email'] = email
    session['admin_forgot_otp'] = otp

    try:
        msg = Message(
            subject="SmartCart Admin - Password Reset OTP",
            sender=config.MAIL_USERNAME,
            recipients=[email]
        )
        msg.body = f"Your SmartCart Admin password reset OTP is: {otp}\n\nDo not share this OTP with anyone."
        mail.send(msg)
    except Exception as e:
        print("MAIL ERROR:", e)

    flash("Password reset OTP sent to your email!", "success")
    return redirect('/admin-forgot-verify-otp')


# =================================================================
# ADMIN FORGOT PASSWORD - VERIFY OTP
# =================================================================
@app.route('/admin-forgot-verify-otp', methods=['GET', 'POST'])
def admin_forgot_verify_otp():
    if 'admin_forgot_email' not in session:
        flash("Session expired. Please request a new OTP.", "danger")
        return redirect('/admin-forgot-password')

    if request.method == 'GET':
        return render_template('admin/forgot_verify_otp.html', email=session['admin_forgot_email'])

    entered_otp = request.form.get('otp', '').strip()
    stored_otp = session.get('admin_forgot_otp', '')

    if entered_otp != stored_otp:
        flash("Invalid OTP! Please enter the correct code.", "danger")
        return redirect('/admin-forgot-verify-otp')

    session['admin_forgot_verified'] = True
    flash("OTP verified! Please create your new password.", "success")
    return redirect('/admin-forgot-reset-password')


# =================================================================
# ADMIN FORGOT PASSWORD - RESET PASSWORD
# =================================================================
@app.route('/admin-forgot-reset-password', methods=['GET', 'POST'])
def admin_forgot_reset_password():
    if 'admin_forgot_email' not in session or not session.get('admin_forgot_verified'):
        flash("Please verify your OTP first.", "danger")
        return redirect('/admin-forgot-password')

    if request.method == 'GET':
        return render_template('admin/reset_password.html', email=session['admin_forgot_email'])

    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not password or not confirm_password:
        flash("Both password fields are required.", "danger")
        return redirect('/admin-forgot-reset-password')

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect('/admin-forgot-reset-password')

    if password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect('/admin-forgot-reset-password')

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE admin SET password=? WHERE email=?", (hashed_password, session['admin_forgot_email']))
    conn.commit()
    cursor.close()
    conn.close()

    session.pop('admin_forgot_email', None)
    session.pop('admin_forgot_otp', None)
    session.pop('admin_forgot_verified', None)

    flash("Password reset successfully! Please login with your new password.", "success")
    return redirect('/admin-login')




# =================================================================
# ROUTE 5: ADMIN DASHBOARD (PROTECTED ROUTE)
# =================================================================
@app.route('/admin-dashboard')
def admin_dashboard():

    # Protect dashboard → Only logged-in admin can access
    if 'admin_id' not in session:
        flash("Please login to access dashboard!", "danger")
        return redirect('/admin-login')

    # Send admin name to dashboard UI
    return render_template("admin/dashboard.html", admin_name=session['admin_name'])



# =================================================================
# ROUTE 6: ADMIN LOGOUT
# =================================================================
@app.route('/admin-logout')
def admin_logout():

    # Clear admin session
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)

    flash("Logged out successfully.", "success")
    return redirect('/admin-login')

import os
from werkzeug.utils import secure_filename

# ------------------- IMAGE UPLOAD PATH -------------------
UPLOAD_FOLDER = 'static/uploads/product_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# =================================================================
# ROUTE 7: SHOW ADD PRODUCT PAGE (Protected Route)
# =================================================================
@app.route('/admin/add-item', methods=['GET'])
def add_item_page():

    # Only logged-in admin can access
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    return render_template("admin/add_item.html")



# =================================================================
# ROUTE 8: ADD PRODUCT INTO DATABASE
# =================================================================
@app.route('/admin/add-item', methods=['POST'])
def add_item():

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']
    image_file = request.files['image']

    # 2️⃣ Validate image upload
    if image_file.filename == "":
        flash("Please upload a product image!", "danger")
        return redirect('/admin/add-item')

    # 3️⃣ Secure the file name
    filename = secure_filename(image_file.filename)

    # 4️⃣ Create full path
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # 5️⃣ Save image into folder
    image_file.save(image_path)

    # 6️⃣ Insert product into database
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO products (name, description, category, price, image) VALUES (?, ?, ?, ?, ?)",
        (name, description, category, price, filename)
    )

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect('/admin/add-item')


# =================================================================
# ROUTE 9: DISPLAY ALL PRODUCTS (Admin)
# =================================================================
@app.route('/admin/item-list')
def item_list():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch category list for dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # 2️⃣ Build dynamic query based on filters
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/item_list.html",
        products=products,
        categories=categories
    )




#=================================================================
# ROUTE 10: VIEW SINGLE PRODUCT DETAILS
# =================================================================
@app.route('/admin/view-item/<int:item_id>')
def view_item(item_id):

    # Check admin session
    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    return render_template("admin/view_item.html", product=product)
@app.route('/admin/update-item/<int:item_id>', methods=['GET'])
def update_item_page(item_id):

    # Check login
    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # Fetch product data
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    return render_template("admin/update_item.html", product=product)
# =================================================================
# ROUTE-12: UPDATE PRODUCT + OPTIONAL IMAGE REPLACE
# =================================================================
@app.route('/admin/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    # 1️⃣ Get updated form data
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    price = request.form['price']

    new_image = request.files['image']

    # 2️⃣ Fetch old product data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    old_image_name = product['image']

    # 3️⃣ If admin uploaded a new image → replace it
    if new_image and new_image.filename != "":
        
        # Secure filename
        from werkzeug.utils import secure_filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        new_image_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        new_image.save(new_image_path)

        # Delete old image file
        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image_name)
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        final_image_name = new_filename

    else:
        # No new image uploaded → keep old one
        final_image_name = old_image_name

    # 4️⃣ Update product in the database
    cursor.execute("""
        UPDATE products
        SET name=?, description=?, category=?, price=?, image=?
        WHERE product_id=?
    """, (name, description, category, price, final_image_name, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Product updated successfully!", "success")
    return redirect('/admin/item-list')

@app.route('/admin/delete-item/<int:item_id>')
def delete_item(item_id):

    if 'admin_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/admin-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1️⃣ Fetch product to get image name
    cursor.execute("SELECT image FROM products WHERE product_id=?", (item_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/admin/item-list')

    image_name = product['image']

    # Delete image from folder
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    if os.path.exists(image_path):
        os.remove(image_path)

    # 2️⃣ Delete product from DB
    cursor.execute("DELETE FROM products WHERE product_id=?", (item_id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Product deleted successfully!", "success")
    return redirect('/admin/item-list')
# =================================================================
# ROUTE 1: SHOW ADMIN PROFILE DATA
# =================================================================
@app.route('/admin/profile', methods=['GET'])
def admin_profile():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE admin_id = ?", (admin_id,))
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/admin_profile.html", admin=admin)
# =================================================================
# ROUTE 2: UPDATE ADMIN PROFILE (NAME, EMAIL, PASSWORD, IMAGE)
# =================================================================
@app.route('/admin/profile', methods=['POST'])
def admin_profile_update():

    if 'admin_id' not in session:
        flash("Please login!", "danger")
        return redirect('/admin-login')

    admin_id = session['admin_id']

    # 1️⃣ Get form data
    name = request.form['name']
    email = request.form['email']
    new_password = request.form['password']
    new_image = request.files['profile_image']

    conn = get_db_connection()
    cursor = conn.cursor()

    # 2️⃣ Fetch old admin data
    cursor.execute("SELECT * FROM admin WHERE admin_id = ?", (admin_id,))
    admin = cursor.fetchone()

    old_image_name = admin['profile_image']

    # 3️⃣ Update password only if entered
    if new_password:
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        hashed_password = admin['password']  # keep old password

    # 4️⃣ Process new profile image if uploaded
    if new_image and new_image.filename != "":
        
        from werkzeug.utils import secure_filename
        new_filename = secure_filename(new_image.filename)

        # Save new image
        image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], new_filename)
        new_image.save(image_path)

        # Delete old image
        if old_image_name:
            old_image_path = os.path.join(app.config['ADMIN_UPLOAD_FOLDER'], old_image_name)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        final_image_name = new_filename
    else:
        final_image_name = old_image_name

    # 5️⃣ Update database
    cursor.execute("""
        UPDATE admin
        SET name=?, email=?, password=?, profile_image=?
        WHERE admin_id=?
    """, (name, email, hashed_password, final_image_name, admin_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Update session name for UI consistency
    session['admin_name'] = name  
    session['admin_email'] = email

    flash("Profile updated successfully!", "success")
    return redirect('/admin/profile')

'''--------------------------user module--------------------------------------------------------------------------------'''

# =================================================================
# USER MODULE
# =================================================================


# =================================================================
# USER REGISTRATION - SEND OTP
# =================================================================

@app.route('/user-register', methods=['GET', 'POST'])
def user_register():

    # -------------------------------------------------------------
    # GET REQUEST
    # -------------------------------------------------------------

    if request.method == 'GET':

        return render_template(
            'user/user_register.html'
        )


    # -------------------------------------------------------------
    # GET FORM DATA
    # -------------------------------------------------------------

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()


    # -------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------

    if not name or not email:

        flash(
            'Name and email are required!',
            'danger'
        )

        return redirect('/user-register')


    # -------------------------------------------------------------
    # GENERATE OTP
    # -------------------------------------------------------------

    otp = str(random.randint(100000, 999999))


    # -------------------------------------------------------------
    # SAVE DATA TEMPORARILY IN SESSION
    # -------------------------------------------------------------

    session['user_register_name'] = name
    session['user_register_email'] = email
    session['user_register_otp'] = otp


    # -------------------------------------------------------------
    # PRINT OTP IN TERMINAL FOR TESTING
    # -------------------------------------------------------------

    print("======================================")
    print("USER REGISTRATION OTP")
    print("Name :", name)
    print("Email:", email)
    print("OTP  :", otp)
    print("======================================")


    # -------------------------------------------------------------
    # SEND OTP TO EMAIL
    # -------------------------------------------------------------

    try:

        msg = Message(
            subject='E-Commerce - Email Verification OTP',
            sender=config.MAIL_USERNAME,
            recipients=[email]
        )

        msg.body = f"""
Hello {name},

Thank you for registering with our E-Commerce Application.

Your verification OTP is:

{otp}

Please enter this OTP to continue your registration.

Do not share this OTP with anyone.

Regards,
E-Commerce Team
"""

        mail.send(msg)


    except Exception as e:

        print("MAIL ERROR:", e)

        # Remove temporary session data

        session.pop('user_register_name', None)
        session.pop('user_register_email', None)
        session.pop('user_register_otp', None)

        flash(
            'Unable to send OTP. Please check your email configuration.',
            'danger'
        )

        return redirect('/user-register')


    # -------------------------------------------------------------
    # OTP SENT SUCCESSFULLY
    # -------------------------------------------------------------

    flash(
        'OTP sent successfully! Check your email.',
        'success'
    )

    return redirect('/user-verify-otp')

# =================================================================
# TEMPORARY OTP PAGE
# =================================================================

# =================================================================
# USER OTP VERIFICATION
# =================================================================

@app.route('/user-verify-otp', methods=['GET', 'POST'])
def user_verify_otp():

    # -------------------------------------------------------------
    # CHECK REGISTRATION SESSION
    # -------------------------------------------------------------

    if 'user_register_email' not in session:

        flash(
            'Registration session expired. Please register again.',
            'danger'
        )

        return redirect('/user-register')


    # -------------------------------------------------------------
    # GET REQUEST
    # -------------------------------------------------------------

    if request.method == 'GET':

        return render_template(
            'user/verify_otp.html',
            email=session['user_register_email']
        )


    # -------------------------------------------------------------
    # GET ENTERED OTP
    # -------------------------------------------------------------

    entered_otp = request.form.get(
        'otp',
        ''
    ).strip()

    stored_otp = session.get(
        'user_register_otp',
        ''
    )


    # -------------------------------------------------------------
    # DEBUG
    # -------------------------------------------------------------

    print("======================================")
    print("ENTERED OTP :", entered_otp)
    print("STORED OTP  :", stored_otp)
    print("======================================")


    # -------------------------------------------------------------
    # VERIFY OTP
    # -------------------------------------------------------------

    if entered_otp != stored_otp:

        flash(
            'Incorrect OTP! Please enter the correct OTP.',
            'danger'
        )

        return redirect('/user-verify-otp')


    # -------------------------------------------------------------
    # OTP SUCCESS
    # -------------------------------------------------------------

    flash(
        'OTP verified successfully!',
        'success'
    )

    return redirect('/user-create-password')


# =================================================================
# USER CREATE PASSWORD
# =================================================================

@app.route('/user-create-password', methods=['GET', 'POST'])
def user_create_password():

    # -------------------------------------------------------------
    # CHECK OTP VERIFICATION
    # -------------------------------------------------------------

    if 'user_register_email' not in session:

        flash(
            'Please complete email verification first.',
            'danger'
        )

        return redirect('/user-register')


    # -------------------------------------------------------------
    # GET REQUEST
    # -------------------------------------------------------------

    if request.method == 'GET':

        return render_template(
            'user/create_password.html',
            email=session['user_register_email']
        )


    # -------------------------------------------------------------
    # GET PASSWORD
    # -------------------------------------------------------------

    password = request.form.get(
        'password',
        ''
    )

    confirm_password = request.form.get(
        'confirm_password',
        ''
    )


    # -------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------

    if not password or not confirm_password:

        flash(
            'Both password fields are required.',
            'danger'
        )

        return redirect('/user-create-password')


    if len(password) < 6:

        flash(
            'Password must contain at least 6 characters.',
            'danger'
        )

        return redirect('/user-create-password')


    # -------------------------------------------------------------
    # CHECK PASSWORD MATCH
    # -------------------------------------------------------------

    if password != confirm_password:

        flash(
            'Passwords do not match!',
            'danger'
        )

        return redirect('/user-create-password')


    # -------------------------------------------------------------
    # GET USER DETAILS FROM SESSION
    # -------------------------------------------------------------

    name = session['user_register_name']
    email = session['user_register_email']


    # -------------------------------------------------------------
    # HASH PASSWORD
    # -------------------------------------------------------------

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


    # -------------------------------------------------------------
    # DATABASE CONNECTION
    # -------------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        # ---------------------------------------------------------
        # CREATE USER
        # ---------------------------------------------------------

        cursor.execute(
            '''
            INSERT INTO users
            (name, email, password, is_verified)
            VALUES (?, ?, ?, ?)
            ''',
            (
                name,
                email,
                hashed_password,
                True
            )
        )

        conn.commit()


    except sqlite3.Error as e:

        conn.rollback()

        print('DATABASE ERROR:', e)

        cursor.close()
        conn.close()

        flash(
            'Unable to create account. Please try again.',
            'danger'
        )

        return redirect('/user-register')


    cursor.close()
    conn.close()


    # -------------------------------------------------------------
    # CLEAR REGISTRATION SESSION
    # -------------------------------------------------------------

    session.pop('user_register_name', None)
    session.pop('user_register_email', None)
    session.pop('user_register_otp', None)


    # -------------------------------------------------------------
    # REGISTRATION SUCCESS
    # -------------------------------------------------------------

    flash(
        'Account created successfully! Please login.',
        'success'
    )

    return redirect('/user-login')

# =================================================================
# USER LOGIN
# =================================================================

@app.route('/user-login', methods=['GET', 'POST'])
def user_login():

    # -------------------------------------------------------------
    # GET REQUEST
    # -------------------------------------------------------------

    if request.method == 'GET':

        return render_template(
            'user/user_login.html'
        )


    # -------------------------------------------------------------
    # GET FORM DATA
    # -------------------------------------------------------------

    email = request.form.get(
        'email',
        ''
    ).strip().lower()

    password = request.form.get(
        'password',
        ''
    )


    # -------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------

    if not email or not password:

        flash(
            'Email and password are required.',
            'danger'
        )

        return redirect('/user-login')


    # -------------------------------------------------------------
    # FIND USER
    # -------------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT
            user_id,
            name,
            email,
            password,
            is_verified
        FROM users
        WHERE email=?
        ''',
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()


    # -------------------------------------------------------------
    # USER NOT FOUND
    # -------------------------------------------------------------

    if not user:

        flash(
            'Email not found. Please register first.',
            'danger'
        )

        return redirect('/user-login')


    # -------------------------------------------------------------
    # CHECK EMAIL VERIFICATION
    # -------------------------------------------------------------

    if not user['is_verified']:

        flash(
            'Please verify your email first.',
            'warning'
        )

        return redirect('/user-login')


    # -------------------------------------------------------------
    # CHECK PASSWORD
    # -------------------------------------------------------------

    stored_hashed_password = user['password']
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(
        password.encode('utf-8'),
        stored_hashed_password
    ):

        flash(
            'Incorrect password!',
            'danger'
        )

        return redirect('/user-login')


    # -------------------------------------------------------------
    # CREATE LOGIN SESSION
    # -------------------------------------------------------------

    session.clear()

    session['user_id'] = user['user_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']


    # -------------------------------------------------------------
    # LOGIN SUCCESS
    # -------------------------------------------------------------

    flash(
        'Login successful!',
        'success'
    )

    return redirect('/user-dashboard')


# =================================================================
# USER FORGOT PASSWORD - REQUEST OTP
# =================================================================
@app.route('/user-forgot-password', methods=['GET', 'POST'])
def user_forgot_password():
    if request.method == 'GET':
        return render_template('user/forgot_password.html')

    email = request.form.get('email', '').strip().lower()
    if not email:
        flash("Email address is required!", "danger")
        return redirect('/user-forgot-password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("No account found with that email address.", "danger")
        return redirect('/user-forgot-password')

    otp = str(random.randint(100000, 999999))
    session['user_forgot_email'] = email
    session['user_forgot_otp'] = otp

    try:
        msg = Message(
            subject="SmartCart - Password Reset OTP",
            sender=config.MAIL_USERNAME,
            recipients=[email]
        )
        msg.body = f"Hello {user.get('name', 'Customer')},\n\nYour SmartCart password reset OTP is: {otp}\n\nDo not share this OTP with anyone.\n\nRegards,\nSmartCart Team"
        mail.send(msg)
    except Exception as e:
        print("MAIL ERROR:", e)

    flash("Password reset OTP sent to your email!", "success")
    return redirect('/user-forgot-verify-otp')


# =================================================================
# USER FORGOT PASSWORD - VERIFY OTP
# =================================================================
@app.route('/user-forgot-verify-otp', methods=['GET', 'POST'])
def user_forgot_verify_otp():
    if 'user_forgot_email' not in session:
        flash("Session expired. Please request a new OTP.", "danger")
        return redirect('/user-forgot-password')

    if request.method == 'GET':
        return render_template('user/forgot_verify_otp.html', email=session['user_forgot_email'])

    entered_otp = request.form.get('otp', '').strip()
    stored_otp = session.get('user_forgot_otp', '')

    if entered_otp != stored_otp:
        flash("Invalid OTP! Please enter the correct code.", "danger")
        return redirect('/user-forgot-verify-otp')

    session['user_forgot_verified'] = True
    flash("OTP verified! Please create your new password.", "success")
    return redirect('/user-forgot-reset-password')


# =================================================================
# USER FORGOT PASSWORD - RESET PASSWORD
# =================================================================
@app.route('/user-forgot-reset-password', methods=['GET', 'POST'])
def user_forgot_reset_password():
    if 'user_forgot_email' not in session or not session.get('user_forgot_verified'):
        flash("Please verify your OTP first.", "danger")
        return redirect('/user-forgot-password')

    if request.method == 'GET':
        return render_template('user/reset_password.html', email=session['user_forgot_email'])

    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not password or not confirm_password:
        flash("Both password fields are required.", "danger")
        return redirect('/user-forgot-reset-password')

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect('/user-forgot-reset-password')

    if password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect('/user-forgot-reset-password')

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed_password, session['user_forgot_email']))
    conn.commit()
    cursor.close()
    conn.close()

    session.pop('user_forgot_email', None)
    session.pop('user_forgot_otp', None)
    session.pop('user_forgot_verified', None)

    flash("Password updated successfully! Please login with your new password.", "success")
    return redirect('/user-login')


# =================================================================
# USER DASHBOARD
# =================================================================

@app.route('/user-dashboard')
def user_dashboard():

    # -------------------------------------------------------------
    # CHECK LOGIN
    # -------------------------------------------------------------

    if 'user_id' not in session:

        flash(
            'Please login first.',
            'danger'
        )

        return redirect('/user-login')


    # -------------------------------------------------------------
    # SHOW DASHBOARD
    # -------------------------------------------------------------

    return render_template(
        'user/user_home.html',
        user_name=session['user_name'],
        user_email=session['user_email']
    )

# =================================================================
# USER LOGOUT
# =================================================================

@app.route('/user-logout')
def user_logout():

    session.clear()

    flash(
        'Logged out successfully!',
        'success'
    )

    return redirect('/user-login')

# ROUTE: USER PRODUCT LISTING (SEARCH + FILTER)
# =================================================================
@app.route('/user/products')
def user_products():

    # Optional: restrict only logged-in users
    if 'user_id' not in session:
        flash("Please login to view products!", "danger")
        return redirect('/user-login')

    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch categories for filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()

    # Build dynamic SQL
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append("%" + search + "%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    cursor.execute(query, params)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "user/user_products.html",
        products=products,
        categories=categories
    )
# =================================================================
# ROUTE: USER PRODUCT DETAILS PAGE
# =================================================================
@app.route('/user/product/<int:product_id>')
def user_product_details(product_id):

    if 'user_id' not in session:
        flash("Please login!", "danger")
        return redirect('/user-login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    return render_template("user/product_details.html", product=product)

# =================================================================
# ADD ITEM TO CART
# =================================================================
@app.route('/user/add-to-cart/<int:product_id>')
def add_to_cart(product_id):

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Create cart if doesn't exist
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect(request.referrer)

    pid = str(product_id)

    # If exists → increase quantity
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }

    session['cart'] = cart

    flash("Item added to cart!", "success")
    return redirect(request.referrer) 
  

# =================================================================
# VIEW CART PAGE
# =================================================================
@app.route('/user/cart')
def view_cart():

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    cart = session.get('cart', {})

    # Calculate total
    grand_total = sum(item['price'] * item['quantity'] for item in cart.values())

    return render_template("user/cart.html", cart=cart, grand_total=grand_total)

# =================================================================
# INCREASE QUANTITY
# =================================================================
@app.route('/user/cart/increase/<pid>')
def increase_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] += 1

    session['cart'] = cart
    return redirect('/user/cart')

# =================================================================
# DECREASE QUANTITY
# =================================================================
@app.route('/user/cart/decrease/<pid>')
def decrease_quantity(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart[pid]['quantity'] -= 1

        # If quantity becomes 0 → remove item
        if cart[pid]['quantity'] <= 0:
            cart.pop(pid)

    session['cart'] = cart
    return redirect('/user/cart')

# =================================================================
# REMOVE ITEM
# =================================================================
@app.route('/user/cart/remove/<pid>')
def remove_from_cart(pid):

    cart = session.get('cart', {})

    if pid in cart:
        cart.pop(pid)

    session['cart'] = cart

    flash("Item removed!", "success")
    return redirect('/user/cart')

# buy now
@app.route('/user/buy-now/<int:product_id>')
def buy_now(product_id):

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get product
    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    # Product not found
    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    # Open address page
    return render_template(
        'user/address.html',
        product=product
    )
# Proceed to Pay route
@app.route('/user/proceed-to-pay/<int:product_id>', methods=['POST'])
def proceed_to_pay(product_id):

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Get address information
    full_name = request.form.get('full_name')
    mobile = request.form.get('mobile')
    house = request.form.get('house')
    street = request.form.get('street')
    city = request.form.get('city')
    state = request.form.get('state')
    pincode = request.form.get('pincode')

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    # Product not found
    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    # Store Buy Now product ID
    session['buy_now_product_id'] = product_id

    # Store address temporarily in session
    session['buy_now_address'] = {
        'full_name': full_name,
        'mobile': mobile,
        'house': house,
        'street': street,
        'city': city,
        'state': state,
        'pincode': pincode
    }

    # Go to payment route
    return redirect(
        f'/user/payment/{product_id}'
    )
# Payment route
@app.route('/user/payment/<int:product_id>')
def payment(product_id):

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    # Check address
    if 'buy_now_address' not in session:
        flash("Please enter delivery address first!", "danger")
        return redirect(
            f'/user/buy-now/{product_id}'
        )

    # Get product
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    # Product not found
    if not product:
        flash("Product not found!", "danger")
        return redirect('/user/products')

    # Store Buy Now product ID
    session['buy_now_product_id'] = product_id

    # Product price
    total_amount = float(product['price'])

    # Convert rupees to paise
    razorpay_amount = int(total_amount * 100)

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    # Store Razorpay order ID
    session['razorpay_order_id'] = razorpay_order['id']

    # Render payment page
    return render_template(
        'user/payment.html',
        product=product,
        amount=total_amount,
        key_id=config.RAZORPAY_KEY_ID,
        order_id=razorpay_order['id']
    )
# =========================================================
# VERIFY PAYMENT
# =========================================================

@app.route('/verify-payment', methods=['POST'])
def verify_payment():

    # -----------------------------------------------------
    # CHECK LOGIN
    # -----------------------------------------------------

    if 'user_id' not in session:
        flash(
            "Please login to complete the payment.",
            "danger"
        )
        return redirect('/user-login')


    # -----------------------------------------------------
    # GET RAZORPAY RESPONSE
    # -----------------------------------------------------

    razorpay_payment_id = request.form.get(
        'razorpay_payment_id'
    )

    razorpay_order_id = request.form.get(
        'razorpay_order_id'
    )

    razorpay_signature = request.form.get(
        'razorpay_signature'
    )


    # -----------------------------------------------------
    # CHECK PAYMENT DATA
    # -----------------------------------------------------

    if not (
        razorpay_payment_id
        and razorpay_order_id
        and razorpay_signature
    ):

        flash(
            "Payment verification failed (missing data).",
            "danger"
        )

        return redirect('/user/products')


    # -----------------------------------------------------
    # VERIFY RAZORPAY PAYMENT
    # -----------------------------------------------------

    payload = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }


    try:

        razorpay_client.utility.verify_payment_signature(
            payload
        )

    except Exception as e:

        app.logger.error(
            "Razorpay signature verification failed: %s",
            str(e)
        )

        flash(
            "Payment verification failed. Please contact support.",
            "danger"
        )

        return redirect('/user/products')


    # -----------------------------------------------------
    # GET USER
    # -----------------------------------------------------

    user_id = session['user_id']


    # -----------------------------------------------------
    # GET BUY NOW PRODUCT
    # -----------------------------------------------------

    product_id = session.get(
        'buy_now_product_id'
    )


    # -----------------------------------------------------
    # GET DELIVERY ADDRESS
    # -----------------------------------------------------

    address = session.get(
        'buy_now_address'
    )


    # -----------------------------------------------------
    # CHECK ORDER INFORMATION
    # -----------------------------------------------------

    if not product_id or not address:

        flash(
            "Order information is missing.",
            "danger"
        )

        return redirect('/user/products')


    # -----------------------------------------------------
    # GET PRODUCT FROM DATABASE
    # -----------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    conn.close()


    # -----------------------------------------------------
    # PRODUCT NOT FOUND
    # -----------------------------------------------------

    if not product:

        flash(
            "Product not found. Order cannot be created.",
            "danger"
        )

        return redirect('/user/products')


    # =====================================================
    # PRICE CALCULATION
    # =====================================================

    quantity = 1

    unit_price = float(
        product['price']
    )

    subtotal = unit_price * quantity

    delivery_charge = 0.00

    grand_total = subtotal + delivery_charge


    # =====================================================
    # SAVE ORDER
    # =====================================================

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # CREATE COMPLETE ADDRESS
        # -------------------------------------------------

        complete_address = (
            f"{address.get('house')}, "
            f"{address.get('street')}"
        )


        # -------------------------------------------------
        # INSERT ORDER
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO orders
            (
                user_id,
                razorpay_order_id,
                razorpay_payment_id,
                amount,
                payment_status,
                customer_name,
                customer_phone,
                shipping_address,
                shipping_city,
                shipping_state,
                shipping_pincode
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
        """, (
            user_id,
            razorpay_order_id,
            razorpay_payment_id,
            grand_total,
            'paid',
            address.get('full_name'),
            address.get('mobile'),
            complete_address,
            address.get('city'),
            address.get('state'),
            address.get('pincode')
        ))


        # -------------------------------------------------
        # GET ORDER ID
        # -------------------------------------------------

        order_db_id = cursor.lastrowid


        # -------------------------------------------------
        # SAVE ORDER ITEM
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO order_items
            (
                order_id,
                product_id,
                product_name,
                quantity,
                price
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?
            )
        """, (
            order_db_id,
            product_id,
            product['name'],
            quantity,
            unit_price
        ))


        # -------------------------------------------------
        # SAVE CHANGES
        # -------------------------------------------------

        conn.commit()


        # -------------------------------------------------
        # REMOVE TEMPORARY SESSION DATA
        # -------------------------------------------------

        session.pop(
            'buy_now_product_id',
            None
        )

        session.pop(
            'buy_now_address',
            None
        )

        session.pop(
            'razorpay_order_id',
            None
        )


        # -------------------------------------------------
        # SUCCESS MESSAGE
        # -------------------------------------------------

        flash(
            "Payment successful and order placed!",
            "success"
        )


        # -------------------------------------------------
        # GO TO ORDER SUCCESS PAGE
        # -------------------------------------------------

        return redirect(
            f'/user/order-success/{order_db_id}'
        )


    except Exception as e:

        # -------------------------------------------------
        # ROLLBACK
        # -------------------------------------------------

        conn.rollback()

        app.logger.error(
            "Order storage failed: %s\n%s",
            str(e),
            traceback.format_exc()
        )

        flash(
            "There was an error saving your order. Please contact support.",
            "danger"
        )

        return redirect('/user/products')


    finally:

        cursor.close()
        conn.close()
@app.route('/user/order-success/<int:order_id>')
def order_success(order_id):

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get order
    cursor.execute("""
        SELECT *
        FROM orders
        WHERE order_id = ?
        AND user_id = ?
    """, (order_id, user_id))

    order = cursor.fetchone()

    # Get order items
    cursor.execute("""
        SELECT *
        FROM order_items
        WHERE order_id = ?
    """, (order_id,))

    order_items = cursor.fetchall()

    cursor.close()
    conn.close()

    # Order not found
    if not order:
        flash("Order not found!", "danger")
        return redirect('/user/products')

    return render_template(
        'user/order_success.html',
        order=order,
        order_items=order_items
    )
@app.route('/user/my-orders')
def my_orders():

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'user/my_orders.html',
        orders=orders
    )


@app.route('/user/download-invoice/<int:order_id>')
def download_invoice(order_id):

    # Check login
    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/user-login')

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get order
    cursor.execute("""
        SELECT *
        FROM orders
        WHERE order_id = ?
        AND user_id = ?
    """, (order_id, user_id))

    order = cursor.fetchone()

    # Get order items
    cursor.execute("""
        SELECT *
        FROM order_items
        WHERE order_id = ?
    """, (order_id,))

    order_items = cursor.fetchall()

    cursor.close()
    conn.close()

    # Order not found
    if not order:
        flash("Order not found!", "danger")
        return redirect('/user/my-orders')

    # Generate invoice HTML
    html = render_template(
        'user/invoice.html',
        order=order,
        order_items=order_items
    )

    # Generate PDF
    pdf = generate_pdf(html)

    if pdf is None:

        flash(
            "Unable to generate invoice.",
            "danger"
        )

        return redirect('/user/my-orders')

    # Create response
    response = make_response(pdf)

    response.headers[
        'Content-Type'
    ] = 'application/pdf'

    response.headers[
        'Content-Disposition'
    ] = (
        f'attachment; '
        f'filename=invoice_{order_id}.pdf'
    )

    return response


# =================================================================
# RUN FLASK APPLICATION
# =================================================================

if __name__ == '__main__':
    app.run(debug=True)