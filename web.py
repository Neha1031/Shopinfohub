from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from psycopg2.extras import RealDictCursor
import psycopg2
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = "shopsecret123"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    try:
        return psycopg2.connect(
            host="dpg-d7vf60tckfvc73ei03a0-a",
            database="shopinfo_hnh0",
            user="shopuser",
            password="Mmdr7JSYuKPmVvBUmv0jyZoSHb5LbOUE",
            port="5432"
        )
    except Exception as e:
        print("Database connection error:", e)
        return None
    


def init_db():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        password VARCHAR(100),
        role VARCHAR(20),
        is_deleted BOOLEAN DEFAULT FALSE
    )
    """)

    cursor.execute("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    shop_name VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    shop_photo TEXT,
    address TEXT,
    map_link VARCHAR(500),
    description TEXT,
    user_email VARCHAR(255) NOT NULL,
    is_open BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE
    )
    """)

    cursor.execute("""
    ALTER TABLE shops
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE
    """)

    cursor.execute("""
    ALTER TABLE shops
    ADD COLUMN IF NOT EXISTS city VARCHAR(255)
    """)

    cursor.execute("""
    ALTER TABLE shops
    ADD COLUMN IF NOT EXISTS area VARCHAR(255)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    shop_email VARCHAR(255),
    shop_id INTEGER,
    product_name VARCHAR(255) NOT NULL,
    product_photo TEXT,
    price DECIMAL(10,2),
    details TEXT,
    voice_description TEXT,
    status VARCHAR(100),
    quantity INTEGER DEFAULT 0,
    weight VARCHAR(50),
    quality VARCHAR(100) DEFAULT 'Standard'
    )
    """)

    cursor.execute("""
    ALTER TABLE products
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE
    """)

    cursor.execute("""
    ALTER TABLE products
    ADD COLUMN IF NOT EXISTS main_category VARCHAR(100) DEFAULT 'General'
    """)
    cursor.execute("""
    ALTER TABLE products
    ADD COLUMN IF NOT EXISTS sub_category VARCHAR(100) DEFAULT 'General'
    """)
    cursor.execute("""
    ALTER TABLE products
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(100) DEFAULT 'General'
    """)

    db.commit()
    cursor.close()
    db.close()

init_db()

CATEGORIES = {
    "Women": {
        "Jewellery": ["Earrings", "Necklace", "Anklet", "Rings"],
        "Clothes": ["Tops", "Dresses", "Sarees", "Kurtis"],
        "Hair Accessories": ["Clips", "Bands", "Pins"]
    },
    "Men": {
        "Clothes": ["Shirts", "T-Shirts", "Jeans", "Trousers"],
        "Footwear": ["Sneakers", "Formal", "Sandals"],
        "Accessories": ["Watches", "Belts", "Wallets"]
    },
    "Electronics": {
        "Mobiles": ["Smartphones", "Feature Phones", "Cases"],
        "Computers": ["Laptops", "Desktops", "Accessories"],
        "Audio": ["Headphones", "Earbuds", "Speakers"]
    },
    "Groceries": {
        "Staples": ["Rice", "Flour", "Dal"],
        "Snacks": ["Chips", "Biscuits", "Namkeen"],
        "Beverages": ["Tea", "Coffee", "Juices"]
    }
}

