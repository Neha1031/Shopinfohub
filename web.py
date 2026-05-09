from flask import Flask, render_template, request, session, redirect, url_for, flash
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
    if db:
        cursor = db.cursor()
        try:
            # Check products table patches
            cursor.execute("SHOW COLUMNS FROM products LIKE 'quantity'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE products ADD COLUMN quantity INT DEFAULT 0")
                db.commit()

            cursor.execute("SHOW COLUMNS FROM products LIKE 'quality'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE products ADD COLUMN quality VARCHAR(100) DEFAULT 'Standard'")
                db.commit()
                
            cursor.execute("SHOW COLUMNS FROM products LIKE 'weight'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE products ADD COLUMN weight VARCHAR(50)")
                db.commit()
                
            cursor.execute("SHOW COLUMNS FROM products LIKE 'voice_description'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE products ADD COLUMN voice_description TEXT")
                db.commit()

            cursor.execute("SHOW COLUMNS FROM products LIKE 'shop_id'")
            if not cursor.fetchone():
                # Add shop_id
                cursor.execute("ALTER TABLE products ADD COLUMN shop_id INT")
                cursor.execute("ALTER TABLE products ADD FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE")
                db.commit()
                # Auto-migrate existing products: tie to first found shop of that user
                cursor.execute("""
                    UPDATE products p 
                    JOIN shops s ON s.user_email = p.shop_email 
                    SET p.shop_id = s.id 
                    WHERE p.shop_id IS NULL 
                """)
                db.commit()

            # Soft Delete columns
            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_deleted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                db.commit()

            cursor.execute("SHOW COLUMNS FROM shops LIKE 'is_deleted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE shops ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                db.commit()

            cursor.execute("SHOW COLUMNS FROM products LIKE 'is_deleted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE products ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                db.commit()

            # Increase length for photo columns
            cursor.execute("ALTER TABLE shops MODIFY COLUMN shop_photo LONGTEXT")
            cursor.execute("ALTER TABLE products MODIFY COLUMN product_photo LONGTEXT")
            db.commit()
                
        except Exception as e:
            print("Auto-patch DB error:", e)
        finally:
            db.close()

# Run DB checks on startup
init_db()

# Home / Public Dashboard
@app.route('/')
def home():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        db = get_db_connection()
        cursor = db.cursor()
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
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s AND is_deleted=0",
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
        cursor = db.cursor()
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
    cursor = db.cursor(dictionary=True)
    
    # Get Shop info
    cursor.execute("SELECT * FROM shops WHERE id=%s AND is_deleted=0", (shop_id,))
    shop_info = cursor.fetchone()
    
    if not shop_info:
        db.close()
        return "Shop not found", 404
        
    # Get products for THIS specific shop
    cursor.execute("SELECT * FROM products WHERE shop_id=%s AND is_deleted=0", (shop_id,))
    products = cursor.fetchall()
    
    db.close()
    return render_template('shop_catalog.html', shop=shop_info, products=products)


# View All Shops - PUBLIC
@app.route('/shops')
def list_shops():
    search_query = request.args.get('q', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    if search_query:
        sql = """
            SELECT DISTINCT s.* 
            FROM shops s
            LEFT JOIN products p ON s.id = p.shop_id
            WHERE (s.shop_name LIKE %s 
               OR s.address LIKE %s 
               OR p.product_name LIKE %s)
               AND s.is_deleted = 0
        """
        val = f"%{search_query}%"
        cursor.execute(sql, (val, val, val))
    else:
        cursor.execute("SELECT * FROM shops WHERE is_deleted=0")
        
    data = cursor.fetchall()
    db.close()

    return render_template('shops.html', shops=data, search_query=search_query)

# Manage Specific Shop Dashboard (Shopkeeper)
@app.route('/manage_shop/<int:shop_id>')
def manage_shop(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM shops WHERE id=%s AND user_email=%s AND is_deleted=0", (shop_id, session['email']))
    shop = cursor.fetchone()
    
    if not shop:
        db.close()
        return "Not authorized to manage this shop or it does not exist.", 403
        
    cursor.execute("SELECT * FROM products WHERE shop_id=%s AND is_deleted=0", (shop_id,))
    products = cursor.fetchall()
    db.close()
    
    return render_template('manage_shop.html', shop=shop, products=products)

# Add Product to specific shop (Shopkeeper)
@app.route('/addproduct/<int:shop_id>', methods=['GET', 'POST'])
def addproduct(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
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

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO products(shop_email, shop_id, product_name, product_photo, price, details, voice_description, status, quantity, weight, quality) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (session['email'], shop_id, product_name, product_photo, price, details, voice_desc, status, quantity, weight, quality)
        )
        db.commit()
        db.close()
        flash("Product Added Successfully!", "success")
        return redirect(url_for('manage_shop', shop_id=shop_id))

    db.close()
    return render_template('add_product.html', shop=shop)

# Toggle Shop Status (Open/Close) specific to shop ID
@app.route('/toggle_shop_status/<int:shop_id>', methods=['POST'])
def toggle_shop_status(shop_id):
    if 'role' not in session or session['role'] != 'shopkeeper':
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE shops SET is_open = NOT is_open WHERE id = %s AND user_email = %s AND is_deleted=0", (shop_id, session['email']))
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
    cursor = db.cursor(dictionary=True)
    
    # Ensure they own this product
    cursor.execute("SELECT shop_id FROM products WHERE id=%s AND shop_email=%s AND is_deleted=0", (product_id, session['email']))
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
    cursor = db.cursor(dictionary=True)
    
    # Ensure they own this product
    cursor.execute("SELECT shop_id FROM products WHERE id=%s AND shop_email=%s AND is_deleted=0", (product_id, session['email']))
    prod = cursor.fetchone()
    
    if prod:
        cursor.execute("UPDATE products SET is_deleted=1 WHERE id=%s", (product_id,))
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
    cursor = db.cursor(dictionary=True)
    
    # Ensure they own this shop
    cursor.execute("SELECT id FROM shops WHERE id=%s AND user_email=%s", (shop_id, session['email']))
    shop = cursor.fetchone()
    
    if shop:
        # Soft delete shop
        cursor.execute("UPDATE shops SET is_deleted=1 WHERE id=%s", (shop_id,))
        # Soft delete all products of this shop
        cursor.execute("UPDATE products SET is_deleted=1 WHERE shop_id=%s", (shop_id,))
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
    cursor = db.cursor()
    # Soft delete user
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
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM shops WHERE user_email=%s AND is_deleted=0", (session['email'],))
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
    cursor = db.cursor(dictionary=True)
    
    if search_query:
        sql = """
            SELECT DISTINCT s.* 
            FROM shops s
            LEFT JOIN products p ON s.id = p.shop_id
            WHERE (s.shop_name LIKE %s 
               OR s.address LIKE %s 
               OR p.product_name LIKE %s)
               AND s.is_deleted = 0
        """
        val = f"%{search_query}%"
        cursor.execute(sql, (val, val, val))
    else:
        cursor.execute("SELECT * FROM shops WHERE is_deleted=0")
        
    all_shops = cursor.fetchall()
    db.close()

    return render_template('customer_dashboard.html', name=session['name'], shops=all_shops, search_query=search_query)

@app.route('/upgrade_to_shopkeeper', methods=['POST'])
def upgrade_to_shopkeeper():
    if 'email' not in session or session['role'] != 'customer':
        return redirect('/login')

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET role='shopkeeper' WHERE email=%s", (session['email'],))
    db.commit()
    db.close()

    session['role'] = 'shopkeeper'
    flash("Congratulations! You are now a Shopkeeper. You can start creating your shops.", "success")
    return redirect(url_for('shopkeeper_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)