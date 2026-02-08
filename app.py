
import os
import sqlite3
import subprocess
import requests
from flask import Flask, render_template, request, redirect, url_for, session, send_file, send_from_directory, g

app = Flask(__name__)
app.secret_key = 'super_secret_key_that_is_not_secure_at_all'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['DB_NAME'] = 'database.db'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------
# DATABASE SETUP
# -------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DB_NAME'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                email TEXT,
                full_name TEXT
            )
        ''')

        # Create Products Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                image_url TEXT,
                stock INTEGER DEFAULT 100
            )
        ''')

        # Create Orders Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_date TEXT,
                total REAL,
                status TEXT
            )
        ''')

        # Seed Data - Users
        # Check if users exist
        cursor.execute('SELECT count(*) FROM users')
        if cursor.fetchone()[0] == 0:
            # Generate random admin password (8-12 characters, alphanumeric)
            import secrets
            import string
            password_length = secrets.choice(range(8, 13))
            admin_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(password_length))
            
            cursor.execute("INSERT INTO users (username, password, role, email, full_name) VALUES ('admin', ?, 'admin', 'admin@vulnerable.com', 'System Administrator')", (admin_password,))
            cursor.execute("INSERT INTO users (username, password, role, email, full_name) VALUES ('user', 'password', 'user', 'user@vulnerable.com', 'Regular User')")
            cursor.execute("INSERT INTO users (username, password, role, email, full_name) VALUES ('alice', 'alice123', 'user', 'alice@vulnerable.com', 'Alice Wonderland')")
            
            print(f"[INIT] Admin password generated: {admin_password}")

        # Seed Data - Products
        cursor.execute('SELECT count(*) FROM products')
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO products (name, description, price, image_url) VALUES ('Vulnerable T-Shirt', 'Limited edition vulnerable item', 29.99, 'tshirt.jpg')")
            cursor.execute("INSERT INTO products (name, description, price, image_url) VALUES ('Insecure Hoodie', 'Keeps you warm, keeps your data exposed', 49.99, 'hoodie.jpg')")
            cursor.execute("INSERT INTO products (name, description, price, image_url) VALUES ('SQLi Mug', 'Select * from drinks', 15.00, 'mug.jpg')")
            
        # Seed Data - Orders (Optional, since we mock it in route for simplicity unless Lab 6 uses DB)
        # But let's add some rows anyway
        cursor.execute('SELECT count(*) FROM orders')
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO orders (user_id, order_date, total, status) VALUES (2, '2024-01-15', 29.99, 'Delivered')")
            cursor.execute("INSERT INTO orders (user_id, order_date, total, status) VALUES (2, '2024-02-10', 49.99, 'Processing')")

        db.commit()

# Initialize DB on start
if not os.path.exists(app.config['DB_NAME']):
    init_db()
else:
    # Re-run init to ensure tables exist if deleted
    init_db()


# -------------------------
# MAIN ROUTES
# -------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Intentionally vulnerable logic handled in labs
        # This is the "safe" standard login for the base app (still weak plaintext)
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            error = 'Invalid Credentials'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Simple registration
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists"
    return render_template('register.html')

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Mock orders for demonstration
    # In a real app this would query the DB for the user's orders
    orders = [
        {'id': 101, 'date': '2024-01-15', 'total': 29.99, 'status': 'Delivered'},
        {'id': 102, 'date': '2024-02-10', 'total': 49.99, 'status': 'Processing'},
        {'id': 103, 'date': '2024-03-05', 'total': 15.00, 'status': 'Shipped'}
    ]
    return render_template('orders.html', orders=orders)

@app.route('/products')
def product_list():
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('product_list.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product:
        return render_template('product_detail.html', product=product)
    else:
        return "Product not found", 404


# -------------------------
# LAB 1: Path Traversal (Multiple Variations)
# -------------------------
@app.route('/lab1')
def lab1():
    return render_template('lab1/index.html')

# Helper function to create files for all lab1 variations
def create_lab1_files(subdir, files):
    files_dir = os.path.join('data', subdir)
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
    
    for f in files:
        f_path = os.path.join(files_dir, f)
        if not os.path.exists(f_path):
            with open(f_path, 'w') as file:
                file.write(f"This is content of {f}")

# LAB 1.1: DocuVault (Document Management)
@app.route('/lab1/1')
def lab1_1():
    files = [
        'Invoice_2024_001.pdf', 
        'Invoice_2024_002.pdf', 
        'Project_Alpha_Specs.docx', 
        'Q1_Financial_Report.xlsx', 
        'Meeting_Minutes_Jan.txt',
        'Employee_Handbook_v2.pdf',
        'Architecture_Diagram_Final.png',
        'Client_Contract_AcmeCorp.pdf',
        'Budget_Allocation_2024.xlsx',
        'Security_Policy_Draft.docx',
        'Server_Logs_Backup.txt',
        'Marketing_Assets.zip',
        'Team_Photo_Retreat.jpg',
        'Vendor_List.csv',
        'readme.txt'
    ]
    create_lab1_files('docuvault/invoices', files)
    return render_template('lab1/sub1.html', files=files)

@app.route('/lab1/1/download')
def lab1_1_download():
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
    
    try:
        base_dir = os.getcwd()
        intended_dir = os.path.join(base_dir, 'data', 'docuvault', 'invoices')
        file_path = os.path.join(intended_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=False, mimetype='text/plain')
        else:
            return f"File not found: {file_path}", 404
    except Exception as e:
        return str(e), 500

# LAB 1.2: ShopExpress (Coffee Shop Theme - Path Traversal in Image Loading)
@app.route('/lab1/2')
def lab1_2():
    # E-commerce Product List
    products = [
        {
            'id': 1,
            'name': 'Eco-Friendly Bamboo Coffee Cup',
            'description': 'Sustainable bamboo cup with silicone lid and grip. Perfect for your daily brew.',
            'price': 12.99,
            'image': 'prod_1.png'
        },
        {
            'id': 2,
            'name': 'Recycled Plastic Travel Mug',
            'description': 'Made from 100% recycled plastics. Durable and leak-proof.',
            'price': 15.50,
            'image': 'prod_2.png'
        },
        {
            'id': 3,
            'name': 'Ceramic Artisan Mug',
            'description': 'Hand-crafted ceramic mug with unique glaze patterns.',
            'price': 18.00,
            'image': 'prod_3.png'
        },
        {
            'id': 4,
            'name': 'Stainless Steel Thermal Flask',
            'description': 'Keeps your coffee hot for up to 6 hours. Double-walled insulation.',
            'price': 24.99,
            'image': 'prod_4.png'
        },
         {
            'id': 5,
            'name': 'Glass Coffee Cup with Cork Band',
            'description': 'Elegant glass design with a heat-resistant cork band.',
            'price': 14.95,
            'image': 'prod_5.png'
        },
        {
            'id': 6,
            'name': 'Compostable Takeaway Cup (Pack of 50)',
            'description': 'Fully compostable cups for events or office use.',
            'price': 29.99,
            'image': 'prod_6.png'
        }
    ]
    return render_template('lab1/sub2.html', products=products)

@app.route('/lab1/2/image')
def lab1_2_image():
    filename = request.args.get('filename')
    if not filename:
        return "No filename specified", 400
    
    # VULNERABILITY: Path Traversal
    # Intended directory is 'img' folder in root
    base_dir = os.getcwd()
    intended_dir = os.path.join(base_dir, 'img')
    file_path = os.path.join(intended_dir, filename)
    
    # We should normalize path to check if it's safe (which we WON'T do for the vulnerability)
    # But we will check if it exists
    
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    else:
        return f"Image not found: {file_path}", 404

# LAB 1.3: MediaHub (Stock Photo Marketplace Theme)
@app.route('/lab1/3')
def lab1_3():
    # Rich media objects for a "Real Website" look
    # Using files that exist in the 'img' folder
    media_items = [
        {'file': 'summer_vacation_001.jpg', 'title': 'Golden Hour Beach', 'author': 'Sarah Jenkins', 'tags': ['Nature', 'Travel'], 'views': '2.4k', 'price': 29},
        {'file': 'office_party_2023.jpg', 'title': 'Corporate Celebration', 'author': 'TechLife Media', 'tags': ['Business', 'Events'], 'views': '1.1k', 'price': 49},
        {'file': 'product_launch.jpg', 'title': 'Minimalist Product Shot', 'author': 'Studio 54', 'tags': ['Product', 'Minimal'], 'views': '8.5k', 'price': 99},
        {'file': 'hiking_adventure.jpg', 'title': 'Mountain Summit', 'author': 'Alex Climbs', 'tags': ['Adventure', 'Nature'], 'views': '5k', 'price': 35},
        {'file': 'design_mockup_v2.jpg', 'title': 'UI/UX Dashboard Kit', 'author': 'Creative UI', 'tags': ['Tech', 'Design'], 'views': '12k', 'price': 59},
        {'file': 'city_skyline.jpg', 'title': 'Urban Nightlife', 'author': 'City Lights', 'tags': ['City', 'Travel'], 'views': '3.2k', 'price': 45},
        {'file': 'abstract_background.jpg', 'title': 'Neon Abstract 4K', 'author': 'Digital Dreams', 'tags': ['Abstract', 'Art'], 'views': '900', 'price': 15},
        {'file': 'coffee_break.jpg', 'title': 'Morning Espresso', 'author': 'Barista Daily', 'tags': ['Food', 'Lifestyle'], 'views': '4.1k', 'price': 25},
        
    ]
    
    # Extract just filenames for file creation (backend logic)
    filenames = [item['file'] for item in media_items]
    create_lab1_files('mediahub/gallery/uploads', filenames)
    
    # Pass full objects to template
    return render_template('lab1/sub3.html', files=media_items)

# Helper route to serve images for Lab 1.3 preview
@app.route('/lab1/3/preview/<path:filename>')
def lab1_3_preview(filename):
    # Serve directly from the 'img' folder in the root directory
    base_dir = os.getcwd()
    img_dir = os.path.join(base_dir, 'img')
    return send_from_directory(img_dir, filename)

@app.route('/lab1/3/download')
def lab1_3_download():
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
    
    try:
        base_dir = os.getcwd()
        intended_dir = os.path.join(base_dir, 'data', 'mediahub', 'gallery', 'uploads')
        file_path = os.path.join(intended_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=False, mimetype='text/plain')
        else:
            return f"File not found: {file_path}", 404
    except Exception as e:
        return str(e), 500


# -------------------------
# LAB 2: Access Control
# -------------------------
@app.route('/lab2')
def lab2():
    return render_template('lab2/index.html')

# Lab 2 Variation Menus
@app.route('/lab2/1/menu')
def lab2_1_menu():
    return render_template('lab2/sub1_menu.html')

@app.route('/lab2/2/menu')
def lab2_2_menu():
    return render_template('lab2/sub2_menu.html')

@app.route('/lab2/3/menu')
def lab2_3_menu():
    return render_template('lab2/sub3_menu.html')

@app.route('/lab2/4/menu')
def lab2_4_menu():
    return render_template('lab2/sub4_menu.html')

@app.route('/lab2/5/menu')
def lab2_5_menu():
    return render_template('lab2/sub5_menu.html')

# LAB 2.1: Robots.txt
# LAB 2.1: Robots.txt (Shared vulnerability, but accessed via specific paths in a real scenario)
# Variation A Robots.txt
@app.route('/lab2/1/robots.txt')
def robots_txt_a():
    # Serve real static file
    base_dir = os.getcwd()
    file_dir = os.path.join(base_dir, 'static', 'lab2', '1', 'a')
    return send_from_directory(file_dir, 'robots.txt')

# Variation B Robots.txt
@app.route('/lab2/1/b/robots.txt')
def robots_txt_b():
    # Serve real static file
    base_dir = os.getcwd()
    file_dir = os.path.join(base_dir, 'static', 'lab2', '1', 'b')
    return send_from_directory(file_dir, 'robots.txt')

# Variation C Robots.txt
@app.route('/lab2/1/c/robots.txt')
def robots_txt_c():
    # Serve real static file
    base_dir = os.getcwd()
    file_dir = os.path.join(base_dir, 'static', 'lab2', '1', 'c')
    return send_from_directory(file_dir, 'robots.txt')

@app.route('/lab2/1')
def lab2_1():
    # TechStore Products (Theme A)
    products = [
        {'id': 101, 'name': 'Quantum X1 Laptop', 'price': 1299, 'desc': 'Next-gen processing power.', 'badge': 'New'},
        {'id': 102, 'name': 'Nebula Phone 5G', 'price': 899, 'desc': 'Capture the universe in your pocket.', 'badge': 'Bestseller'},
        {'id': 103, 'name': 'Void Cancelling Headphones', 'price': 249, 'desc': 'Silence the world around you.', 'badge': ''},
        {'id': 104, 'name': 'SmartHome Hub', 'price': 149, 'desc': 'Control your reality with voice.', 'badge': 'Sale'},
        {'id': 105, 'name': 'CyberWatch Pro', 'price': 399, 'desc': 'Health monitoring from the future.', 'badge': ''},
        {'id': 106, 'name': 'Holographic Drone', 'price': 599, 'desc': '4K recording in 3D space.', 'badge': ''},
    ]
    return render_template('lab2/sub1.html', products=products)

@app.route('/lab2/1/b')
def lab2_1b():
    # FashionHub Products (Theme B)
    products = [
        {'id': 201, 'name': 'Velvet Evening Gown', 'price': 299, 'desc': 'Elegant and timeless.', 'badge': 'Trending'},
        {'id': 202, 'name': 'Urban Street Hoodie', 'price': 89, 'desc': 'Comfort meets style.', 'badge': 'New'},
        {'id': 203, 'name': 'Designer Leather Bag', 'price': 450, 'desc': 'Italian craftsmanship.', 'badge': ''},
        {'id': 204, 'name': 'Silk Scarf Collection', 'price': 55, 'desc': '100% pure silk.', 'badge': 'Sale'},
    ]
    return render_template('lab2/sub1_b.html', products=products)

@app.route('/lab2/1/c')
def lab2_1c():
    # FoodMart Products (Theme C)
    products = [
        {'id': 301, 'name': 'Organic Avocado Box', 'price': 15, 'desc': 'Fresh from the farm.', 'badge': 'Organic'},
        {'id': 302, 'name': 'Artisan Sourdough', 'price': 8, 'desc': 'Baked fresh daily.', 'badge': ''},
        {'id': 303, 'name': 'Gourmet Cheese Platter', 'price': 45, 'desc': 'Selection of fine cheeses.', 'badge': 'Best Value'},
        {'id': 304, 'name': 'Cold Pressed Juice Kit', 'price': 30, 'desc': 'Detox and refresh.', 'badge': ''},
    ]
    return render_template('lab2/sub1_c.html', products=products)

@app.route('/lab2/1/super_secret_admin_panel_xyz', methods=['GET', 'POST'])
def lab2_1_admin():
    users = [
        {'id': 101, 'username': 'testuser1'}
    ]
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id == '101':
            return render_template('lab2/sub1_admin.html', users=[], flag="FLAG{robots_txt_enumerated_sucessfully}")
    return render_template('lab2/sub1_admin.html', users=users, flag=None)


# LAB 2.2: Hidden Link / Conditional Logic (Variation A: GadgetShop)
@app.route('/lab2/2')
def lab2_2():
    # Admin URL is hidden in the source code logic
    products = [
        {'id': 1, 'name': 'Smartphone X', 'price': 999},
        {'id': 2, 'name': 'Tablet Pro', 'price': 699},
    ]
    return render_template('lab2/sub2.html', products=products)

@app.route('/lab2/2/admin_dashboard_hidden_abc123', methods=['GET', 'POST'])
def lab2_2_admin():
    users = [{'id': 202, 'username': 'target_user'}]
    if request.method == 'POST':
        # "Deleting" user
        return render_template('lab2/sub2_admin.html', users=[], flag="FLAG{source_code_logic_bypass_mastered}")
    return render_template('lab2/sub2_admin.html', users=users, flag=None)

# LAB 2.2 Variation B: BookStore
@app.route('/lab2/2/b')
def lab2_2b():
    products = [
        {'id': 1, 'name': 'The Great Gatsby', 'price': 15},
        {'id': 2, 'name': '1984', 'price': 12},
    ]
    return render_template('lab2/sub2_b.html', products=products)

# LAB 2.2 Variation C: GameZone
@app.route('/lab2/2/c')
def lab2_2c():
    products = [
        {'id': 1, 'name': 'Elden Ring', 'price': 60},
        {'id': 2, 'name': 'Cyberpunk 2077', 'price': 50},
    ]
    return render_template('lab2/sub2_c.html', products=products)


# LAB 2.3: Cookie Manipulation
@app.route('/lab2/3', methods=['GET', 'POST'])
def lab2_3():
    # CHECK ADMIN COOKIE - If true, show admin page
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        # Show admin page directly
        db = get_db()
        
        # Handle user deletion (POST request)
        if request.method == 'POST':
            # User clicked delete - show flag
            return render_template('lab2/sub3_admin.html', users=[], flag="FLAG{cookie_manipulation_is_sweet}")
        
        # GET request - show users
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        return render_template('lab2/sub3_admin.html', users=users, flag=None)
    
    # Otherwise, show regular store page
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    
    current_user = request.cookies.get('session')  # Can be any identifier
    return render_template('lab2/sub3.html', products=products, username=current_user)

@app.route('/lab2/3/login', methods=['GET', 'POST'])
def lab2_3_login_page():
    # If GET, just redirect to store (modal should be used)
    if request.method == 'GET':
        return redirect(url_for('lab2_3'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple check 
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        
        if user:
            # SUCCESSFUL LOGIN
            is_admin_val = 'false'
            if user['role'] == 'admin':
                is_admin_val = 'true'
            
            # If admin, redirect to admin page directly
            if is_admin_val == 'true':
                resp = redirect(url_for('lab2_3_admin'))
            else:
                # Regular user goes to my-account page
                resp = redirect(url_for('lab2_3_my_account', id=username))
            
            resp.set_cookie('Admin', is_admin_val)
            resp.set_cookie('session', '5i06DbK0e5AUWufFfpCk8BnxM1sU81Me')
            return resp
        else:
            return redirect(url_for('lab2_3', login_error="Invalid Credentials"))

@app.route('/lab2/3/my-account', methods=['GET', 'POST'])
def lab2_3_my_account():
    # This acts as the "Store" or "Account" page
    # It takes ?id=username
    user_id = request.args.get('id')
    
    # CHECK ADMIN COOKIE - If true, show admin page
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        # Show admin page directly
        db = get_db()
        
        # Handle user deletion (POST request)
        if request.method == 'POST':
            # User clicked delete - show flag
            return render_template('lab2/sub3_admin.html', users=[], flag="FLAG{cookie_manipulation_is_sweet}")
        
        # GET request - show users
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        return render_template('lab2/sub3_admin.html', users=users, flag=None)
    
    # Otherwise, show regular store page
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    
    return render_template('lab2/sub3.html', products=products, username=user_id)

@app.route('/lab2/3/logout')
def lab2_3_logout():
    resp = redirect(url_for('lab2_3'))
    # Clear the NEW cookie names we set in login
    resp.set_cookie('Admin', '', expires=0)
    resp.set_cookie('session', '', expires=0)
    # Also clear old ones just in case
    resp.set_cookie('lab2_admin', '', expires=0)
    resp.set_cookie('lab2_user', '', expires=0)
    return resp

# New API to check admin status (explicit request for Burp analysis)
@app.route('/lab2/3/api/check_privileges')
def lab2_3_check_privileges():
    is_admin = request.cookies.get('Admin') == 'true'
    return {"is_admin": is_admin, "user": request.args.get('id')} # simplified

@app.route('/lab2/3/admin', methods=['GET', 'POST'])
def lab2_3_admin():
    # Check cookie
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        users = [{'id': 303, 'username': 'cookie_monster'}]
        if request.method == 'POST':
             return render_template('lab2/sub3_admin.html', users=[], flag="FLAG{cookie_manipulation_is_sweet}")
        return render_template('lab2/sub3_admin.html', users=users, flag=None)
    else:
        return "<h1>403 Forbidden</h1><p>Admin access required. Cookie 'Admin' is false.</p>", 403


# LAB 2.4: Parameter Tampering (IDOR)
@app.route('/lab2/4')
def lab2_4():
    # Main store page for Lab 2.4
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    
    # No session/cookies - purely URL-based
    return render_template('lab2/sub4.html', products=products, username=None, user_id=None)

@app.route('/lab2/4/login', methods=['GET', 'POST'])
def lab2_4_login():
    if request.method == 'GET':
        return redirect(url_for('lab2_4'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        
        if user:
            # NO SESSION/COOKIES - Just redirect with username in URL
            # This makes the IDOR vulnerability more obvious
            return redirect(url_for('lab2_4_myaccount', id=user['username']))
        else:
            return redirect(url_for('lab2_4', login_error="Invalid Credentials"))

@app.route('/lab2/4/my-account')
def lab2_4_myaccount():
    # VULNERABILITY: Trusts the 'id' parameter from URL without validation
    account_username = request.args.get('id')
    
    if not account_username:
        return redirect(url_for('lab2_4'))
    
    # Fetch user data based on USERNAME from URL parameter (IDOR vulnerability)
    db = get_db()
    account_user = db.execute('SELECT * FROM users WHERE username = ?', (account_username,)).fetchone()
    
    if not account_user:
        return "User not found", 404
    
    # Check if this is admin account (username: 'admin')
    if account_user['role'] == 'admin':
        # Show admin panel with flag immediately
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        return render_template('lab2/sub4_admin.html', 
                             account=account_user, 
                             flag="FLAG{parameter_tampering_idor_master}",
                             users=users)
    
    # Regular user account page
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('lab2/sub4_account.html', 
                         account=account_user, 
                         products=products)

@app.route('/lab2/4/logout')
def lab2_4_logout():
    # No session to clear - just redirect
    return redirect(url_for('lab2_4'))


# LAB 2.5: Password Disclosure via IDOR
@app.route('/lab2/5')
def lab2_5():
    # Main store page for Lab 2.5
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('lab2/sub5.html', products=products)

@app.route('/lab2/5/login', methods=['GET', 'POST'])
def lab2_5_login():
    if request.method == 'GET':
        return redirect(url_for('lab2_5'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        
        if user:
            # VULNERABILITY: Redirect to profile with username parameter
            # The profile page will expose the password in HTML
            return redirect(url_for('lab2_5_profile', username=user['username']))
        else:
            return redirect(url_for('lab2_5', login_error="Invalid Credentials"))

@app.route('/lab2/5/profile')
def lab2_5_profile():
    # VULNERABILITY: Trusts username parameter and exposes password in HTML comment
    username_param = request.args.get('username')
    
    if not username_param:
        return redirect(url_for('lab2_5'))
    
    # Fetch user data based on username parameter (IDOR vulnerability)
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
    
    if not user:
        return "User not found", 404
    
    # Check if admin accessed
    if user['role'] == 'admin':
        flag = "FLAG{password_disclosure_idor_master}"
    else:
        flag = None
    
    # VULNERABILITY: Password is exposed in the template (hidden in HTML comment)
    return render_template('lab2/sub5_profile.html', 
                         user=user, 
                         flag=flag)

@app.route('/lab2/5/logout')
def lab2_5_logout():
    return redirect(url_for('lab2_5'))

# End Lab 2


# -------------------------
# LAB 3: Authentication
# -------------------------
@app.route('/lab3')
def lab3():
    return render_template('lab3/index.html')

# LAB 3.1: Brute Force Attack
@app.route('/lab3/1')
def lab3_1():
    # Clear previous session data to ensure fresh credentials each time
    session.pop('lab3_1_admin_user', None)
    session.pop('lab3_1_admin_pass', None)
    session.pop('lab3_1_logged_in', None)
    session.pop('lab3_1_username', None)
    
    # Generate random credentials from wordlists each time lab is accessed
    import random
    
    usernames_file = os.path.join('data', 'wordlists', 'usernames.txt')
    passwords_file = os.path.join('data', 'wordlists', 'passwords.txt')
    
    # Read wordlists
    with open(usernames_file, 'r') as f:
        usernames = [line.strip() for line in f if line.strip()]
    with open(passwords_file, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]
    
    # Select random credentials
    admin_username = random.choice(usernames)
    admin_password = random.choice(passwords)
    
    # Store in session for this lab instance
    session['lab3_1_admin_user'] = admin_username
    session['lab3_1_admin_pass'] = admin_password
    
    # Log to console for testing (with timestamp for clarity)
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[LAB 3.1 - {timestamp}] New credentials generated: {admin_username} / {admin_password}")
    
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    
    return render_template('lab3/sub1.html', products=products)


@app.route('/lab3/1/login', methods=['POST'])
def lab3_1_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Get the correct credentials from session
    correct_user = session.get('lab3_1_admin_user', 'admin')
    correct_pass = session.get('lab3_1_admin_pass', 'password')
    
    # VULNERABILITY: No rate limiting, allows brute force
    if username == correct_user and password == correct_pass:
        session['lab3_1_logged_in'] = True
        session['lab3_1_username'] = username
        return redirect(url_for('lab3_1_admin'))
    else:
        # Return JSON for easier brute forcing
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/1/admin')
def lab3_1_admin():
    if not session.get('lab3_1_logged_in'):
        return redirect(url_for('lab3_1'))
    
    db = get_db()
    users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
    admin_user = session.get('lab3_1_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         flag=None)

@app.route('/lab3/1/admin/delete', methods=['POST'])
def lab3_1_delete_user():
    if not session.get('lab3_1_logged_in'):
        return redirect(url_for('lab3_1'))
    
    # Show flag after deletion
    admin_user = session.get('lab3_1_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         flag="FLAG{brute_force_authentication_master}")

@app.route('/lab3/1/logout')
def lab3_1_logout():
    session.pop('lab3_1_logged_in', None)
    session.pop('lab3_1_username', None)
    return redirect(url_for('lab3_1'))


# LAB 3.2: 2FA Bypass - Menu
@app.route('/lab3/2/menu')
def lab3_2_menu():
    return render_template('lab3/sub2_menu.html')

# LAB 3.2A: 2FA Bypass - SecureShop (Original)
@app.route('/lab3/2')
def lab3_2():
    # Clear any existing session
    session.pop('lab3_2_username', None)
    session.pop('lab3_2_verified', None)
    
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub2.html', products=products)

@app.route('/lab3/2/login', methods=['POST'])
def lab3_2_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Hardcoded credentials
    valid_users = {
        'wiener': 'peter',
        'carlos': 'montoya'
    }
    
    if username in valid_users and valid_users[username] == password:
        # Store username in session but NOT verified status
        session['lab3_2_username'] = username
        
        # Generate 2FA code (4 digits)
        import random
        code = str(random.randint(1000, 9999))
        session['lab3_2_code'] = code
        
        # Log code to console (simulating email)
        print(f"[LAB 3.2A] 2FA code for {username}: {code}")
        
        # Redirect to 2FA verification page
        return redirect(url_for('lab3_2_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2/verify')
def lab3_2_verify():
    username = session.get('lab3_2_username')
    if not username:
        return redirect(url_for('lab3_2'))
    
    code = session.get('lab3_2_code', '0000')
    return render_template('lab3/sub2_verify.html', username=username, code=code)

@app.route('/lab3/2/verify', methods=['POST'])
def lab3_2_verify_post():
    username = session.get('lab3_2_username')
    if not username:
        return redirect(url_for('lab3_2'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2_code')
    
    if submitted_code == correct_code:
        # Mark as verified
        session['lab3_2_verified'] = True
        return redirect(url_for('lab3_2_account'))
    else:
        return render_template('lab3/sub2_verify.html', 
                             username=username, 
                             code=session.get('lab3_2_code', '0000'),
                             error='Invalid verification code')

@app.route('/lab3/2/my-account')
def lab3_2_account():
    username = session.get('lab3_2_username')
    
    # VULNERABILITY: Only checks if username exists in session
    # Does NOT check if 2FA was completed (lab3_2_verified)
    if not username:
        return redirect(url_for('lab3_2'))
    
    # Check if this is carlos (victim) and 2FA was bypassed
    verified = session.get('lab3_2_verified', False)
    flag = None
    
    if username == 'carlos' and not verified:
        # 2FA was bypassed!
        flag = "FLAG{two_factor_authentication_bypass_master}"
    
    return render_template('lab3/sub2_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag)

@app.route('/lab3/2/logout')
def lab3_2_logout():
    session.pop('lab3_2_username', None)
    session.pop('lab3_2_verified', None)
    session.pop('lab3_2_code', None)
    return redirect(url_for('lab3_2'))


# LAB 3.2B: 2FA Bypass - BankSecure (Variation B)
@app.route('/lab3/2b')
def lab3_2b():
    session.pop('lab3_2b_username', None)
    session.pop('lab3_2b_verified', None)
    return render_template('lab3/sub2b.html')

@app.route('/lab3/2b/login', methods=['POST'])
def lab3_2b_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    valid_users = {'alice': 'alice123', 'bob': 'bob456'}
    
    if username in valid_users and valid_users[username] == password:
        session['lab3_2b_username'] = username
        import random
        code = str(random.randint(1000, 9999))
        session['lab3_2b_code'] = code
        print(f"[LAB 3.2B] 2FA code for {username}: {code}")
        return redirect(url_for('lab3_2b_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2b/verify')
def lab3_2b_verify():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    code = session.get('lab3_2b_code', '0000')
    return render_template('lab3/sub2b_verify.html', username=username, code=code, variation='B')

@app.route('/lab3/2b/verify', methods=['POST'])
def lab3_2b_verify_post():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2b_code')
    
    if submitted_code == correct_code:
        session['lab3_2b_verified'] = True
        return redirect(url_for('lab3_2b_account'))
    else:
        return render_template('lab3/sub2b_verify.html', 
                             username=username, 
                             code=session.get('lab3_2b_code', '0000'),
                             variation='B',
                             error='Invalid verification code')

@app.route('/lab3/2b/dashboard')
def lab3_2b_account():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    
    verified = session.get('lab3_2b_verified', False)
    flag = None
    
    if username == 'bob' and not verified:
        flag = "FLAG{two_factor_authentication_bypass_banksecure}"
    
    return render_template('lab3/sub2b_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag)

@app.route('/lab3/2b/logout')
def lab3_2b_logout():
    session.pop('lab3_2b_username', None)
    session.pop('lab3_2b_verified', None)
    session.pop('lab3_2b_code', None)
    return redirect(url_for('lab3_2b'))


# LAB 3.2C: 2FA Bypass - CloudDrive (Variation C)
@app.route('/lab3/2c')
def lab3_2c():
    session.pop('lab3_2c_username', None)
    session.pop('lab3_2c_verified', None)
    return render_template('lab3/sub2c.html')

@app.route('/lab3/2c/login', methods=['POST'])
def lab3_2c_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    valid_users = {'user1': 'pass1', 'admin': 'admin2024'}
    
    if username in valid_users and valid_users[username] == password:
        session['lab3_2c_username'] = username
        import random
        code = str(random.randint(1000, 9999))
        session['lab3_2c_code'] = code
        print(f"[LAB 3.2C] 2FA code for {username}: {code}")
        return redirect(url_for('lab3_2c_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2c/verify')
def lab3_2c_verify():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    code = session.get('lab3_2c_code', '0000')
    return render_template('lab3/sub2c_verify.html', username=username, code=code, variation='C')

@app.route('/lab3/2c/verify', methods=['POST'])
def lab3_2c_verify_post():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2c_code')
    
    if submitted_code == correct_code:
        session['lab3_2c_verified'] = True
        return redirect(url_for('lab3_2c_account'))
    else:
        return render_template('lab3/sub2c_verify.html', 
                             username=username, 
                             code=session.get('lab3_2c_code', '0000'),
                             variation='C',
                             error='Invalid verification code')

@app.route('/lab3/2c/files')
def lab3_2c_account():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    
    verified = session.get('lab3_2c_verified', False)
    flag = None
    
    if username == 'admin' and not verified:
        flag = "FLAG{two_factor_authentication_bypass_clouddrive}"
    
    return render_template('lab3/sub2c_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag)

@app.route('/lab3/2c/logout')
def lab3_2c_logout():
    session.pop('lab3_2c_username', None)
    session.pop('lab3_2c_verified', None)
    session.pop('lab3_2c_code', None)
    return redirect(url_for('lab3_2c'))



# -------------------------
# LAB 4: SSRF
# -------------------------
@app.route('/lab4')
def lab4():
    return render_template('lab4.html')

@app.route('/lab4/check_stock', methods=['POST'])
def lab4_check_stock():
    stock_api = request.form.get('stock_api')
    # VULNERABILITY: Fetches any URL provided by user
    # Try http://localhost:5000/lab2/admin 
    try:
        resp = requests.get(stock_api, timeout=2)
        return f"Stock Status from {stock_api}: <br><pre>{resp.text}</pre>"
    except Exception as e:
        return f"Error fetching stock: {e}"


# -------------------------
# LAB 5: File Upload
# -------------------------
@app.route('/lab5')
def lab5():
    return render_template('lab5.html')

@app.route('/lab5/upload', methods=['POST'])
def lab5_upload():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    
    # VULNERABILITY: No file extension validation
    # Saves file to public upload directory
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_url = url_for('static', filename=f'uploads/{filename}')
        return f"File uploaded successfully! <a href='{file_url}'>View File</a>"


# -------------------------
# LAB 6: OS Command Injection
# -------------------------
@app.route('/lab6')
def lab6():
    return render_template('lab6.html')

@app.route('/lab6/track', methods=['POST'])
def lab6_track():
    address = request.form.get('address')
    
    # VULNERABILITY: Command Injection
    # In a real scenario this might be a tracking ID, but we ping an IP here.
    # User can enter: 127.0.0.1 && dir
    ping_param = "-c" if os.name != "nt" else "-n"
    command = f"ping {ping_param} 1 {address}" 
    
    try:
        # shell=True allows command chaining
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return f"<pre>{output.decode('utf-8', errors='ignore')}</pre>"
    except subprocess.CalledProcessError as e:
        return f"<pre>Error: {e.output.decode('utf-8', errors='ignore')}</pre>"
    except Exception as e:
        return f"Error: {str(e)}"


# -------------------------
# LAB 7: SQL Injection
# -------------------------
@app.route('/lab7', methods=['GET', 'POST'])
def lab7():
    products = []
    if request.method == 'POST':
        search_term = request.form.get('search')
        
        # VULNERABILITY: Raw SQL String Formatting
        # Allow ' UNION SELECT ... --
        query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
        
        db = get_db()
        try:
            # Using execute with string formatted query (BAD PRACTICE)
            products = db.execute(query).fetchall()
        except Exception as e:
            return f"SQL Error: {e}"
            
    return render_template('lab7.html', products=products)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
