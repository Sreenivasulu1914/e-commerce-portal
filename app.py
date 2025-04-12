from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
import stripe
from flask_mail import Mail, Message
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import logging
from flask_cors import CORS
from mysql.connector import Error
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'panasabotlasreenivas@gmail.com'
app.config['MAIL_PASSWORD'] = 'qlxxgqilaexieurn'
mail = Mail(app)

# Stripe API key
stripe.api_key = 'sk_test_51QkgcEC4jul9TxeyUqx9asajB3S1xzcCW3TIoFcSVcplhduCU1G2AOrZEIQaeGUVBkde2JnC1qx8147RLkv9syNx00EaeoMf7n'

# Generate and send OTP
def send_otp(email):
    try:
        otp = random.randint(100000, 999999)
        msg = Message('Your OTP', sender='panasabotlasreenivas@gmail.com', recipients=[email])
        msg.body = f'Your OTP is {otp}'
        mail.send(msg)
        logger.info(f"OTP sent to {email}")
        return otp
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}")
        raise

# Database connection function
def get_db_connection():
    try:
        config = {
            'host': os.environ.get('DB_HOST', 'mainline.proxy.rlwy.net'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASS', 'mmjNeFRrEgFPeCbpnNxbJjWuxVqZPaOr'),
            'port': int(os.environ.get('DB_PORT', '47424')),
            'database': os.environ.get('DB_NAME', 'railway'),
            'raise_on_warnings': True
        }
        logger.info(f"Attempting DB connection: {config['host']}:{config['port']}")
        conn = mysql.connector.connect(**config)
        logger.info("DB connection successful")
        return conn
    except mysql.connector.Error as e:
        logger.error(f"DB Connection failed: {e.errno} - {str(e)}")
        return None

# Login route with OTP
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        hcaptcha_response = request.form['h-captcha-response']
        
        # Verify hCaptcha
        secret_key = 'ES_cbbc36b5577144fc99e380d107a62918'
        payload = {'secret': secret_key, 'response': hcaptcha_response}
        response = requests.post('https://hcaptcha.com/siteverify', data=payload)
        result = response.json()
        
        if not result.get('success'):
            flash('Invalid hCaptcha. Please try again.', 'danger')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Login: No DB connection")
            flash('Database connection failed', 'danger')
            return redirect(url_for('login'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM user_info WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.fetchall()  # Clear results
            cursor.close()
            conn.close()
            if user:
                otp = send_otp(email)
                session['otp'] = otp
                session['email'] = email
                flash('OTP sent to your email address', 'info')
                return redirect(url_for('verify_otp'))
            else:
                flash('Email is not registered', 'danger')
                return redirect(url_for('login'))
        except mysql.connector.Error as e:
            logger.error(f"Login failed: {e.errno} - {str(e)}")
            conn.close()
            flash('Database error', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# Verify OTP
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if int(entered_otp) == session.get('otp'):
            email = session.get('email')
            conn = get_db_connection()
            if conn is None:
                logger.error("Verify OTP: No DB connection")
                flash('Database connection failed', 'danger')
                return redirect(url_for('login'))
            
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    'SELECT u.role, u.username, u.user_id FROM users u JOIN user_info ui ON u.user_id = ui.user_id WHERE ui.email = %s',
                    (email,)
                )
                user = cursor.fetchone()
                cursor.fetchall()
                cursor.close()
                conn.close()
                if user:
                    session['role'] = user['role']
                    session['username'] = user['username']
                    session['user_id'] = user['user_id']
                    flash('Login successful', 'success')
                    return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('user_dashboard'))
                else:
                    flash('User not found', 'danger')
                    return redirect(url_for('login'))
            except mysql.connector.Error as e:
                logger.error(f"Verify OTP failed: {e.errno} - {str(e)}")
                conn.close()
                flash('Database error', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid OTP', 'danger')
            return redirect(url_for('login'))
    return render_template('verify_otp.html')

# Main route
@app.route('/')
def index():
    logger.info("Rendering index page")
    return render_template('index.html')

@app.route('/about')
def about_us():
    return render_template('about_us.html')

@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = 'panasabotlasreenivas@gmail.com'
        msg['Subject'] = subject
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('panasabotlasreenivas@gmail.com', 'qlxxgqilaexieurn')
            server.sendmail(email, 'panasabotlasreenivas@gmail.com', msg.as_string())
            server.quit()
            flash('Message sent successfully', 'success')
        except Exception as e:
            logger.error(f"Contact email failed: {str(e)}")
            flash(f'Error sending message: {str(e)}', 'danger')
        return redirect(url_for('contact_us'))
    return render_template('contact_us.html')











# ... your get_db_connection() and other routes ...

@app.route('/api/admin_stats')
def admin_stats():
    conn = get_db_connection()
    if conn is None:
        print("DB connection failed")
        return jsonify({'products': 0, 'categories': 0, 'companies': 0, 'orders': 0}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) AS count FROM products')
        products = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM categories')
        categories = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM brands')  # Adjusted to 'companies'
        companies = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM orders')
        orders = cursor.fetchone()['count']
        cursor.close()
        conn.close()
        print(f"Stats fetched: products={products}, categories={categories}, companies={companies}, orders={orders}")
        return jsonify({
            'products': products,
            'categories': categories,
            'companies': companies,
            'orders': orders
        })
    except Error as e:
        print(f"DB error: {e}")
        cursor.close()
        conn.close()
        return jsonify({'products': 0, 'categories': 0, 'companies': 0, 'orders': 0}), 500

# ... rest of your routes ...











@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# Cart routes
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please log in to add items to your cart', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Add to cart: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('products'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM cart WHERE user_id = %s AND product_id = %s', (user_id, product_id))
        cart_item = cursor.fetchone()
        if cart_item:
            cursor.execute('UPDATE cart SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s', (user_id, product_id))
        else:
            cursor.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)', (user_id, product_id, 1))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product added to cart successfully', 'success')
        return redirect(url_for('cart'))
    except mysql.connector.Error as e:
        logger.error(f"Add to cart failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('products'))

@app.route('/api/remove_from_cart/<int:product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Remove from cart: No DB connection")
        return jsonify({'success': False, 'error': 'Database connection failed'})
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = %s AND product_id = %s', (user_id, product_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except mysql.connector.Error as e:
        logger.error(f"Remove from cart failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    
    user_id = session['user_id']
    new_quantity = request.json.get('quantity')
    conn = get_db_connection()
    if conn is None:
        logger.error("Update cart quantity: No DB connection")
        return jsonify({'success': False, 'error': 'Database connection failed'})
    
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s', (new_quantity, user_id, product_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except mysql.connector.Error as e:
        logger.error(f"Update cart quantity failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cart_count')
def cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Cart count: No DB connection")
        return jsonify({'count': 0, 'error': 'Database connection failed'})
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(quantity) FROM cart WHERE user_id = %s', (user_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({'count': count if count else 0})
    except mysql.connector.Error as e:
        logger.error(f"Cart count failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'count': 0, 'error': str(e)})

# Dashboard routes
@app.route('/user_dashboard')
def user_dashboard():
    logger.info("Rendering user dashboard")
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'danger')
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    logger.info("Rendering admin dashboard")
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')

# Change password
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in to change your password', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
        if new_password != confirm_new_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('change_password'))
        
        user_id = session['user_id']
        conn = get_db_connection()
        if conn is None:
            logger.error("Change password: No DB connection")
            flash('Database connection failed', 'danger')
            return redirect(url_for('change_password'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT password FROM users WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()
            if user and user['password'] == current_password:
                cursor.execute('UPDATE users SET password = %s WHERE user_id = %s', (new_password, user_id))
                conn.commit()
                flash('Password changed successfully', 'success')
            else:
                flash('Current password is incorrect', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('change_password'))
        except mysql.connector.Error as e:
            logger.error(f"Change password failed: {e.errno} - {str(e)}")
            conn.close()
            flash('Database error', 'danger')
            return redirect(url_for('change_password'))
    return render_template('change_password.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        contact = request.form['contact']
        email = request.form['email']
        date_of_birth = request.form['date_of_birth']
        address = request.form['address']
        city = request.form['city'] or request.form['manual_city']
        state = request.form['state'] or request.form['manual_state']
        country = request.form['country'] or request.form['manual_country']
        image = request.files['image']
        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        os.makedirs(upload_folder, exist_ok=True)
        image_filename = image.filename
        image_path = os.path.join(upload_folder, image_filename)
        image.save(image_path)
        conn = get_db_connection()
        if conn is None:
            logger.error("Register: No DB connection")
            flash('Database connection failed', 'danger')
            return jsonify({'error': 'Database connection failed'}), 500
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                (username, password, role)
            )
            user_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO user_info (user_id, contact, email, date_of_birth, address, city, state, country, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (user_id, contact, email, date_of_birth, address, city, state, country, image_filename)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Registration successful', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            logger.error(f"Register failed: {e.errno} - {str(e)}")
            conn.close()
            flash('Database error', 'danger')
            return jsonify({'error': str(e)}), 500
    return render_template('register.html')

# Products page
@app.route('/products')
def products():
    return render_template('products.html')

# Account details
@app.route('/account_details')
def account_details():
    if 'user_id' not in session:
        flash('Please log in to view your account details', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Account details: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT u.username, ui.email, ui.contact, ui.date_of_birth, ui.address, ui.city, ui.state, ui.country, ui.image '
            'FROM users u JOIN user_info ui ON u.user_id = ui.user_id WHERE u.user_id = %s',
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('account_details.html', user=user)
    except mysql.connector.Error as e:
        logger.error(f"Account details failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        flash('Please log in to update your account details', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    username = request.form['username']
    email = request.form['email']
    contact = request.form['contact']
    date_of_birth = request.form['date_of_birth']
    address = request.form['address']
    city = request.form['city']
    state = request.form['state']
    country = request.form['country']
    image = request.files['image']
    upload_folder = os.path.join(app.root_path, 'static', 'upload')
    os.makedirs(upload_folder, exist_ok=True)
    image_filename = None
    if image and image.filename:
        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Update account: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('account_details'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'UPDATE users u JOIN user_info ui ON u.user_id = ui.user_id '
            'SET u.username = %s, ui.email = %s, ui.contact = %s, ui.date_of_birth = %s, ui.address = %s, ui.city = %s, ui.state = %s, ui.country = %s '
            'WHERE u.user_id = %s',
            (username, email, contact, date_of_birth, address, city, state, country, user_id)
        )
        if image_filename:
            cursor.execute('UPDATE user_info SET image = %s WHERE user_id = %s', (image_filename, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Account details updated successfully', 'success')
        return redirect(url_for('account_details'))
    except mysql.connector.Error as e:
        logger.error(f"Update account failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('account_details'))

# Order details
@app.route('/order_details')
def order_details():
    if 'user_id' not in session:
        flash('Please log in to view your orders', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Order details: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT oi.order_item_id, p.product_name, p.image, p.cost, oi.quantity '
            'FROM orderitems oi JOIN products p ON oi.product_id = p.product_id JOIN orders o ON oi.order_id = o.order_id '
            'WHERE o.user_id = %s',
            (user_id,)
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('order_detail.html', orders=orders)
    except mysql.connector.Error as e:
        logger.error(f"Order details failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/place_order')
def place_order():
    if 'user_id' not in session:
        flash('Please log in to place an order', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Place order: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('cart'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT SUM(p.cost * c.quantity) AS total_amount FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s',
            (user_id,)
        )
        total_amount = cursor.fetchone()['total_amount']
        cursor.close()
        conn.close()
        return render_template('place_order.html', total_amount=total_amount)
    except mysql.connector.Error as e:
        logger.error(f"Place order failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('cart'))

@app.route('/process_payment')
def process_payment():
    if 'user_id' not in session:
        flash('Please log in to place an order', 'danger')
        return redirect(url_for('login'))
    
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Payment failed or canceled', 'danger')
        return redirect(url_for('cart'))
    
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status != 'paid':
            flash('Payment not completed', 'danger')
            return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")
        flash('Payment verification failed', 'danger')
        return redirect(url_for('cart'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Process payment: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('cart'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO orders (user_id, total_amount) VALUES (%s, %s)', (user_id, checkout_session.amount_total / 100))
        order_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO orderitems (order_id, product_id, quantity, price) '
            'SELECT %s, cart.product_id, cart.quantity, products.cost '
            'FROM cart JOIN products ON cart.product_id = products.product_id WHERE cart.user_id = %s',
            (order_id, user_id)
        )
        cursor.execute('DELETE FROM cart WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Payment successful and order placed', 'success')
        return redirect(url_for('order_details'))
    except mysql.connector.Error as e:
        logger.error(f"Process payment failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('cart'))

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'user_id' not in session:
        flash('Please log in to place an order', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Create checkout session: No DB connection")
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT p.product_id, p.product_name, p.cost, c.quantity '
            'FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s',
            (user_id,)
        )
        cart_items = cursor.fetchall()
        cursor.close()
        conn.close()
        line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': item['product_name']},
                'unit_amount': int(item['cost'] * 100),
            },
            'quantity': item['quantity'],
        } for item in cart_items]
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('process_payment', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cart', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        logger.error(f"Create checkout session failed: {str(e)}")
        return jsonify({'error': str(e)}), 403

# API routes
@app.route('/api/products')
def api_products():
    query = request.args.get('search', '')
    category = request.args.get('category', '')
    conn = get_db_connection()
    if conn is None:
        logger.error("Products: No DB connection")
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        sql = 'SELECT product_id, product_name, description, image FROM products WHERE 1=1'
        params = []
        if query:
            sql += ' AND product_name LIKE %s'
            params.append(f'%{query}%')
        if category:
            sql += ' AND category_id = %s'
            params.append(category)
        cursor.execute(sql, params)
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Fetched {len(products)} products")
        return jsonify(products)
    except mysql.connector.Error as e:
        logger.error(f"Products fetch failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def api_categories():
    conn = get_db_connection()
    if conn is None:
        logger.error("Categories: No DB connection")
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Fetched {len(categories)} categories")
        return jsonify(categories)
    except mysql.connector.Error as e:
        logger.error(f"Categories fetch failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/categories')
def categories():
    return render_template('category.html')

@app.route('/api/companies')
def api_companies():
    conn = get_db_connection()
    if conn is None:
        logger.error("Companies: No DB connection")
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM brands')
        companies = cursor.fetchall()
        cursor.close()
        conn.close()
        logger.info(f"Fetched {len(companies)} companies")
        return jsonify(companies)
    except mysql.connector.Error as e:
        logger.error(f"Companies fetch failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/company')
def company():
    return render_template('company.html')

@app.route('/company/<int:company_id>')
def view_company_products(company_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("View company products: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('company'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT product_id, product_name, image, cost, description FROM products WHERE brand_id = %s',
            (company_id,)
        )
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('view_company_products.html', products=products)
    except mysql.connector.Error as e:
        logger.error(f"View company products failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('company'))

# Admin reports
@app.route('/all_orders_report')
def all_orders_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    conn = get_db_connection()
    if conn is None:
        logger.error("All orders report: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()['COUNT(*)']
        total_pages = (total_orders + per_page - 1) // per_page
        cursor.execute(
            'SELECT o.order_id, u.username AS user_name, ui.contact, o.order_date AS date, o.total_amount, o.order_status '
            'FROM orders o JOIN users u ON o.user_id = u.user_id JOIN user_info ui ON o.user_id = ui.user_id '
            'LIMIT %s OFFSET %s',
            (per_page, (page - 1) * per_page)
        )
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('all_orders_report.html', orders=orders, total_pages=total_pages, current_page=page, per_page=per_page)
    except mysql.connector.Error as e:
        logger.error(f"All orders report failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/view_order_details/<int:order_id>')
def view_order_details(order_id):
    if 'user_id' not in session:
        flash('Please log in to view order details', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("View order details: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT oi.order_item_id, p.product_name, p.image, p.cost, oi.quantity '
            'FROM orderitems oi JOIN products p ON oi.product_id = p.product_id WHERE oi.order_id = %s',
            (order_id,)
        )
        order_items = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('order_detail.html', order_items=order_items)
    except mysql.connector.Error as e:
        logger.error(f"View order details failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("Cart: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT c.product_id, p.product_name, p.image, p.cost, c.quantity '
            'FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s',
            (user_id,)
        )
        cart_items = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('cart.html', cart_items=cart_items)
    except mysql.connector.Error as e:
        logger.error(f"Cart failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/api/cart')
def api_cart():
    if 'user_id' not in session:
        return jsonify([])
    
    user_id = session['user_id']
    conn = get_db_connection()
    if conn is None:
        logger.error("API cart: No DB connection")
        return jsonify({'error': 'Database connection failed'})
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT p.product_id, p.product_name, p.image, p.cost, c.quantity '
            'FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s',
            (user_id,)
        )
        cart_items = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(cart_items)
    except mysql.connector.Error as e:
        logger.error(f"API cart failed: {e.errno} - {str(e)}")
        conn.close()
        return jsonify({'error': str(e)})

@app.route('/view_product/<int:product_id>')
def view_product(product_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("View product: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('products'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT p.*, c.category_type AS category, b.name AS brand '
            'FROM products p JOIN categories c ON p.category_id = c.category_id JOIN brands b ON p.brand_id = b.brand_id '
            'WHERE p.product_id = %s',
            (product_id,)
        )
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        if product:
            return render_template('view_product.html', product=product)
        else:
            flash('Product not found', 'danger')
            return redirect(url_for('products'))
    except mysql.connector.Error as e:
        logger.error(f"View product failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('products'))

# Admin category management
@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        category_type = request.form['category_type']
        description = request.form['description']
        image = request.files.get('image')  # Optional image
        image_filename = None
        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        os.makedirs(upload_folder, exist_ok=True)
        if image and image.filename:
            image_filename = image.filename
            image.save(os.path.join(upload_folder, image_filename))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Add category: No DB connection")
            flash('Database connection failed', 'danger')
            return redirect(url_for('category_report'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                'INSERT INTO categories (category_type, description, image) VALUES (%s, %s, %s)',
                (category_type, description, image_filename)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Category added successfully', 'success')
            return redirect(url_for('category_report'))
        except mysql.connector.Error as e:
            logger.error(f"Add category failed: {e.errno} - {str(e)}")
            conn.close()
            flash(f'Error adding category: {str(e)}', 'danger')
            return redirect(url_for('category_report'))
    return render_template('add_category.html', category=None)

@app.route('/category_report')
def category_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    conn = get_db_connection()
    if conn is None:
        logger.error("Category report: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) AS total FROM categories')
        total = cursor.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        cursor.execute('SELECT * FROM categories LIMIT %s OFFSET %s', (per_page, (page - 1) * per_page))
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('category_report.html', categories=categories, total_pages=total_pages, current_page=page)
    except mysql.connector.Error as e:
        logger.error(f"Category report failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('index'))

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Edit category: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('category_report'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM categories WHERE category_id = %s', (category_id,))
        category = cursor.fetchone()
        cursor.close()
        conn.close()
        if not category:
            flash('Category not found', 'danger')
            return redirect(url_for('category_report'))
        
        if request.method == 'POST':
            category_type = request.form['category_type']
            description = request.form['description']
            image = request.files.get('image')  # Optional image
            image_filename = category['image']  # Keep existing image
            upload_folder = os.path.join(app.root_path, 'static', 'upload')
            os.makedirs(upload_folder, exist_ok=True)
            if image and image.filename:
                image_filename = image.filename
                image.save(os.path.join(upload_folder, image_filename))
            
            conn = get_db_connection()
            if conn is None:
                logger.error("Edit category: No DB connection")
                flash('Database connection failed', 'danger')
                return redirect(url_for('category_report'))
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE categories SET category_type = %s, description = %s, image = %s WHERE category_id = %s',
                    (category_type, description, image_filename, category_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Category updated successfully', 'success')
                return redirect(url_for('category_report'))
            except mysql.connector.Error as e:
                logger.error(f"Edit category failed: {e.errno} - {str(e)}")
                conn.close()
                flash(f'Error updating category: {str(e)}', 'danger')
                return redirect(url_for('category_report'))
        return render_template('add_category.html', category=category)
    except mysql.connector.Error as e:
        logger.error(f"Fetch category failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('category_report'))

@app.route('/delete_category/<int:category_id>')
def delete_category(category_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Delete category: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('category_report'))
    
    try:
        cursor = conn.cursor()
        # Delete dependent products first
        cursor.execute('DELETE FROM cart WHERE product_id IN (SELECT product_id FROM products WHERE category_id = %s)', (category_id,))
        cursor.execute('DELETE FROM orderitems WHERE product_id IN (SELECT product_id FROM products WHERE category_id = %s)', (category_id,))
        cursor.execute('DELETE FROM products WHERE category_id = %s', (category_id,))
        # Now delete category
        cursor.execute('DELETE FROM categories WHERE category_id = %s', (category_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Category and related products deleted successfully', 'success')
        return redirect(url_for('category_report'))
    except mysql.connector.Error as e:
        logger.error(f"Delete category failed: {e.errno} - {str(e)}")
        conn.close()
        flash(f'Error deleting category: {str(e)}', 'danger')
        return redirect(url_for('category_report'))

@app.route('/category/<int:category_id>')
def view_category(category_id):
    conn = get_db_connection()
    if conn is None:
        logger.error("View category: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('categories'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT p.product_id, p.product_name, p.image, p.cost, p.description FROM products p WHERE p.category_id = %s',
            (category_id,)
        )
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('view_category.html', products=products)
    except mysql.connector.Error as e:
        logger.error(f"View category failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('categories'))

# Admin company management
@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        company_name = request.form['company_name']
        description = request.form['description']
        image = request.files.get('image')  # Optional image
        image_filename = None
        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        os.makedirs(upload_folder, exist_ok=True)
        if image and image.filename:
            image_filename = image.filename
            image.save(os.path.join(upload_folder, image_filename))
        
        conn = get_db_connection()
        if conn is None:
            logger.error("Add company: No DB connection")
            flash('Database connection failed', 'danger')
            return redirect(url_for('company_report'))
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO brands (name, description, image) VALUES (%s, %s, %s)',
                (company_name, description, image_filename)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Company added successfully', 'success')
            return redirect(url_for('company_report'))
        except mysql.connector.Error as e:
            logger.error(f"Add company failed: {e.errno} - {str(e)}")
            conn.close()
            flash(f'Error adding company: {str(e)}', 'danger')
            return redirect(url_for('company_report'))
    return render_template('add_company.html', edit=False)

@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Edit company: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('company_report'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM brands WHERE brand_id = %s', (company_id,))
        company = cursor.fetchone()
        cursor.close()
        conn.close()
        if not company:
            flash('Company not found', 'danger')
            return redirect(url_for('company_report'))
        
        if request.method == 'POST':
            company_name = request.form['company_name']
            description = request.form['description']
            image = request.files.get('image')  # Optional image
            image_filename = company['image']  # Keep existing image
            upload_folder = os.path.join(app.root_path, 'static', 'upload')
            os.makedirs(upload_folder, exist_ok=True)
            if image and image.filename:
                image_filename = image.filename
                image.save(os.path.join(upload_folder, image_filename))
            
            conn = get_db_connection()
            if conn is None:
                logger.error("Edit company: No DB connection")
                flash('Database connection failed', 'danger')
                return redirect(url_for('company_report'))
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE brands SET name = %s, description = %s, image = %s WHERE brand_id = %s',
                    (company_name, description, image_filename, company_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Company updated successfully', 'success')
                return redirect(url_for('company_report'))
            except mysql.connector.Error as e:
                logger.error(f"Edit company failed: {e.errno} - {str(e)}")
                conn.close()
                flash(f'Error updating company: {str(e)}', 'danger')
                return redirect(url_for('company_report'))
        return render_template('add_company.html', company=company, edit=True)
    except mysql.connector.Error as e:
        logger.error(f"Fetch company failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('company_report'))

@app.route('/company_report')
def company_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 3, type=int)
    conn = get_db_connection()
    if conn is None:
        logger.error("Company report: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) FROM brands')
        total_companies = cursor.fetchone()['COUNT(*)']
        total_pages = (total_companies + per_page - 1) // per_page
        cursor.execute('SELECT * FROM brands LIMIT %s OFFSET %s', (per_page, (page - 1) * per_page))
        companies = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('company_report.html', companies=companies, total_pages=total_pages, current_page=page, per_page=per_page)
    except mysql.connector.Error as e:
        logger.error(f"Company report failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('index'))

@app.route('/delete_company/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Delete company: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('company_report'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE product_id IN (SELECT product_id FROM products WHERE brand_id = %s)', (company_id,))
        cursor.execute('DELETE FROM orderitems WHERE product_id IN (SELECT product_id FROM products WHERE brand_id = %s)', (company_id,))
        cursor.execute('DELETE FROM products WHERE brand_id = %s', (company_id,))
        cursor.execute('DELETE FROM brands WHERE brand_id = %s', (company_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Company and related products deleted successfully', 'success')
        return redirect(url_for('company_report'))
    except mysql.connector.Error as e:
        logger.error(f"Delete company failed: {e.errno} - {str(e)}")
        conn.close()
        flash(f'Error deleting company: {str(e)}', 'danger')
        return redirect(url_for('company_report'))

# Admin product management
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Add product: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT brand_id, name FROM brands')
        companies = cursor.fetchall()
        cursor.execute('SELECT category_id, category_type FROM categories')
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        if request.method == 'POST':
            product_name = request.form['product_name']
            brand_id = request.form['company']
            category_id = request.form['category_id']  # Changed from product_type
            cost = request.form['cost']
            description = request.form['description']
            image = request.files.get('image')  # Optional image
            image_filename = None
            upload_folder = os.path.join(app.root_path, 'static', 'upload')
            os.makedirs(upload_folder, exist_ok=True)
            if image and image.filename:
                image_filename = image.filename
                image.save(os.path.join(upload_folder, image_filename))
            
            conn = get_db_connection()
            if conn is None:
                logger.error("Add product: No DB connection")
                flash('Database connection failed', 'danger')
                return redirect(url_for('admin_dashboard'))
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO products (product_name, cost, description, image, category_id, brand_id) '
                    'VALUES (%s, %s, %s, %s, %s, %s)',
                    (product_name, cost, description, image_filename, category_id, brand_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Product added successfully', 'success')
                return redirect(url_for('admin_dashboard'))
            except mysql.connector.Error as e:
                logger.error(f"Add product failed: {e.errno} - {str(e)}")
                conn.close()
                flash(f'Error adding product: {str(e)}', 'danger')
                return redirect(url_for('admin_dashboard'))
        return render_template('add_product.html', companies=companies, categories=categories, product=None, edit=False)
    except mysql.connector.Error as e:
        logger.error(f"Fetch brands/categories failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/product_report')
def product_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    conn = get_db_connection()
    if conn is None:
        logger.error("Product report: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) FROM products')
        total_products = cursor.fetchone()['COUNT(*)']
        total_pages = (total_products + per_page - 1) // per_page
        cursor.execute(
            'SELECT p.*, c.category_type, b.name AS brand_name '
            'FROM products p '
            'JOIN categories c ON p.category_id = c.category_id '
            'JOIN brands b ON p.brand_id = b.brand_id '
            'LIMIT %s OFFSET %s',
            (per_page, (page - 1) * per_page)
        )
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('product_report.html', products=products, total_pages=total_pages, current_page=page, per_page=per_page)
    except mysql.connector.Error as e:
        logger.error(f"Product report failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('index'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Edit product: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('product_report'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM products WHERE product_id = %s', (product_id,))
        product = cursor.fetchone()
        cursor.execute('SELECT brand_id, name FROM brands')
        companies = cursor.fetchall()
        cursor.execute('SELECT category_id, category_type FROM categories')
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('product_report'))
        
        if request.method == 'POST':
            product_name = request.form['product_name']
            brand_id = request.form['company']
            category_id = request.form['category_id']  # Changed from product_type
            cost = request.form['cost']
            description = request.form['description']
            image = request.files.get('image')  # Optional image
            image_filename = product['image']  # Keep existing image
            upload_folder = os.path.join(app.root_path, 'static', 'upload')
            os.makedirs(upload_folder, exist_ok=True)
            if image and image.filename:
                image_filename = image.filename
                image.save(os.path.join(upload_folder, image_filename))
            
            conn = get_db_connection()
            if conn is None:
                logger.error("Edit product: No DB connection")
                flash('Database connection failed', 'danger')
                return redirect(url_for('product_report'))
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE products SET product_name = %s, cost = %s, description = %s, image = %s, category_id = %s, brand_id = %s '
                    'WHERE product_id = %s',
                    (product_name, cost, description, image_filename, category_id, brand_id, product_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Product updated successfully', 'success')
                return redirect(url_for('product_report'))
            except mysql.connector.Error as e:
                logger.error(f"Edit product failed: {e.errno} - {str(e)}")
                conn.close()
                flash(f'Error updating product: {str(e)}', 'danger')
                return redirect(url_for('product_report'))
        return render_template('add_product.html', product=product, companies=companies, categories=categories, edit=True)
    except mysql.connector.Error as e:
        logger.error(f"Fetch product failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('product_report'))

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Delete product: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('product_report'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE product_id = %s', (product_id,))
        cursor.execute('DELETE FROM orderitems WHERE product_id = %s', (product_id,))
        cursor.execute('DELETE FROM products WHERE product_id = %s', (Rqproduct_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product deleted successfully', 'success')
        return redirect(url_for('product_report'))
    except mysql.connector.Error as e:
        logger.error(f"Delete product failed: {e.errno} - {str(e)}")
        conn.close()
        flash(f'Error deleting product: {str(e)}', 'danger')
        return redirect(url_for('product_report'))

@app.route('/user_report')
def user_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    conn = get_db_connection()
    if conn is None:
        logger.error("User report: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) FROM user_info')
        total_users = cursor.fetchone()['COUNT(*)']
        total_pages = (total_users + per_page - 1) // per_page
        cursor.execute(
            'SELECT ui.user_id, ui.contact, ui.image, u.username '
            'FROM user_info ui JOIN users u ON ui.user_id = u.user_id '
            'LIMIT %s OFFSET %s',
            (per_page, (page - 1) * per_page)
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('user_report.html', users=users, total_pages=total_pages, current_page=page, per_page=per_page)
    except mysql.connector.Error as e:
        logger.error(f"User report failed: {e.errno} - {str(e)}")
        conn.close()
        flash('Database error', 'danger')
        return redirect(url_for('login'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn is None:
        logger.error("Delete user: No DB connection")
        flash('Database connection failed', 'danger')
        return redirect(url_for('user_report'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM orderitems WHERE order_id IN (SELECT order_id FROM orders WHERE user_id = %s)', (user_id,))
        cursor.execute('DELETE FROM orders WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM user_info WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User deleted successfully', 'success')
        return redirect(url_for('user_report'))
    except mysql.connector.Error as e:
        logger.error(f"Delete user failed: {e.errno} - {str(e)}")
        conn.close()
        flash(f'Error deleting user: {str(e)}', 'danger')
        return redirect(url_for('user_report'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting app on port {port}")
    app.run(host='0.0.0.0', port=port)