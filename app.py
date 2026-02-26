
import os
import sqlite3
import subprocess
import requests
import string
import random
import re
from flask import Flask, render_template, request, redirect, url_for, session, send_file, send_from_directory, g, jsonify

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

@app.route('/cart')
def cart():
    # Shopping cart page
    return render_template('cart.html')

@app.route('/checkout')
def checkout():
    # Checkout page
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('checkout.html')

@app.route('/help')
def help():
    # Help and FAQ page
    return render_template('help.html')


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
@app.route('/lab2/2/bookstore')
def lab2_2b():
    products = [
        {'id': 1, 'name': 'The Great Gatsby', 'price': 15, 'author': 'F. Scott Fitzgerald', 'image': 'gatsby.jpg'},
        {'id': 2, 'name': '1984', 'price': 12, 'author': 'George Orwell', 'image': '1984.jpg'},
        {'id': 3, 'name': 'To Kill a Mockingbird', 'price': 14, 'author': 'Harper Lee', 'image': 'mockingbird.jpg'},
        {'id': 4, 'name': 'Pride and Prejudice', 'price': 10, 'author': 'Jane Austen', 'image': 'pride.jpg'},
        {'id': 5, 'name': 'Moby Dick', 'price': 18, 'author': 'Herman Melville', 'image': 'moby.jpg'},
        {'id': 6, 'name': 'War and Peace', 'price': 25, 'author': 'Leo Tolstoy', 'image': 'war.jpg'},
    ]
    return render_template('lab2/sub2_b.html', products=products)

# LAB 2.2 Variation C: GameZone
@app.route('/lab2/2/gamezone')
def lab2_2c():
    products = [
        {'id': 1, 'name': 'Elden Ring', 'price': 59.99, 'platform': 'PC, PS5, Xbox', 'image': 'elden.jpg'},
        {'id': 2, 'name': 'Cyberpunk 2077', 'price': 49.99, 'platform': 'PC, PS5, Xbox', 'image': 'cyberpunk.jpg'},
        {'id': 3, 'name': 'God of War Ragnarok', 'price': 69.99, 'platform': 'PS5', 'image': 'gow.jpg'},
        {'id': 4, 'name': 'The Legend of Zelda', 'price': 59.99, 'platform': 'Switch', 'image': 'zelda.jpg'},
        {'id': 5, 'name': 'Red Dead Redemption 2', 'price': 39.99, 'platform': 'PC, PS5, Xbox', 'image': 'rdr2.jpg'},
        {'id': 6, 'name': 'Minecraft', 'price': 29.99, 'platform': 'Multiplatform', 'image': 'minecraft.jpg'},
        {'id': 7, 'name': 'Hollow Knight', 'price': 14.99, 'platform': 'PC, Switch', 'image': 'hollow.jpg'},
        {'id': 8, 'name': 'Hades', 'price': 24.99, 'platform': 'PC, Switch', 'image': 'hades.jpg'},
    ]
    return render_template('lab2/sub2_c.html', products=products)


# LAB 2.3: Cookie Manipulation


# Shared Helper for Lab 2.3 Cookie Logic
def handle_lab2_3_request(template_name, products):
    # CHECK ADMIN COOKIE - If true, show admin page
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        # Show admin page directly
        db = get_db()
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        
        # Handle user deletion (POST request simulation)
        flag = None
        if request.method == 'POST':
            flag = "FLAG{cookie_manipulation_is_sweet}"
            users = [] # Clear users to simulate deletion
            
        return render_template('lab2/sub3_admin.html', users=users, flag=flag)
    
    # Otherwise, show regular store page
    current_user = request.cookies.get('session')
    return render_template(template_name, products=products, username=current_user)

# Variation A: MusicStore
@app.route('/lab2/3/music', methods=['GET', 'POST'])
def lab2_3_music():
    products = [
        {'id': 1, 'name': 'Vinyl Classic: Abbey Road', 'price': 35, 'description': 'The Beatles masterpiece.'},
        {'id': 2, 'name': 'Sony WH-1000XM5', 'price': 349, 'description': 'Industry leading noise canceling.'},
        {'id': 3, 'name': 'Fender Stratocaster', 'price': 899, 'description': 'Electric guitar in sunburst.'},
        {'id': 4, 'name': 'Marshall Stanmore III', 'price': 379, 'description': 'Legendary sound at home.'},
    ]
    return handle_lab2_3_request('lab2/sub3_music.html', products)

# Variation B: SportsGear
@app.route('/lab2/3/sports', methods=['GET', 'POST'])
def lab2_3_sports():
    products = [
        {'id': 1, 'name': 'Pro Match Football', 'price': 45, 'description': 'FIFA quality certified.'},
        {'id': 2, 'name': 'Tennis Racket Elite', 'price': 189, 'description': 'Carbon fiber lightweight frame.'},
        {'id': 3, 'name': 'NBA Jersey - Lakers', 'price': 110, 'description': 'Authentic player edition.'},
        {'id': 4, 'name': 'Running Shoes zoom', 'price': 130, 'description': 'Marathon ready cushioning.'},
    ]
    return handle_lab2_3_request('lab2/sub3_sports.html', products)

# Variation C: PetShop
@app.route('/lab2/3/pets', methods=['GET', 'POST'])
def lab2_3_pets():
    products = [
        {'id': 1, 'name': 'Premium Dog Food', 'price': 55, 'description': 'Grain-free nutrition.'},
        {'id': 2, 'name': 'Cat Tree Tower', 'price': 85, 'description': 'Multi-level play area.'},
        {'id': 3, 'name': 'Aquarium Kit 20G', 'price': 120, 'description': 'Complete starter set with filter.'},
        {'id': 4, 'name': 'Hamster Wheel Silent', 'price': 25, 'description': 'No squeak running wheel.'},
    ]
    return handle_lab2_3_request('lab2/sub3_pets.html', products)

# Generic Lab 2.3 Login (Redirects based on referrer or param)
@app.route('/lab2/3/login', methods=['GET', 'POST'])
def lab2_3_login_page():
    # Helper to determine where to redirect back
    # In a real app we'd use 'next' param, here we'll check the referrer or default to Music
    referrer = request.referrer or ''
    if 'sports' in referrer:
        target_route = 'lab2_3_sports'
    elif 'pets' in referrer:
        target_route = 'lab2_3_pets'
    else:
        target_route = 'lab2_3_music' # Default

    if request.method == 'GET':
        return redirect(url_for(target_route))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        target_theme = request.form.get('theme', 'music') # Hidden field in login form
        
        if target_theme == 'sports': target_route = 'lab2_3_sports'
        elif target_theme == 'pets': target_route = 'lab2_3_pets'
        else: target_route = 'lab2_3_music'

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        
        if user:
            # SUCCESSFUL LOGIN
            is_admin_val = 'false'
            if user['role'] == 'admin':
                is_admin_val = 'true'
            
            # If admin, redirect to admin page directly? 
            # Actually, standard flow checks cookie on the main page.
            # So we redirect back to the store main page.
            
            resp = redirect(url_for(target_route))
            
            resp.set_cookie('Admin', is_admin_val)
            resp.set_cookie('session', '5i06DbK0e5AUWufFfpCk8BnxM1sU81Me')
            return resp
        else:
             return redirect(url_for(target_route, login_error="Invalid Credentials"))


@app.route('/lab2/3/logout')
def lab2_3_logout():
    # Redirect back to where they came from
    referrer = request.referrer or ''
    if 'sports' in referrer:
        target_route = 'lab2_3_sports'
    elif 'pets' in referrer:
        target_route = 'lab2_3_pets'
    else:
        target_route = 'lab2_3_music'

    resp = redirect(url_for(target_route))
    resp.set_cookie('Admin', '', expires=0)
    resp.set_cookie('session', '', expires=0)
    return resp

@app.route('/lab2/3/admin', methods=['GET', 'POST'])
def lab2_3_admin():
    # Check cookie
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        db = get_db()
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        
        # Handle user deletion (POST request simulation)
        flag = None
        if request.method == 'POST':
            flag = "FLAG{cookie_manipulation_is_sweet}"
            users = [] # Clear users to simulate deletion
            
        return render_template('lab2/sub3_admin.html', users=users, flag=flag)
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

# LAB 2.4 Variation B: JewelryStore (Parameter Tampering)
@app.route('/lab2/4b')
def lab2_4b():
    db = get_db()
    products = db.execute('SELECT * FROM products WHERE description LIKE "%necklace%" OR description LIKE "%watch%" OR id > 10 LIMIT 6').fetchall()
    return render_template('lab2/sub4_b.html', products=products)