# Home / Public Dashboard
@app.route('/')
def home():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    # Fetch random products for the product dashboard
    cursor.execute("""
        SELECT p.*, s.shop_name 
        FROM products p
        JOIN shops s ON p.shop_id = s.id
        WHERE p.is_deleted = FALSE AND s.is_deleted = FALSE
        ORDER BY RANDOM() 
        LIMIT 6
    """)
    random_products = cursor.fetchall()
    db.close()
    
    return render_template('index.html', random_products=random_products, categories=CATEGORIES)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(
                "INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,%s)",
                (name, email, password, role)
            )
            db.commit()
            flash("Registered Successfully! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Error during registration. Email might already exist.", "error")
        finally:
            db.close()

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s AND is_deleted=FALSE",
            (email, password)
        )
        user = cursor.fetchone()
        db.close()

        if user:
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            if user['role'] == "shopkeeper":
                return redirect(url_for('shopkeeper_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            flash("Invalid Login credentials", "error")

    return render_template('login.html')

# Add Shop (Shopkeeper)
@app.route('/addshop', methods=['GET', 'POST'])
def addshop():
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        shop_name = request.form.get('shop_name', '')
        owner_name = request.form.get('owner_name', '')
        address = request.form.get('address', '')
        map_link = request.form.get('map_link', '')
        description = request.form.get('description', '')
        user_email = session['email']

        shop_photo = ''
        file = request.files.get('shop_photo_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            shop_photo = url_for('static', filename='uploads/' + filename)
        else:
            shop_photo = request.form.get('shop_photo_url', '')

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "INSERT INTO shops(shop_name,owner_name,shop_photo,address,map_link,description,user_email) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (shop_name, owner_name, shop_photo, address, map_link, description, user_email)
        )
        db.commit()
        db.close()
        flash("Shop Added Successfully!", "success")
        return redirect(url_for('shopkeeper_dashboard'))

    return render_template('add_shop.html')

# View Catalog (Specific Shop Details + Products) - PUBLIC
@app.route('/shop/<int:shop_id>')
def shop_catalog(shop_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    # Get Shop info
    cursor.execute("SELECT * FROM shops WHERE id=%s AND is_deleted=FALSE", (shop_id,))
    shop_info = cursor.fetchone()
    
    if not shop_info:
        db.close()
        return "Shop not found", 404
        
    # Get products for THIS specific shop
    cursor.execute("SELECT * FROM products WHERE shop_id=%s AND is_deleted=FALSE", (shop_id,))
    products = cursor.fetchall()
    
    db.close()
    return render_template('shop_catalog.html', shop=shop_info, products=products)


# View All Shops - PUBLIC
@app.route('/shops')
def list_shops():
    search_query = request.args.get('q', '')
    
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    if search_query:
        sql = """
            SELECT DISTINCT s.*
            FROM shops s
            LEFT JOIN products p ON s.id = p.shop_id
            WHERE (
                s.shop_name ILIKE %s
                OR s.address ILIKE %s
                OR s.city ILIKE %s
                OR s.area ILIKE %s
                OR p.product_name ILIKE %s
            )
            AND s.is_deleted = FALSE
        """
        val = f"%{search_query}%"
        cursor.execute(sql, (val, val, val, val, val))
    else:
        cursor.execute("SELECT * FROM shops WHERE is_deleted=FALSE")
        
    data = cursor.fetchall()
    db.close()

    return render_template('shops.html', shops=data, search_query=search_query)

# Manage Specific Shop Dashboard (Shopkeeper)
@app.route('/manage_shop/<int:shop_id>')
def manage_shop(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM shops WHERE id=%s AND user_email=%s AND is_deleted=FALSE", (shop_id, session['email']))
    shop = cursor.fetchone()
    
    if not shop:
        db.close()
        return "Not authorized to manage this shop or it does not exist.", 403
        
    cursor.execute("SELECT * FROM products WHERE shop_id=%s AND is_deleted=FALSE", (shop_id,))
    products = cursor.fetchall()
    db.close()
    
    return render_template('manage_shop.html', shop=shop, products=products)

# Add Product to specific shop (Shopkeeper)
@app.route('/addproduct/<int:shop_id>', methods=['GET', 'POST'])
def addproduct(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM shops WHERE id=%s AND user_email=%s", (shop_id, session['email']))
    shop = cursor.fetchone()
    
    if not shop:
        db.close()
        return "Unauthorized", 403
        
    if request.method == 'POST':
        product_name = request.form.get('product_name', '')
        price = request.form.get('price', 0)
        details = request.form.get('details', '')
        voice_desc = request.form.get('voice_description', '')
        status = request.form.get('status', 'Available')
        quantity = request.form.get('quantity', 0)
        weight = request.form.get('weight', '')
        quality = request.form.get('quality', 'Standard')
        
        main_category = request.form.get('main_category', 'General')
        sub_category = request.form.get('sub_category', 'General')
        item_type = request.form.get('item_type', 'General')

        if not quantity:
            quantity = 0

        product_photo = ''
        file = request.files.get('product_photo_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product_photo = url_for('static', filename='uploads/' + filename)
        else:
            product_photo = request.form.get('product_photo_url', '')

        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """INSERT INTO products(shop_email, shop_id, product_name, product_photo, price, details, voice_description, status, quantity, weight, quality, main_category, sub_category, item_type) 
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (session['email'], shop_id, product_name, product_photo, price, details, voice_desc, status, quantity, weight, quality, main_category, sub_category, item_type)
        )
        db.commit()
        db.close()
        flash("Product Added Successfully!", "success")
        return redirect(url_for('manage_shop', shop_id=shop_id))

    db.close()
    return render_template('add_product.html', shop=shop, categories=CATEGORIES)

# Toggle Shop Status (Open/Close) specific to shop ID
@app.route('/toggle_shop_status/<int:shop_id>', methods=['POST'])
def toggle_shop_status(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE shops SET is_open = NOT is_open WHERE id = %s AND user_email = %s AND is_deleted=FALSE", (shop_id, session['email']))
    db.commit()
    db.close()
    
    flash("Shop status updated successfully!", "success")
    return redirect(url_for('manage_shop', shop_id=shop_id))

# Update Product Status
@app.route('/update_product_status/<int:product_id>', methods=['POST'])
def update_product_status(product_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    new_status = request.form['status']
    
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    # Ensure they own this product
    cursor.execute("SELECT shop_id FROM products WHERE id=%s AND shop_email=%s AND is_deleted=FALSE", (product_id, session['email']))
    prod = cursor.fetchone()
    
    if prod:
        cursor.execute("UPDATE products SET status=%s WHERE id=%s", (new_status, product_id))
        db.commit()
        flash("Product status updated!", "success")
        db.close()
        return redirect(url_for('manage_shop', shop_id=prod['shop_id']))
    
    db.close()
    return "Not authorized", 403

# Delete Product
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    # Ensure they own this product
    cursor.execute("SELECT shop_id FROM products WHERE id=%s AND shop_email=%s AND is_deleted=FALSE ", (product_id, session['email']))
    prod = cursor.fetchone()
    
    if prod:
        cursor.execute("UPDATE products SET is_deleted=TRUE  WHERE id=%s", (product_id,))
        db.commit()
        flash("Product deleted successfully!", "success")
        db.close()
        return redirect(url_for('manage_shop', shop_id=prod['shop_id']))
        
    db.close()
    return "Not authorized", 403

# Delete Shop
@app.route('/delete_shop/<int:shop_id>', methods=['POST'])
def delete_shop(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    # Ensure they own this shop
    cursor.execute("SELECT id FROM shops WHERE id=%s AND user_email=%s", (shop_id, session['email']))
    shop = cursor.fetchone()
    
    if shop:
        # Soft delete shop
        cursor.execute("UPDATE shops SET is_deleted=TRUE WHERE id=%s", (shop_id,))
        # Soft delete all products of this shop
        cursor.execute("UPDATE products SET is_deleted=TRUE WHERE shop_id=%s", (shop_id,))
        db.commit()
        flash("Shop deleted successfully!", "success")
        db.close()
        return redirect(url_for('shopkeeper_dashboard'))
        
    db.close()
    return "Not authorized", 403

# Delete Account
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'email' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE users SET is_deleted = 1 WHERE email = %s", (session['email'],))
    # Soft delete all shops of this user
    cursor.execute("UPDATE shops SET is_deleted = 1 WHERE user_email = %s", (session['email'],))
    # Soft delete all products of this user
    cursor.execute("UPDATE products SET is_deleted = 1 WHERE shop_email = %s", (session['email'],))
    db.commit()
    db.close()
    
    session.clear()
    flash("Your account and all associated data have been permanently deleted.", "success")
    return redirect(url_for('home'))

# Shopkeeper Dashboard (Multi-Shop Viewer)
@app.route('/shopkeeper_dashboard')
def shopkeeper_dashboard():
    if 'email' not in session or session['role'] != 'shopkeeper':
        return redirect('/login')

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM shops WHERE user_email=%s AND is_deleted=FALSE", (session['email'],))
    shops = cursor.fetchall()
    
    db.close()

    return render_template(
        'shopkeeper_dashboard.html',
        name=session['name'],
        shops=shops
    )

# Customer Dashboard
@app.route('/customer_dashboard')
def customer_dashboard():
    if 'email' not in session or session['role'] != 'customer':
        return redirect('/login')
        
    search_query = request.args.get('q', '')
    
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    if search_query:
        sql = """
            SELECT DISTINCT s.* 
            FROM shops s
            LEFT JOIN products p ON s.id = p.shop_id
            WHERE (s.shop_name ILIKE %s 
               OR s.address ILIKE %s 
               OR s.city ILIKE %s 
               OR s.area ILIKE %s 
               OR p.product_name ILIKE %s)
               AND s.is_deleted = FALSE
        """
        val = f"%{search_query}%"
        cursor.execute(sql, (val, val, val, val, val))
    else:
        cursor.execute("SELECT * FROM shops WHERE is_deleted=FALSE")
        
    all_shops = cursor.fetchall()
    db.close()

    return render_template('customer_dashboard.html', name=session['name'], shops=all_shops, search_query=search_query)

@app.route('/upgrade_to_shopkeeper', methods=['POST'])
def upgrade_to_shopkeeper():
    if 'email' not in session or session['role'] != 'customer':
        return redirect('/login')

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE users SET role='shopkeeper' WHERE email=%s", (session['email'],))
    db.commit()
    db.close()

    session['role'] = 'shopkeeper'
    flash("Congratulations! You are now a Shopkeeper. You can start creating your shops.", "success")
    return redirect(url_for('shopkeeper_dashboard'))

@app.route('/downgrade_to_customer', methods=['POST'])
def downgrade_to_customer():
    if 'email' not in session or session['role'] != 'shopkeeper':
        return redirect('/login')

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE users SET role='customer' WHERE email=%s", (session['email'],))
    db.commit()
    db.close()

    session['role'] = 'customer'
    flash("You have exited the Business Dashboard and returned to Customer mode.", "success")
    return redirect(url_for('customer_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/')

# Static Pages
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# Product Details - PUBLIC
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT p.*, s.shop_name, s.address, s.map_link, s.city, s.area
        FROM products p
        JOIN shops s ON p.shop_id = s.id
        WHERE p.id = %s AND p.is_deleted = FALSE AND s.is_deleted = FALSE
    """, (product_id,))
    product = cursor.fetchone()
    
    db.close()
    
    if not product:
        return "Product not found", 404
        
    return render_template('product_detail.html', product=product)

@app.route('/category/<cat_name>')
def category_page(cat_name):
    # Pass the full subcategory dict to the template
    category_data = {}
    if cat_name in CATEGORIES:
        category_data = CATEGORIES[cat_name]
        
    return render_template('category_page.html', main_category=cat_name, category_data=category_data)

# API to fetch products dynamically for the homepage or category page
@app.route('/api/products')
def api_products():
    cat = request.args.get('category', '')
    sub_cat = request.args.get('sub_category', '')
    item_t = request.args.get('item_type', '')
    if not cat:
        return jsonify([])
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    
    if sub_cat and item_t:
        product_query = """
            SELECT p.*, s.shop_name, s.address 
            FROM products p
            JOIN shops s ON p.shop_id = s.id
            WHERE p.is_deleted = FALSE AND s.is_deleted = FALSE AND p.main_category = %s AND p.sub_category = %s AND p.item_type = %s
        """
        cursor.execute(product_query, (cat, sub_cat, item_t))
    elif sub_cat:
        product_query = """
            SELECT p.*, s.shop_name, s.address 
            FROM products p
            JOIN shops s ON p.shop_id = s.id
            WHERE p.is_deleted = FALSE AND s.is_deleted = FALSE AND p.main_category = %s AND p.sub_category = %s
        """
        cursor.execute(product_query, (cat, sub_cat))
    else:
        product_query = """
            SELECT p.*, s.shop_name, s.address 
            FROM products p
            JOIN shops s ON p.shop_id = s.id
            WHERE p.is_deleted = FALSE AND s.is_deleted = FALSE AND p.main_category = %s
        """
        cursor.execute(product_query, (cat,))
        
    products = cursor.fetchall()
    db.close()
    
    return jsonify(products)

# Unified Search (Shops and Products) - PUBLIC
@app.route('/search')
def search():
    q = request.args.get('q', '')
    cat = request.args.get('category', '')
    subcat = request.args.get('sub_category', '')
    item = request.args.get('item_type', '')
    
    if not q and not cat:
        return redirect(url_for('home'))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)

    shops = []
    
    # Only search shops if there is a text query and NO category filters
    if q and not cat:
        shop_sql = """
            SELECT * FROM shops
            WHERE (
                shop_name ILIKE %s OR address ILIKE %s OR city ILIKE %s OR area ILIKE %s
            ) AND is_deleted = FALSE
        """
        val = f"%{q}%"
        cursor.execute(shop_sql, (val, val, val, val))
        shops = cursor.fetchall()

    # Search Products dynamically based on provided filters
    product_query = """
        SELECT p.*, s.shop_name, s.address 
        FROM products p
        JOIN shops s ON p.shop_id = s.id
        WHERE p.is_deleted = FALSE AND s.is_deleted = FALSE
    """
    params = []
    
    if q:
        product_query += " AND (p.product_name ILIKE %s OR p.details ILIKE %s OR s.shop_name ILIKE %s)"
        val = f"%{q}%"
        params.extend([val, val, val])
        
    if cat:
        product_query += " AND p.main_category = %s"
        params.append(cat)
    if subcat:
        product_query += " AND p.sub_category = %s"
        params.append(subcat)
    if item:
        product_query += " AND p.item_type = %s"
        params.append(item)

    cursor.execute(product_query, tuple(params))
    products = cursor.fetchall()

    db.close()

    # Determine display title
    display_title = q if q else ''
    if cat:
        display_title = f"{cat}"
        if subcat: display_title += f" > {subcat}"
        if item: display_title += f" > {item}"

    return render_template('search_results.html', query=display_title, shops=shops, products=products)