@app.route('/lab2/4b/login', methods=['POST'])
def lab2_4b_login():
    username = request.form.get('username')
    password = request.form.get('password')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    if user:
        # VULNERABILITY: IDOR via 'user' parameter
        return redirect(url_for('lab2_4b_account', user=user['username']))
    return redirect(url_for('lab2_4b', login_error="Invalid Credentials"))

@app.route('/lab2/4b/account')
def lab2_4b_account():
    username_param = request.args.get('user')
    if not username_param: return redirect(url_for('lab2_4b'))
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
    if not user: return "User not found", 404
    
    if user['role'] == 'admin':
        return render_template('lab2/sub4_b_admin.html', account=user, flag="FLAG{jewelry_tampering_gold}")
    return render_template('lab2/sub4_b_account.html', account=user)

# LAB 2.4 Variation C: ElectroMart (Parameter Tampering)
@app.route('/lab2/4c')
def lab2_4c():
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab2/sub4_c.html', products=products)

@app.route('/lab2/4c/login', methods=['POST'])
def lab2_4c_login():
    username = request.form.get('username')
    password = request.form.get('password')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    if user:
        # VULNERABILITY: IDOR via 'username' parameter
        return redirect(url_for('lab2_4c_account', username=user['username']))
    return redirect(url_for('lab2_4c', login_error="Invalid Credentials"))

@app.route('/lab2/4c/account')
def lab2_4c_account():
    username_param = request.args.get('username')
    if not username_param: return redirect(url_for('lab2_4c'))
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
    if not user: return "User not found", 404
    
    if user['role'] == 'admin':
        return render_template('lab2/sub4_c_admin.html', account=user, flag="FLAG{electro_tampering_volt}")
    return render_template('lab2/sub4_c_account.html', account=user)


# LAB 2.5: Password Disclosure via IDOR
@app.route('/lab2/5')
def lab2_5():
    # Main store page for Lab 2.5
    error = request.args.get('login_error')
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('lab2/sub5.html', products=products, error=error)

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

    # Generate a random password for the admin if accessed
    # In a real app, this would be in the DB, but for the lab we simulate it
    # to ensure it's different every time and requires checking the vulnerability
    if username_param == 'admin':
        # Generate random password
        chars = string.ascii_letters + string.digits + "!@#$%"
        random_password = ''.join(random.choice(chars) for _ in range(12))
        
        # Create a mock user object with the random password
        user = {
            'username': 'admin',
            'password': random_password, # The secret!
            'email': 'admin@shophub.com',
            'role': 'admin',
            'full_name': 'System Administrator'
        }
        flag = f"FLAG{{shophub_admin_password_{random_password}}}"
    else:
        # Fetch regular user data/mock data
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
        flag = None
        
        if not user:
             return "User not found", 404

    # VULNERABILITY: Password is exposed in the template (hidden in HTML comment or hidden input)
    return render_template('lab2/sub5_profile.html', 
                         user=user, 
                         flag=flag)

@app.route('/lab2/5/logout')
def lab2_5_logout():
    return redirect(url_for('lab2_5'))

# Variation B: CloudMart (Same vuln, different theme)
@app.route('/lab2/5b')
def lab2_5b():
    error = request.args.get('login_error')
    return render_template('lab2/sub5_b.html', error=error)

@app.route('/lab2/5b/login', methods=['POST'])
def lab2_5b_login():
    username = request.form.get('username')
    password = request.form.get('password')
    # Use mock check for variation
    if username == "guest" and password == "guest123":
        return redirect(url_for('lab2_5b_profile', username=username))
    return redirect(url_for('lab2_5b', login_error="Invalid Credentials"))

@app.route('/lab2/5b/profile')
def lab2_5b_profile():
    import random
    import string
    
    # VULNERABILITY: IDOR via 'username' parameter
    username_param = request.args.get('username')
    
    if not username_param:
        return redirect(url_for('lab2_5b'))

    if username_param == 'root':
        # Generate random password for the challenge
        chars = string.ascii_letters + string.digits
        random_password = ''.join(random.choice(chars) for _ in range(12))
        
        user = {
            'username': 'root',
            'password': random_password,
            'email': 'infrastructure@cloudmart.io',
            'role': 'super_admin',
            'full_name': 'Cloud Infrastructure Root'
        }
        flag = f"FLAG{{cloudmart_root_access_{random_password}}}"
    else:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
        flag = None
        if not user:
             return "User not found", 404

    return render_template('lab2/sub5_b_profile.html', user=user, flag=flag)

# Variation C: DataVault
@app.route('/lab2/5c')
def lab2_5c():
    error = request.args.get('login_error')
    return render_template('lab2/sub5_c.html', error=error)

@app.route('/lab2/5c/login', methods=['POST'])
def lab2_5c_login():
    username = request.form.get('username')
    password = request.form.get('password')
    # Use mock check for variation
    if username == "viewer" and password == "view123":
        return redirect(url_for('lab2_5c_profile', username=username))
    return redirect(url_for('lab2_5c', login_error="Invalid Credentials"))

@app.route('/lab2/5c/profile')
def lab2_5c_profile():
    # VULNERABILITY: IDOR via 'username' parameter
    username_param = request.args.get('username')
    
    if not username_param:
        return redirect(url_for('lab2_5c'))

    if username_param == 'owner':
        # Generate random password for the challenge
        chars = string.ascii_letters + string.digits + "_-*"
        random_password = ''.join(random.choice(chars) for _ in range(12))
        
        user = {
            'username': 'owner',
            'password': random_password,
            'email': 'security@datavault_internal.net',
            'role': 'system_owner',
            'full_name': 'DataVault System Owner'
        }
        flag = f"FLAG{{datavault_owner_override_{random_password}}}"
    else:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username_param,)).fetchone()
        flag = None
        if not user:
             return "User not found", 404

    # VULNERABILITY: Password exposed in template comment
    return render_template('lab2/sub5_c_profile.html', user=user, flag=flag)

# End Lab 2


# -------------------------
# LAB 3: Authentication
# -------------------------
@app.route('/lab3')
def lab3():
    return render_template('lab3/index.html')

# LAB 3.1: Brute Force Attack Menu
@app.route('/lab3/1/menu')
def lab3_1_menu():
    return render_template('lab3/menu.html')

# LAB 3.1.1: Brute Force Attack - SecureVault
@app.route('/lab3/1')
def lab3_1():
    import random # Local import to ensure it's available
    
    # 3. Pick Random Credentials from Wordlists
    usernames_file = os.path.join('data', 'wordlists', 'usernames.txt')
    passwords_file = os.path.join('data', 'wordlists', 'passwords.txt')
    
    with open(usernames_file, 'r') as f:
        usernames = [line.strip() for line in f if line.strip()]
    with open(passwords_file, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]

    target_user = random.choice(usernames)
    target_password = random.choice(passwords)
    
    # 4. Store in Session (So we can verify later)
    session['lab3_1_target_user'] = target_user
    session['lab3_1_target_pass'] = target_password
    
    # 5. Log for learning/debugging
    print(f"\n[LAB 3.1 START] Integrity Check:")
    print(f" -> Target User: {target_user}")
    print(f" -> Target Pass: {target_password}")
    print(f"----------------------------------------\n")
    
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1.html', products=products)


@app.route('/lab3/1/login', methods=['POST'])
def lab3_1_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_target_user')
    target_pass = session.get('lab3_1_target_pass')
    
    # Scenario 1: Correct Credentials
    if username == target_user and password == target_pass:
        session['lab3_1_logged_in'] = True
        session['lab3_1_username'] = username
        # SUCCESS: Redirect (Status 302) - Easy to spot in Burp
        return redirect(url_for('lab3_1_admin'))

    # Scenario 2: Correct Username, Wrong Password
    if username == target_user:
        # VULNERABILITY: User Enumeration
        # Different error message allows attacker to know user exists
        error_msg = "Incorrect password."
        # Optional: Add padding if you want length difference to be huge
        # error_msg += " " * 100 
        
        db = get_db()
        products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
        return render_template('lab3/sub1.html', products=products, error=error_msg), 200

    # Scenario 3: Invalid Username
    # Default generic error message
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1.html', products=products, error="Invalid username or password"), 200

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
                         variant='1',
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
                         variant='1',
                         flag="FLAG{brute_force_authentication_master}")

# LAB 3.1.2: Brute Force Attack - Luxury Variant
@app.route('/lab3/1/2')
def lab3_1_2():
    import random
    
    usernames_file = os.path.join('data', 'wordlists', 'usernames.txt')
    passwords_file = os.path.join('data', 'wordlists', 'passwords.txt')
    
    with open(usernames_file, 'r') as f:
        usernames = [line.strip() for line in f if line.strip()]
    with open(passwords_file, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]

    target_user = random.choice(usernames)
    target_password = random.choice(passwords)
    
    session['lab3_1_2_target_user'] = target_user
    session['lab3_1_2_target_pass'] = target_password
    
    print(f"\n[LAB 3.1.2 START] Integrity Check:")
    print(f" -> Target User: {target_user}")
    print(f" -> Target Pass: {target_password}")
    print(f"----------------------------------------\n")
    
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1_b.html', products=products)

@app.route('/lab3/1/2/login', methods=['POST'])
def lab3_1_2_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_2_target_user')
    target_pass = session.get('lab3_1_2_target_pass')
    
    if username == target_user and password == target_pass:
        session['lab3_1_2_logged_in'] = True
        session['lab3_1_2_username'] = username
        return redirect(url_for('lab3_1_2_admin'))

    if username == target_user:
        error_msg = "Incorrect password."
        db = get_db()
        products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
        return render_template('lab3/sub1_b.html', products=products, error=error_msg), 200

    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1_b.html', products=products, error="Invalid username or password"), 200

@app.route('/lab3/1/2/admin')
def lab3_1_2_admin():
    if not session.get('lab3_1_2_logged_in'):
        return redirect(url_for('lab3_1_2'))
    
    db = get_db()
    users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
    admin_user = session.get('lab3_1_2_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         variant='2',
                         flag=None)

@app.route('/lab3/1/2/admin/delete', methods=['POST'])
def lab3_1_2_delete_user():
    if not session.get('lab3_1_2_logged_in'):
        return redirect(url_for('lab3_1_2'))
    
    admin_user = session.get('lab3_1_2_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         variant='2',
                         flag="FLAG{brute_force_premium_variant}")

@app.route('/lab3/1/2/logout')
def lab3_1_2_logout():
    session.pop('lab3_1_2_logged_in', None)
    session.pop('lab3_1_2_username', None)
    return redirect(url_for('lab3_1_2'))

# LAB 3.1.3: Brute Force Attack - Corporate Variant
@app.route('/lab3/1/3')
def lab3_1_3():
    import random
    
    usernames_file = os.path.join('data', 'wordlists', 'usernames.txt')
    passwords_file = os.path.join('data', 'wordlists', 'passwords.txt')
    
    with open(usernames_file, 'r') as f:
        usernames = [line.strip() for line in f if line.strip()]
    with open(passwords_file, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]

    target_user = random.choice(usernames)
    target_password = random.choice(passwords)
    
    session['lab3_1_3_target_user'] = target_user
    session['lab3_1_3_target_pass'] = target_password
    
    print(f"\n[LAB 3.1.3 START] Integrity Check:")
    print(f" -> Target User: {target_user}")
    print(f" -> Target Pass: {target_password}")
    print(f"----------------------------------------\n")
    
    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1_c.html', products=products)

@app.route('/lab3/1/3/login', methods=['POST'])
def lab3_1_3_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_3_target_user')
    target_pass = session.get('lab3_1_3_target_pass')
    
    if username == target_user and password == target_pass:
        session['lab3_1_3_logged_in'] = True
        session['lab3_1_3_username'] = username
        return redirect(url_for('lab3_1_3_admin'))

    if username == target_user:
        error_msg = "Incorrect password."
        db = get_db()
        products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
        return render_template('lab3/sub1_c.html', products=products, error=error_msg), 200

    db = get_db()
    products = db.execute('SELECT * FROM products LIMIT 6').fetchall()
    return render_template('lab3/sub1_c.html', products=products, error="Invalid username or password"), 200

@app.route('/lab3/1/3/admin')
def lab3_1_3_admin():
    if not session.get('lab3_1_3_logged_in'):
        return redirect(url_for('lab3_1_3'))
    
    db = get_db()
    users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
    admin_user = session.get('lab3_1_3_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         variant='3',
                         flag=None)

@app.route('/lab3/1/3/admin/delete', methods=['POST'])
def lab3_1_3_delete_user():
    if not session.get('lab3_1_3_logged_in'):
        return redirect(url_for('lab3_1_3'))
    
    admin_user = session.get('lab3_1_3_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         variant='3',
                         flag="FLAG{brute_force_corporate_variant}")

@app.route('/lab3/1/3/logout')
def lab3_1_3_logout():
    session.pop('lab3_1_3_logged_in', None)
    session.pop('lab3_1_3_username', None)
    return redirect(url_for('lab3_1_3'))

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
    return render_template('lab4/index.html')

# Lab 4.1: Basic SSRF against the local server (Variation A: Retail)
@app.route('/lab4/1')
def lab4_1():
    # Mock data with images instead of DB
    products = [
        {'id': 1, 'name': 'Vulnerable T-Shirt', 'description': 'Limited edition vulnerable item.', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Insecure Hoodie', 'description': 'Keeps you warm, keeps your data exposed.', 'price': 49.99, 'image': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'SQLi Mug', 'description': 'Select * from drinks.', 'price': 15.00, 'image': 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=600&q=80'},
        {'id': 4, 'name': 'Smart Watch X', 'description': 'Tracks your location... everywhere.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'},
        {'id': 5, 'name': 'Urban Backpack', 'description': 'Fits all your stolen secrets.', 'price': 89.50, 'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80'},
        {'id': 6, 'name': 'Running Sneakers', 'description': 'Run away from security audits.', 'price': 120.00, 'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80'},
        {'id': 7, 'name': 'Aviator Sunglasses', 'description': 'Shade your eyes from the glare of pwned servers.', 'price': 145.00, 'image': 'https://images.unsplash.com/photo-1572635196237-14b3f281503f?auto=format&fit=crop&w=600&q=80'},
        {'id': 8, 'name': 'Designer Cap', 'description': 'Hat tip to the white hats.', 'price': 35.00, 'image': 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab4/sub1.html', products=products)

@app.route('/lab4/1/product/<int:product_id>')
def lab4_1_product(product_id):
    # Re-define products here for the detail view since we removed DB
    products = [
        {'id': 1, 'name': 'Vulnerable T-Shirt', 'description': 'Limited edition vulnerable item.', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Insecure Hoodie', 'description': 'Keeps you warm, keeps your data exposed.', 'price': 49.99, 'image': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'SQLi Mug', 'description': 'Select * from drinks.', 'price': 15.00, 'image': 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=600&q=80'},
        {'id': 4, 'name': 'Smart Watch X', 'description': 'Tracks your location... everywhere.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'},
        {'id': 5, 'name': 'Urban Backpack', 'description': 'Fits all your stolen secrets.', 'price': 89.50, 'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80'},
        {'id': 6, 'name': 'Running Sneakers', 'description': 'Run away from security audits.', 'price': 120.00, 'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80'},
        {'id': 7, 'name': 'Aviator Sunglasses', 'description': 'Shade your eyes from the glare of pwned servers.', 'price': 145.00, 'image': 'https://images.unsplash.com/photo-1572635196237-14b3f281503f?auto=format&fit=crop&w=600&q=80'},
        {'id': 8, 'name': 'Designer Cap', 'description': 'Hat tip to the white hats.', 'price': 35.00, 'image': 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=600&q=80'}
    ]
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Product not found", 404
    return render_template('lab4/sub1_product.html', product=product)

@app.route('/lab4/1/stock', methods=['POST'])
def lab4_1_stock():
    stock_api = request.form.get('stockApi')
    if not stock_api:
        return "Missing stockApi parameter", 400
    
    # VULNERABILITY: SSRF
    import requests
    try:
        # We use a trick to allow requests to localhost/127.0.0.1 if it's targeted
        # In a real scenario, this would just be requests.get(stock_api)
        # But we need to make sure 'localhost' refers to THIS app instance.
        # If the URL is http://localhost/admin, we internally redirect or 
        # just use requests if the app is actually running on 80.
        # Since we are on port 5000, we should expect http://localhost:5000/admin 
        # or simulate it.
        
        # Helper to handle internal routing for simulation
        if "localhost" in stock_api or "127.0.0.1" in stock_api:
            # Re-route to our own server if port is missing or 80
            if ":5000" not in stock_api:
                stock_api = stock_api.replace("localhost", "localhost:5000").replace("127.0.0.1", "127.0.0.1:5000")
        
        resp = requests.get(stock_api, timeout=5)
        return resp.text
    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500

# Lab 4.1 Menu
@app.route('/lab4/1/menu')
def lab4_1_menu():
    return render_template('lab4/sub1_menu.html')

# Update Lab 4.1 (Variation A) to use new template if needed, or just keep as is.
# The user asked to "Restructure all follow Lab2 Structure".
# In Lab 2, /lab2/1 is Variation A. We already have this.

# Helper for Lab 4.1c (Logistics)
def get_lab4_1c_products():
    return [
        {'id': 201, 'name': 'Container 40ft High Cube', 'description': 'Refrigerated transport unit. Origin: Shanghai.', 'price': 3500, 'image': 'https://images.unsplash.com/photo-1494412651409-ae1c4027d164?auto=format&fit=crop&w=600&q=80'},
        {'id': 202, 'name': 'IoT Sensor Array', 'description': 'Real-time GPS and humidity tracking module.', 'price': 450, 'image': 'https://images.unsplash.com/photo-1566576912906-253c723f03b5?auto=format&fit=crop&w=600&q=80'},
        {'id': 203, 'name': 'Automated Forklift Drone', 'description': 'Warehouse autonomous vehicle.', 'price': 15000, 'image': 'https://images.unsplash.com/photo-1506543730537-8051c72f778d?auto=format&fit=crop&w=600&q=80'},
        {'id': 204, 'name': 'Deep Sea Buoy', 'description': 'Weather monitoring station.', 'price': 8000, 'image': 'https://images.unsplash.com/photo-1518114674381-893bd558a27d?auto=format&fit=crop&w=600&q=80'},
        {'id': 205, 'name': 'Automated Warehouse System', 'description': 'Full stack inventory robotics.', 'price': 45000, 'image': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=600&q=80'},
        {'id': 206, 'name': 'Cargo Ship Transport', 'description': 'Heavy lift vessel capacity slot.', 'price': 12000, 'image': 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=600&q=80'},
        {'id': 207, 'name': 'Logistics Truck Fleet', 'description': 'Last mile delivery unit.', 'price': 85000, 'image': 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=600&q=80'},
        {'id': 208, 'name': 'Industrial Control Panel', 'description': 'SCADA interface for facility management.', 'price': 2500, 'image': 'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=600&q=80'}
    ]

# Lab 4.1 Variation C: Logistics
@app.route('/lab4/1/c')
def lab4_1c():
    products = get_lab4_1c_products()
    return render_template('lab4/sub1_c.html', products=products)

@app.route('/lab4/1/c/product/<int:product_id>')
def lab4_1c_product(product_id):
    products = get_lab4_1c_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Product not found", 404
    return render_template('lab4/sub1_c_product.html', product=product)

# Helper for Lab 4.1b products
def get_lab4_1b_products():
    return [
        {'id': 101, 'name': 'Quantum Blade Server X1', 'description': 'High-density compute node with 128 cores.', 'price': 15000, 'image': 'https://images.unsplash.com/photo-1558494949-ef526b01201b?auto=format&fit=crop&w=600&q=80'},
        {'id': 102, 'name': 'Nebula Storage Array', 'description': 'Petabyte-scale solid state storage.', 'price': 45000, 'image': 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=600&q=80'},
        {'id': 103, 'name': 'Vortex Network Switch', 'description': '400Gbps ultra-low latency fabric.', 'price': 8500, 'badge': 'High Perf', 'image': 'https://images.unsplash.com/photo-1544197150-b99a580bbc7c?auto=format&fit=crop&w=600&q=80'},
        {'id': 104, 'name': 'AI Training Cluster', 'description': 'Dedicated GPU rack for ML workloads.', 'price': 120000, 'image': 'https://images.unsplash.com/photo-1551703652-8564730a845b?auto=format&fit=crop&w=600&q=80'},
        {'id': 105, 'name': 'Secure Gateway Appliance', 'description': 'Military-grade firewall and VPN concentrator.', 'price': 12000, 'badge': 'Critical', 'image': 'https://images.unsplash.com/photo-1563770095128-42fa6112a83e?auto=format&fit=crop&w=600&q=80'},
        {'id': 106, 'name': 'CoolCore Liquid Loop', 'description': 'Active cooling system for high-TDP racks.', 'price': 5500, 'image': 'https://images.unsplash.com/photo-1535295972055-1c762f4483e5?auto=format&fit=crop&w=600&q=80'},
        {'id': 107, 'name': 'Biometric Access Panel', 'description': 'Retina scan entry system.', 'price': 2500, 'image': 'https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?auto=format&fit=crop&w=600&q=80'},
        {'id': 108, 'name': 'Encrypted Data Tape', 'description': 'Cold storage for long-term retention.', 'price': 150, 'image': 'https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?auto=format&fit=crop&w=600&q=80'}
    ]

# Lab 4.1 Variant B: Cloud Infrastructure Marketplace
@app.route('/lab4/1/b')
def lab4_1b():
    products = get_lab4_1b_products()
    return render_template('lab4/sub1_b.html', products=products)

@app.route('/lab4/1/b/product/<int:product_id>')
def lab4_1b_product(product_id):
    products = get_lab4_1b_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Product not found", 404
    return render_template('lab4/sub1_b_product.html', product=product)

# Dummy Stock Check API for realism
@app.route('/stock/check')
def stock_check_api():
    product_id = request.args.get('id')
    import random
    return f"Success: {random.randint(10, 100)} units available for Item-{product_id}."

# Simulated External Admin for 4.1
@app.route('/admin')
def admin_panel():
    # Simulate restriction: Only accessible from loopback
    # In a real SSRF lab, the admin panel is blocked by a WAF/Firewall 
    # for external IPs but allowed for internal ones.
    if request.remote_addr != '127.0.0.1' and '127.0.0.1' not in request.host:
        return "<h1>403 Forbidden</h1><p>Admin interface only accessible from local network.</p>", 403
    
    return render_template('lab4/admin_panel.html', user_to_delete="carlos")

@app.route('/admin/delete')
def admin_delete_user():
    if request.remote_addr != '127.0.0.1' and '127.0.0.1' not in request.host:
        return "403 Forbidden", 403
        
    username = request.args.get('username')
    if username == "carlos":
        return f"<h1>Success</h1><p>User {username} deleted successfully!</p><p>FLAG{{ssrf_local_admin_pwned}}</p>"
    return f"User {username} not found."




# -------------------------
# LAB 5: File Upload
# -------------------------

@app.route('/lab5')
def lab5():
    return render_template('lab5/index.html')

import uuid

# LAB 5.1: Remote Code Execution via Web Shell Upload
# Menu Selection
@app.route('/lab5/1/menu')
def lab5_1_menu():
    return render_template('lab5/sub1_menu.html')

@app.route('/lab5/1')
def lab5_1():
    # Render the E-commerce Shop Home Page
    products = [
        {'name': 'SecureDrive SSD', 'description': 'Encrypted 2TB storage for ultimate privacy.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Privacy Shield', 'description': 'Anti-spam filter hardware appliance.', 'price': 149.50, 'image': 'https://images.unsplash.com/photo-1563770095128-42fa6112a83e?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Developer Laptop', 'description': 'Optimized for heavy compiling workloads.', 'price': 1299.00, 'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca4?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Wireless Headers', 'description': 'Noise-canceling over-ear headphones.', 'price': 299.00, 'image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Mechanical Keyboard', 'description': 'RGB backlit clicky switches.', 'price': 89.99, 'image': 'https://images.unsplash.com/photo-1587829741301-dc798b91a05c?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Smart Watch', 'description': 'Health tracking and notifications.', 'price': 150.00, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab5/sub1_home.html', products=products)

@app.route('/lab5/1/login', methods=['GET', 'POST'])
def lab5_1_login():
    if request.method == 'GET':
        if 'lab5_1_user' in session:
            return redirect(url_for('lab5_1_account'))
        return render_template('lab5/sub1_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Wiener:peter (Standard PortSwigger user)
    if username == 'wiener' and password == 'peter':
        session['lab5_1_user'] = username
        # Generate a unique session ID for file isolation if not exists
        if 'lab5_1_uid' not in session:
            session['lab5_1_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_account'))
    else:
        return render_template('lab5/sub1_login.html', error='Invalid credentials')

@app.route('/lab5/1/account')
def lab5_1_account():
    username = session.get('lab5_1_user')
    if not username:
        return redirect(url_for('lab5_1_login'))
    
    # Check if user has an avatar uploaded in their specific directory
    avatar = session.get('lab5_1_avatar') # This now stores 'uid/filename' or just filename? 
    # Let's store RELATIVE path 'uid/filename' in the session for simplicity?
    # Or keep just filename and construct path. Storing relative path is safer.
    
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub1_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/1/upload', methods=['POST'])
def lab5_1_upload():
    if 'lab5_1_user' not in session:
        return redirect(url_for('lab5_1_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_1_account'))
    
    # Ensure UID exists
    if 'lab5_1_uid' not in session:
        session['lab5_1_uid'] = str(uuid.uuid4())
    
    user_uid = session['lab5_1_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_1_account'))
    
    # VULNERABILITY: No validation of file extension or content
    filename = file.filename
    
    # Create User Specific Directory
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file.save(os.path.join(upload_dir, filename))
    
    # Update session with relative path
    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_avatar'] = relative_path
    
    return render_template('lab5/sub1_account.html', 
                         username=session['lab5_1_user'], 
                         avatar=f"/files/avatars/{relative_path}",
                         message=f"Avatar {filename} uploaded successfully!")

@app.route('/lab5/1/logout')
@app.route('/lab5/1/logout')
def lab5_1_logout():
    # Cleanup: Delete user files on logout
    uid = session.get('lab5_1_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                print(f"Error cleaning up directory {user_upload_dir}: {e}")

    session.pop('lab5_1_user', None)
    session.pop('lab5_1_avatar', None)
    session.pop('lab5_1_uid', None)
    return redirect(url_for('lab5_1_login'))

# The Vulnerable File Serving Route
@app.route('/files/avatars/<path:filename>')
def lab5_1_file(filename):
    # Filename here will be "uid/actual_filename.ext" because of <path:filename>
    base_dir = os.getcwd()
    # Base upload directory
    upload_base_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars')
    
    # Securely join paths? No, we want to allow access to the file.
    # But let's construct the full path.
    file_path = os.path.join(upload_base_dir, filename)
    
    # Security check: Ensure we don't traverse up from 'avatars' directory
    # Although path traversal is another vulnerability potential, for this specific lab focus on File Upload RCE,
    # let's keep it scoped to the avatars folder structure essentially.
    if not os.path.abspath(file_path).startswith(os.path.abspath(upload_base_dir)):
         return "Access Denied", 403

    if not os.path.exists(file_path):
        return "File not found", 404
        
    # SIMULATION: Check if it's a PHP file and "execute" it
    if filename.lower().endswith('.php'):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for the specific payload requested in the lab
            # Payload: <?php echo file_get_contents('/home/carlos/secret'); ?>
            if "file_get_contents('/home/carlos/secret')" in content:
                # Return the secret!
                return "FLAG{file_upload_code_execution_php}"
            
            # Simulated generic echo
            if "echo" in content:
                import re
                matches = re.findall(r"echo\s+['\"](.*?)['\"]", content)
                if matches:
                    return "".join(matches)
                    
            # Fallback: Just return the content as text/plain (source code disclosure)
            return content, 200, {'Content-Type': 'text/plain'}
            
        except Exception as e:
            return str(e), 500
            
    # Serve normal images
    # We need to serve from the specific directory.
    # send_from_directory expects a directory and a filename.
    # Since 'filename' contains 'uid/image.png', we can pass base dir and the path.
    return send_from_directory(upload_base_dir, filename)


# -------------------------
# LAB 5.2: Content-Type Bypass
# -------------------------
@app.route('/lab5/2/menu')
def lab5_2_menu():
    return render_template('lab5/sub2_menu.html')

@app.route('/lab5/2')
def lab5_2():
    # Similar products to Lab 5.1 but distinct enough
    products = [
         {'name': 'Encrypted Drive', 'description': 'Secure data storage.', 'price': 89.99, 'image': 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=600&q=80'},
         {'name': 'Privacy Filter', 'description': 'Screen protector.', 'price': 29.50, 'image': 'https://images.unsplash.com/photo-1563770095128-42fa6112a83e?auto=format&fit=crop&w=600&q=80'},
         {'name': 'Dev Station', 'description': 'Workstation laptop.', 'price': 1499.00, 'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca4?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab5/sub2_home.html', products=products)

@app.route('/lab5/2/login', methods=['GET', 'POST'])
def lab5_2_login():
    if request.method == 'GET':
        if 'lab5_2_user' in session:
            return redirect(url_for('lab5_2_account'))
        return render_template('lab5/sub2_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_user'] = username
        if 'lab5_2_uid' not in session:
            session['lab5_2_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_account'))
    else:
        return render_template('lab5/sub2_login.html', error='Invalid credentials')

@app.route('/lab5/2/account')
def lab5_2_account():
    username = session.get('lab5_2_user')
    if not username:
        return redirect(url_for('lab5_2_login'))
    
    avatar = session.get('lab5_2_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub2_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/2/upload', methods=['POST'])
def lab5_2_upload():
    if 'lab5_2_user' not in session:
        return redirect(url_for('lab5_2_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_2_account'))
    
    if 'lab5_2_uid' not in session:
        session['lab5_2_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_2_account'))
    
    # VULNERABILITY: Content-Type Bypass
    # We check the Content-Type header, but not the actual file content or extension
    if file.content_type not in ['image/jpeg', 'image/png']:
        return render_template('lab5/sub2_error.html', 
                             username=session['lab5_2_user'], 
                             error=f"Error: File type {file.content_type} is not allowed. Only image/jpeg and image/png are accepted in this secure environment.")
    
    # If the attacker changes Content-Type to image/jpeg, we accept it, even if filename is exploit.php
    filename = file.filename
    
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file.save(os.path.join(upload_dir, filename))
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_avatar'] = relative_path
    
    return render_template('lab5/sub2_account.html', 
                         username=session['lab5_2_user'], 
                         avatar=f"/files/avatars/{relative_path}",
                         message=f"Avatar {filename} uploaded successfully!")

@app.route('/lab5/2/logout')
def lab5_2_logout():
    # Cleanup
    uid = session.get('lab5_2_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass

    session.pop('lab5_2_user', None)
    session.pop('lab5_2_avatar', None)
    session.pop('lab5_2_uid', None)
    return redirect(url_for('lab5_2_login'))

# -------------------------
# LAB 5.2 VARIATION B: Global Logistics (Orange Theme)
# -------------------------
@app.route('/lab5/2/b')
def lab5_2_b():
    shipments = [
        {'id': 'SHP-9021', 'status': 'In Transit', 'eta': '2 Days'},
        {'id': 'SHP-8820', 'status': 'Delivered', 'eta': 'Did not arrive'},
        {'id': 'SHP-1029', 'status': 'Processing', 'eta': 'Pending'}
    ]
    return render_template('lab5/sub2_b_home.html', shipments=shipments)

@app.route('/lab5/2/b/login', methods=['GET', 'POST'])
def lab5_2_b_login():
    if request.method == 'GET':
        if 'lab5_2_b_user' in session:
            return redirect(url_for('lab5_2_b_account'))
        return render_template('lab5/sub2_b_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_b_user'] = username
        if 'lab5_2_b_uid' not in session:
            session['lab5_2_b_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_b_account'))
    else:
        return render_template('lab5/sub2_b_login.html', error='Invalid credentials')

@app.route('/lab5/2/b/account')
def lab5_2_b_account():
    username = session.get('lab5_2_b_user')
    if not username:
        return redirect(url_for('lab5_2_b_login'))
    
    avatar = session.get('lab5_2_b_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub2_b_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/2/b/upload', methods=['POST'])
def lab5_2_b_upload():
    if 'lab5_2_b_user' not in session:
        return redirect(url_for('lab5_2_b_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_2_b_account'))
    
    if 'lab5_2_b_uid' not in session:
        session['lab5_2_b_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_b_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_2_b_account'))
    
    # VULNERABILITY (Same as 5.2): Check Content-Type only
    if file.content_type not in ['image/jpeg', 'image/png']:
        return render_template('lab5/sub2_error.html', 
                             username=session['lab5_2_b_user'], 
                             error=f"ERROR P-902: Invalid format {file.content_type}. Driver app only accepts camera images (JPEG/PNG).")
    
    filename = file.filename
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file.save(os.path.join(upload_dir, filename))
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_b_avatar'] = relative_path
    
    return render_template('lab5/sub2_b_account.html', username=session['lab5_2_b_user'], avatar=f"/files/avatars/{relative_path}", message=f"Signature {filename} updated!")

@app.route('/lab5/2/b/logout')
def lab5_2_b_logout():
    # Cleanup
    uid = session.get('lab5_2_b_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass
    session.pop('lab5_2_b_user', None)
    session.pop('lab5_2_b_avatar', None)
    session.pop('lab5_2_b_uid', None)
    return redirect(url_for('lab5_2_b_login'))

# -------------------------
# LAB 5.2 VARIATION C: SecureBank (Purple Theme)
# -------------------------
@app.route('/lab5/2/c')
def lab5_2_c():
    return render_template('lab5/sub2_c_home.html')

@app.route('/lab5/2/c/login', methods=['GET', 'POST'])
def lab5_2_c_login():
    if request.method == 'GET':
        if 'lab5_2_c_user' in session:
            return redirect(url_for('lab5_2_c_account'))
        return render_template('lab5/sub2_c_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_c_user'] = username
        if 'lab5_2_c_uid' not in session:
            session['lab5_2_c_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_c_account'))
    else:
        return render_template('lab5/sub2_c_login.html', error='Invalid credentials')

@app.route('/lab5/2/c/account')
def lab5_2_c_account():
    username = session.get('lab5_2_c_user')
    if not username:
        return redirect(url_for('lab5_2_c_login'))
    
    avatar = session.get('lab5_2_c_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub2_c_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/2/c/upload', methods=['POST'])
def lab5_2_c_upload():
    if 'lab5_2_c_user' not in session:
        return redirect(url_for('lab5_2_c_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_2_c_account'))
    
    if 'lab5_2_c_uid' not in session:
        session['lab5_2_c_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_c_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_2_c_account'))
    
    # VULNERABILITY (Same as 5.2)
    if file.content_type not in ['image/jpeg', 'image/png']:
         return render_template('lab5/sub2_error.html', 
                             username=session['lab5_2_c_user'], 
                             error=f"SECURITY ALERT: The format {file.content_type} is not compliant with banking regulations. Upload only JPEG/PNG scans.")
    
    filename = file.filename
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file.save(os.path.join(upload_dir, filename))
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_c_avatar'] = relative_path
    
    return render_template('lab5/sub2_c_account.html', username=session['lab5_2_c_user'], avatar=f"/files/avatars/{relative_path}", message=f"Document {filename} submitted for verification!")

@app.route('/lab5/2/c/logout')
def lab5_2_c_logout():
    # Cleanup
    uid = session.get('lab5_2_c_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass
    session.pop('lab5_2_c_user', None)
    session.pop('lab5_2_c_avatar', None)
    session.pop('lab5_2_c_uid', None)
    return redirect(url_for('lab5_2_c_login'))


# -------------------------
# LAB 5.1 VARIATION B: PixelArt (NFT/Crypto Theme)
# -------------------------
@app.route('/lab5/1/b')
def lab5_1_b():
    gallery = [
        {'title': 'Cyber Punk #2049', 'artist': 'NeonDreamer', 'price': 0.5, 'image': 'https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Glitch Face', 'artist': 'V0ID', 'price': 2.1, 'image': 'https://images.unsplash.com/photo-1614812513172-567d2fe96a75?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Retro Wave', 'artist': 'SynthBoy', 'price': 0.8, 'image': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Digital Ape', 'artist': 'CryptoKing', 'price': 12.5, 'image': 'https://images.unsplash.com/photo-1622547748225-3fc4abd2cca0?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Abstract 8-bit', 'artist': 'PixelMage', 'price': 0.05, 'image': 'https://images.unsplash.com/photo-1633103453303-34e2c0e6205e?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Metaverse City', 'artist': 'FutureArchitect', 'price': 4.2, 'image': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab5/sub1_b_home.html', gallery=gallery)

@app.route('/lab5/1/b/login', methods=['GET', 'POST'])
def lab5_1_b_login():
    if request.method == 'GET':
        if 'lab5_1_b_user' in session:
            return redirect(url_for('lab5_1_b_account'))
        return render_template('lab5/sub1_b_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_1_b_user'] = username
        if 'lab5_1_b_uid' not in session:
            session['lab5_1_b_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_b_account'))
    else:
        return render_template('lab5/sub1_b_login.html', error='Invalid credentials')

@app.route('/lab5/1/b/account')
def lab5_1_b_account():
    username = session.get('lab5_1_b_user')
    if not username:
        return redirect(url_for('lab5_1_b_login'))
    
    avatar = session.get('lab5_1_b_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub1_b_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/1/b/upload', methods=['POST'])
def lab5_1_b_upload():
    if 'lab5_1_b_user' not in session:
        return redirect(url_for('lab5_1_b_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_1_b_account'))
    
    if 'lab5_1_b_uid' not in session:
        session['lab5_1_b_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_1_b_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_1_b_account'))
    
    # VULNERABILITY
    filename = file.filename
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file.save(os.path.join(upload_dir, filename))
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_b_avatar'] = relative_path
    
    return render_template('lab5/sub1_b_account.html', username=session['lab5_1_b_user'], avatar=f"/files/avatars/{relative_path}", message=f"Artwork {filename} uploaded!")

@app.route('/lab5/1/b/logout')
def lab5_1_b_logout():
    # Cleanup
    uid = session.get('lab5_1_b_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass # Silent fail

    session.pop('lab5_1_b_user', None)
    session.pop('lab5_1_b_avatar', None)
    session.pop('lab5_1_b_uid', None)
    return redirect(url_for('lab5_1_b_login'))


# -------------------------
# LAB 5.1 VARIATION C: HireMinds (Job Portal Theme)
# -------------------------
@app.route('/lab5/1/c')
def lab5_1_c():
    jobs = [
        {'title': 'Senior React Developer', 'company': 'TechFlow', 'location': 'Remote', 'salary': '$120k', 'logo': 'https://ui-avatars.com/api/?name=TF&background=0D8ABC&color=fff'},
        {'title': 'DevOps Engineer', 'company': 'CloudScale', 'location': 'New York, USA', 'salary': '$150k', 'logo': 'https://ui-avatars.com/api/?name=CS&background=ff5722&color=fff'},
        {'title': 'UX Designer', 'company': 'CreativeBox', 'location': 'London, UK', 'salary': '£65k', 'logo': 'https://ui-avatars.com/api/?name=CB&background=673ab7&color=fff'},
        {'title': 'Product Manager', 'company': 'Innovate', 'location': 'Berlin, DE', 'salary': '€85k', 'logo': 'https://ui-avatars.com/api/?name=IN&background=4caf50&color=fff'},
        {'title': 'Data Scientist', 'company': 'DataMind', 'location': 'Toronto, CA', 'salary': '$135k', 'logo': 'https://ui-avatars.com/api/?name=DM&background=607d8b&color=fff'}
    ]
    return render_template('lab5/sub1_c_home.html', jobs=jobs)

@app.route('/lab5/1/c/login', methods=['GET', 'POST'])
def lab5_1_c_login():
    if request.method == 'GET':
        if 'lab5_1_c_user' in session:
            return redirect(url_for('lab5_1_c_account'))
        return render_template('lab5/sub1_c_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_1_c_user'] = username
        if 'lab5_1_c_uid' not in session:
            session['lab5_1_c_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_c_account'))
    else:
        return render_template('lab5/sub1_c_login.html', error='Invalid credentials')

@app.route('/lab5/1/c/account')
def lab5_1_c_account():
    username = session.get('lab5_1_c_user')
    if not username:
        return redirect(url_for('lab5_1_c_login'))
    
    avatar = session.get('lab5_1_c_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    
    return render_template('lab5/sub1_c_account.html', username=username, avatar=avatar_url)

@app.route('/lab5/1/c/upload', methods=['POST'])
def lab5_1_c_upload():
    if 'lab5_1_c_user' not in session:
        return redirect(url_for('lab5_1_c_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_1_c_account'))
    
    if 'lab5_1_c_uid' not in session:
        session['lab5_1_c_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_1_c_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_1_c_account'))
    
    # VULNERABILITY
    filename = file.filename
    base_dir = os.getcwd()
    upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file.save(os.path.join(upload_dir, filename))
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_c_avatar'] = relative_path
    
    return render_template('lab5/sub1_c_account.html', username=session['lab5_1_c_user'], avatar=f"/files/avatars/{relative_path}", message=f"Credential {filename} verified!")

@app.route('/lab5/1/c/logout')
def lab5_1_c_logout():
    # Cleanup
    uid = session.get('lab5_1_c_uid')
    if uid:
        import shutil
        base_dir = os.getcwd()
        user_upload_dir = os.path.join(base_dir, 'static', 'lab5', 'uploads', 'avatars', uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass

    session.pop('lab5_1_c_user', None)
    session.pop('lab5_1_c_avatar', None)
    session.pop('lab5_1_c_uid', None)
    return redirect(url_for('lab5_1_c_login'))


# -------------------------
# LAB 6: OS Command Injection
# -------------------------
@app.route('/lab6')
def lab6():
    return render_template('lab6/index.html')

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
@app.route('/lab7')
def lab7():
    return render_template('lab7/index.html')



# -------------------------
# LAB 8: Cross-Site Scripting (XSS)
# -------------------------

# Initial seed data for Lab 8.2 (Stored XSS)
# Initial seed data for Lab 8.2 (Stored XSS)
LAB8_COMMENTS = [
    {
        'author': 'System Admin', 
        'date': '2024-03-01', 
        'body': 'Welcome to the feedback board! Please identify any bugs you find. (Just kidding, keep it safe!)'
    },
    {
        'author': 'Hacker101', 
        'date': '2024-03-02', 
        'body': 'Check out this cool feature! <img src=x onerror=alert("Stored_XSS_Executed")>'
    },
    {
        'author': 'BugHunter99', 
        'date': '2024-03-02', 
        'body': 'Found a weird issue on the login page. Can we get a fix?'
    }
]

@app.route('/lab8')
def lab8():
    return render_template('lab8/index.html')

# Lab 8.1: Reflected XSS
@app.route('/lab8/1', methods=['GET', 'POST'])
def lab8_1():
    username = None
    flag = None
    show_login = False
    
    # Check if we should show the login page (either via query param or if submitting form)
    if request.args.get('mode') == 'login' or request.method == 'POST':
        show_login = True
    
    if request.method == 'POST':
        username = request.form.get('username')
        # VULNERABILITY: Reflecting username without sanitization
        # Check for XSS payload in username
        if username and ('<script>' in username.lower() or '%3cscript%3e' in username.lower()):
            flag = "FLAG{reflected_xss_login_successful}"
            
    return render_template('lab8/sub1.html', username=username, flag=flag, show_login=show_login)

# Lab 8.2: Stored XSS (Profile Scenario)
# Simple in-memory storage for Lab 8.2
LAB8_USERS_DB = {
    'test': {
        'password': 'test',
        'full_name': 'Joan Smith',
        'address': '123 Cyber Lane, Tech City',
        'email': 'joan.smith@techfusion.corp',
        'bio': 'Senior Analyst at TechFusion Dynamics. Love hiking and coding.'
    }
}

@app.route('/lab8/2', methods=['GET', 'POST'])
def lab8_2():
    # Login Logic
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Static check for credentials (test/test)
        if username == 'test' and password == 'test':
            session['lab8_2_user'] = username
            
            # Initialize isolated profile in session if not exists
            if 'lab8_2_profile' not in session:
                session['lab8_2_profile'] = {
                    'full_name': 'Joan Smith',
                    'email': 'joan.smith@techfusion.corp',
                    'address': '123 Cyber Lane, Tech City',
                    'bio': 'Senior Analyst at TechFusion Dynamics. Love hiking and coding.'
                }
            return redirect(url_for('lab8_2_dashboard'))
        else:
            return render_template('lab8/sub2_login.html', error="Invalid credentials")
            
    # Default GET: Show Login Page if not logged in
    if 'lab8_2_user' in session:
        return redirect(url_for('lab8_2_dashboard'))
        
    return render_template('lab8/sub2_login.html')

@app.route('/lab8/2/dashboard')
def lab8_2_dashboard():
    if 'lab8_2_user' not in session:
        return redirect(url_for('lab8_2'))
    
    # Retrieve data from SESSION, not global DB
    # This isolation allows multiple users to do the lab simultaneously
    user_data = session.get('lab8_2_profile', {})
    
    # Check for Stored XSS Flag condition
    flag = None
    for key in ['full_name', 'address', 'email', 'bio']:
        val = user_data.get(key, '')
        if val and ('<script>' in val.lower() or '%3cscript%3e' in val.lower()):
            flag = "FLAG{stored_xss_profile_pwned}"
            break
            
    return render_template('lab8/sub2_dashboard.html', user=user_data, flag=flag)

@app.route('/lab8/2/update', methods=['POST'])
def lab8_2_update():
    if 'lab8_2_user' not in session:
        return redirect(url_for('lab8_2'))
        
    # Update the SESSION data
    # We must copy/modify the dict to ensure Flask detects the change on the session object
    profile = session.get('lab8_2_profile', {}).copy()
    
    # VULNERABILITY: Storing input without sanitization
    profile['full_name'] = request.form.get('full_name')
    profile['email'] = request.form.get('email')
    profile['address'] = request.form.get('address')
    profile['bio'] = request.form.get('bio')
    
    session['lab8_2_profile'] = profile
    
    return redirect(url_for('lab8_2_dashboard'))

@app.route('/lab8/2/logout')
def lab8_2_logout():
    session.pop('lab8_2_user', None)
    return redirect(url_for('lab8_2'))
    
# Clean up old stored comments route if it exists (not used anymore)
# But keep the helper just in case
def init_lab8_2_user():
    # Helper to reset if needed
    LAB8_USERS_DB['test'] = {
        'password': 'test',
        'full_name': 'Joan Smith',
        'address': '123 Cyber Lane, Tech City',
        'email': 'joan.smith@techfusion.corp',
        'bio': 'Senior Analyst at TechFusion Dynamics.'
    }
    
    return redirect(url_for('lab8_2'))

# Endpoint to reset comments if they get too messy
@app.route('/lab8/2/reset')
def lab8_2_reset():
    global LAB8_COMMENTS
    LAB8_COMMENTS = [
        {'author': 'System Admin', 'date': '2024-03-01', 'body': 'Welcome to the feedback board! Please identify any bugs you find.'}
    ]
    return redirect(url_for('lab8_2'))


# LAB 7.1: SQL Injection in WHERE Clause (Category Filter)
@app.route('/lab7/1')
def lab7_1():
    category = request.args.get('category', '')
    
    # Initialize database connection
    db = get_db()
    cursor = db.cursor()
    
    # Ensure lab7_products table exists with sample data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab7_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            image_url TEXT,
            released INTEGER DEFAULT 1,
            category TEXT
        )
    ''')
    
    # Check if table is empty and seed data
    cursor.execute('SELECT COUNT(*) FROM lab7_products')
    if cursor.fetchone()[0] == 0:
        products_data = [
            ('Luxury Gift Box', 'Premium assortment of chocolates', 49.99, 'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?auto=format&fit=crop&w=600&q=80', 1, 'Gifts'),
            ('Personalized Mug', 'Custom photo coffee mug', 19.99, 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=600&q=80', 1, 'Gifts'),
            ('Scented Candle Set', 'Aromatherapy collection', 34.99, 'https://images.unsplash.com/photo-1602874801006-c2b5d9f6e1c7?auto=format&fit=crop&w=600&q=80', 1, 'Lifestyle'),
            ('Leather Wallet', 'Genuine leather bifold', 59.99, 'https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=600&q=80', 1, 'Accessories'),
            ('Wireless Earbuds', 'Noise-canceling audio', 89.99, 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80', 1, 'Tech'),
            ('Designer Watch', 'Limited edition timepiece', 299.99, 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80', 1, 'Accessories'),
            
            # UNRELEASED PRODUCTS (released = 0)
            ('SECRET: Diamond Necklace', 'Exclusive VIP gift - Coming Soon', 1999.99, 'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=600&q=80', 0, 'Gifts'),
            ('SECRET: Gold Cufflinks', 'Premium executive accessory', 499.99, 'https://images.unsplash.com/photo-1611085583191-a3b181a88401?auto=format&fit=crop&w=600&q=80', 0, 'Accessories'),
            ('SECRET: Smart Home Hub', 'Next-gen AI assistant', 399.99, 'https://images.unsplash.com/photo-1558089687-e28ddf4e8e5f?auto=format&fit=crop&w=600&q=80', 0, 'Tech')
        ]
        
        cursor.executemany('''
            INSERT INTO lab7_products (name, description, price, image_url, released, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', products_data)
        db.commit()
    
    # VULNERABILITY: SQL Injection in WHERE clause
    # The category parameter is directly concatenated into the SQL query
    # Normal query: SELECT * FROM lab7_products WHERE category = 'Gifts' AND released = 1
    # Exploit: category='+OR+1=1-- will bypass the released check
    
    if category:
        # VULNERABLE CODE - Direct string concatenation
        query = f"SELECT * FROM lab7_products WHERE category = '{category}' AND released = 1"
    else:
        query = "SELECT * FROM lab7_products WHERE released = 1"
    
    try:
        cursor.execute(query)
        products = cursor.fetchall()
    except Exception as e:
        # If SQL error occurs, show it (helpful for learning)
        products = []
        print(f"SQL Error: {e}")
    
    return render_template('lab7/sub1_home.html', products=products, category=category)

@app.route('/lab7/1/menu')
def lab7_1_menu():
    return render_template('lab7/sub1_menu.html')

@app.route('/lab7/1/b', methods=['GET', 'POST'])
def lab7_1_b():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab7_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM lab7_staff')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO lab7_staff (username, password, role) VALUES ('admin', 'super_secret_complex_pass_123', 'administrator')")
        cursor.execute("INSERT INTO lab7_staff (username, password, role) VALUES ('j.doe', 'password123', 'staff')")
        db.commit()

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # VULNERABLE QUERY - String concats allow auth bypass like username: admin' --
        query = f"SELECT * FROM lab7_staff WHERE username = '{username}' AND password = '{password}'"
        print(f"Executing: {query}")
        
        try:
            cursor.execute(query)
            user = cursor.fetchone()
            
            if user:
                # Login successful
                if user[3] == 'administrator':
                    return render_template('lab7/sub1_b_home.html', success=True, flag="FLAG{login_bypass_admin}", query=query)
                else:
                    return render_template('lab7/sub1_b_home.html', success=True, flag="Logged in as regular staff.", query=query)
            else:
                return render_template('lab7/sub1_b_home.html', error="Invalid username or password", query=query)
        except Exception as e:
            return render_template('lab7/sub1_b_home.html', error=f"SQL Error: {e}", query=query)
            
    return render_template('lab7/sub1_b_home.html')

@app.route('/lab7/1/c')
def lab7_1_c():
    category = request.args.get('category', 'Dogs')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab7_pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            breed TEXT,
            price REAL,
            image_url TEXT,
            available INTEGER DEFAULT 1,
            type TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab7_admin_creds (
            username TEXT,
            password TEXT
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM lab7_pets')
    if cursor.fetchone()[0] == 0:
        pets_data = [
            ('Buddy', 'Golden Retriever', 800.00, 'https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=600&q=80', 1, 'Dogs'),
            ('Luna', 'Siamese Cat', 400.00, 'https://images.unsplash.com/photo-1513245543132-31f507417b26?auto=format&fit=crop&w=600&q=80', 1, 'Cats'),
            ('Nemo', 'Clownfish', 25.00, 'https://images.unsplash.com/photo-1524704796725-9fc3044a58b2?auto=format&fit=crop&w=600&q=80', 1, 'Fish'),
        ]
        
        cursor.executemany('''
            INSERT INTO lab7_pets (name, breed, price, image_url, available, type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', pets_data)
        
        cursor.execute("INSERT INTO lab7_admin_creds (username, password) VALUES ('administrator', 'FLAG{union_based_sql_injection_master}')")
        db.commit()
    
    # VULNERABLE TO UNION ATTACK
    query = f"SELECT name, breed, price, image_url FROM lab7_pets WHERE type = '{category}' AND available = 1"
    
    try:
        cursor.execute(query)
        pets = cursor.fetchall()
    except Exception as e:
        pets = []
        print(f"SQL Error: {e}")
    
    return render_template('lab7/sub1_c_home.html', products=pets, category=category)

@app.route('/lab7/1/d')
def lab7_1_d():
    emp_id = request.args.get('id', '1')
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lab7_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            email TEXT,
            is_public INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM lab7_employees')
    if cursor.fetchone()[0] == 0:
        emp_data = [
            ('John Doe', 'Sales', 'john.doe@corp.local', 1),
            ('Jane Smith', 'Marketing', 'jane.smith@corp.local', 1),
            ('Bob Sec', 'IT Support', 'bob@corp.local', 1),
            ('Gabe Admin', 'CEO', 'gabe.awp@corp.local - FLAG{integer_sqli_expert}', 0)
        ]
        
        cursor.executemany('''
            INSERT INTO lab7_employees (name, role, email, is_public)
            VALUES (?, ?, ?, ?)
        ''', emp_data)
        db.commit()
    
    # VULNERABLE INTEGER BASED (no quotes)
    query = f"SELECT * FROM lab7_employees WHERE id = {emp_id} AND is_public = 1"
    
    try:
        cursor.execute(query)
        employees = cursor.fetchall()
    except Exception as e:
        employees = []
        print(f"SQL Error: {e}")
    
    return render_template('lab7/sub1_d_home.html', employees=employees, emp_id=emp_id)
# LAB 6.1: OS Command Injection via Stock Check
@app.route('/lab6/1/menu')
def lab6_1_menu():
    return render_template('lab6/sub1_menu.html')

# Variation A: MegaMart
@app.route('/lab6/1')
def lab6_1():
    products = [
        {'id': 1, 'name': 'Organic Bananas', 'description': 'Fresh from local farms', 'price': 2.99, 'image': 'https://images.unsplash.com/photo-1603833665858-e61d17a86224?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Whole Grain Bread', 'description': 'Artisan baked daily', 'price': 4.50, 'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'Free Range Eggs', 'description': 'Dozen large eggs', 'price': 5.99, 'image': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_home.html', products=products)

@app.route('/lab6/1/check-stock', methods=['POST'])
def lab6_1_check_stock():
    product_id = request.form.get('productId', '')
    store_id = request.form.get('storeId', '')
    
    # VULNERABILITY: OS Command Injection
    # The storeId parameter is directly concatenated into a shell command
    # An attacker can inject commands like: 1|whoami or 1;ls or 1 && cat /etc/passwd
    try:
        command = f"echo 'Stock check for product {product_id} at store {store_id}' && echo 'Units available: 42'"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        return result
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error executing stock check: {str(e)}"

# Variation B: AutoParts Pro
@app.route('/lab6/1/b')
def lab6_1_b():
    products = [
        {'id': 101, 'name': 'Brake Pads Set', 'description': 'Ceramic compound', 'price': 89.99, 'image': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=600&q=80'},
        {'id': 102, 'name': 'Oil Filter', 'description': 'Premium filtration', 'price': 12.50, 'image': 'https://images.unsplash.com/photo-1625047509168-a7026f36de04?auto=format&fit=crop&w=600&q=80'},
        {'id': 103, 'name': 'Spark Plugs', 'description': 'Iridium tipped', 'price': 24.99, 'image': 'https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_b_home.html', products=products)

@app.route('/lab6/1/b/check-stock', methods=['POST'])
def lab6_1_b_check_stock():
    product_id = request.form.get('productId', '')
    location_id = request.form.get('locationId', '')
    
    # VULNERABILITY: Same OS Command Injection, different parameter name
    try:
        command = f"echo 'Warehouse query: SKU {product_id} at location {location_id}' && echo 'Inventory count: 156'"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        return result
    except subprocess.TimeoutExpired:
        return "Error: Query timed out"
    except Exception as e:
        return f"System error: {str(e)}"

# Variation C: PharmaCare
@app.route('/lab6/1/c')
def lab6_1_c():
    products = [
        {'id': 201, 'name': 'Ibuprofen 200mg', 'description': 'Pain relief tablets', 'price': 8.99, 'image': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80'},
        {'id': 202, 'name': 'Vitamin D3', 'description': '5000 IU softgels', 'price': 15.99, 'image': 'https://images.unsplash.com/photo-1550572017-4a6e8c5c1f8c?auto=format&fit=crop&w=600&q=80'},
        {'id': 203, 'name': 'First Aid Kit', 'description': 'Complete emergency kit', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1603398938378-e54eab446dde?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_c_home.html', products=products)

@app.route('/lab6/1/c/check-stock', methods=['POST'])
def lab6_1_c_check_stock():
    product_id = request.form.get('productId', '')
    branch_id = request.form.get('branchId', '')
    
    # VULNERABILITY: Same OS Command Injection, different parameter name
    try:
        command = f"echo 'Prescription verification: NDC {product_id} at branch {branch_id}' && echo 'Stock level: 89 units'"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        return result
    except subprocess.TimeoutExpired:
        return "Error: Verification timeout"
    except Exception as e:
        return f"Database error: {str(e)}"


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
