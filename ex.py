from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
import stripe
from flask_mail import Mail, Message
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'panasabotlasreenivas@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'qlxxgqilaexieurn'  # Replace with your App Password
mail = Mail(app)

# Set your secret key. Remember to switch to your live secret key in production!
# See your keys here: https://dashboard.stripe.com/apikeys
stripe.api_key = 'sk_test_51QkgcEC4jul9TxeyUqx9asajB3S1xzcCW3TIoFcSVcplhduCU1G2AOrZEIQaeGUVBkde2JnC1qx8147RLkv9syNx00EaeoMf7n'  # Replace with your actual Stripe secret key



# Generate and send OTP
def send_otp(email):
    otp = random.randint(100000, 999999)
    msg = Message('Your OTP', sender='panasabotlasreenivas@gmail.com', recipients=[email])
    msg.body = f'Your OTP is {otp}'
    mail.send(msg)
    return otp





# Database connection function
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Seenu@123',
        database='ecommerce'
    )
    return conn






# User authentication route, view for login
# User authentication route, view for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        
        # Check if the email exists in the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM user_info WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.fetchall()  # Ensure all results are read
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
    return render_template('login.html')



@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if int(entered_otp) == session.get('otp'):
            email = session.get('email')
            
            # Fetch user details from the database
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT u.role, u.username, u.user_id
                FROM users u
                JOIN user_info ui ON u.user_id = ui.user_id
                WHERE ui.email = %s
            ''', (email,))
            user = cursor.fetchone()
            cursor.fetchall()  # Ensure all results are read
            cursor.close()
            conn.close()
            
            if user:
                # Set session variables
                session['role'] = user['role']
                session['username'] = user['username']
                session['user_id'] = user['user_id']
                
                flash('Login successful', 'success')
                
                # Redirect based on user role
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('User not found', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid OTP', 'danger')
            return redirect(url_for('login'))
    return render_template('verify_otp.html')





# Main route it will launch the landing page
@app.route('/')
def index():
    print("=================Render's into index =================Now your at home page")
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

        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = 'panasabotlasreenivas@gmail.com'  # Replace with your email
        msg['Subject'] = subject
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('panasabotlasreenivas@gmail.com', 'qlxxgqilaexieurn')  # Replace with your email and App Password
            text = msg.as_string()
            server.sendmail(email, 'panasabotlasreenivas@gmail.com', text)  # Replace with your email
            server.quit()
            flash('Message sent successfully', 'success')
        except Exception as e:
            flash(f'An error occurred while sending the message: {str(e)}', 'danger')

        return redirect(url_for('contact_us'))
    return render_template('contact_us.html')



@app.route('/logout')
def logout():
    session.clear()  # Clear the entire session
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))



@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):

    # print (f'=====================user_id===================== {session["user_id"]}---{session["username"]}==============')
    if 'user_id' not in session:
        flash('Please log in to add items to your cart', 'danger')
        # print(f"==============={session['user_id']}")
        return redirect(url_for('login'))
    
    print(f"==============={session['user_id']}============================")
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if the product is already in the cart
    cursor.execute('SELECT * FROM Cart WHERE user_id = %s AND product_id = %s', (user_id, product_id))
    cart_item = cursor.fetchone()

    if cart_item:
        # If the product is already in the cart, update the quantity
        cursor.execute('UPDATE Cart SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s', (user_id, product_id))
    else:
        # If the product is not in the cart, add it to the cart
        cursor.execute('INSERT INTO Cart (user_id, product_id, quantity) VALUES (%s, %s, %s)', (user_id, product_id, 1))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Product added to cart successfully', 'success')
    return redirect(url_for('cart'))


@app.route('/api/remove_from_cart/<int:product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False})

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Cart WHERE user_id = %s AND product_id = %s', (user_id, product_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': True})





#user dashboard view function to launch the user dashboard page
@app.route('/user_dashboard')
def user_dashboard():
    print("=================Render's into user_dashboard =================Now your at user dashboard page")
    print("--------------------USER DASHBOARD----------------------")
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'danger')
        return redirect(url_for('login'))
    print (f'=====================user_id===================== {session["user_id"]}')
    return render_template('user_dashboard.html')

#admin dashboard view function to launch the admin dashboard page
@app.route('/admin_dashboard')
def admin_dashboard():
    print("=================Render's into admin_dashboard =================Now your at admin dashboard page")
    print("--------------------ADMIN DASHBOARD----------------------")
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    return render_template('admin_dashboard.html')

#view function for the change password page
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    print("--------------------CHANGE PASSWORD -------------------------")
    if 'user_id' not in session:
        flash('Please log in to change your password', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
        #IT WILL CHECKS NEW PASSWORD AND CONFIRM PASSWORD IS MATCHING OR NOT

        if new_password != confirm_new_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('change_password'))

        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT password FROM Users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if user and user['password'] == current_password:
            cursor.execute('UPDATE Users SET password = %s WHERE user_id = %s', (new_password, user_id))
            #IT WILL UPDATE THE NEW PASSWORD IN THE DATABASE OF USER 
            conn.commit()
            flash('Password changed successfully', 'success')
        else:
            flash('Current password is incorrect', 'danger')

        cursor.close()
        conn.close()

        return redirect(url_for('change_password'))

    return render_template('change_password.html')



# VIEW FUNCTION FOR THE REGISTER PAGE 

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
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image_path = os.path.join(upload_folder, image_filename)
        
        # Ensure the directory exists before saving the file
        os.makedirs(upload_folder, exist_ok=True)
        image.save(image_path)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('INSERT INTO users (username, password, role) VALUES (%s, %s, %s)', (username, password, role))
        user_id = cursor.lastrowid
        cursor.execute('INSERT INTO user_info (user_id, contact, email, date_of_birth, address, city, state, country, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)', (user_id, contact, email, date_of_birth, address, city, state, country, image_filename))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Registration successful', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')





#IT WILL REDIRCTED TO PRODUCT PAGE 
@app.route('/products')
def products():
    
    return render_template('products.html')




@app.route('/account_details')
def account_details():
    if 'user_id' not in session:
        flash('Please log in to view your account details', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT u.username, ui.email, ui.contact, ui.date_of_birth, ui.address, ui.city, ui.state, ui.country, ui.image
        FROM users u
        JOIN user_info ui ON u.user_id = ui.user_id
        WHERE u.user_id = %s
    ''', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('account_details.html', user=user)



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
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    image_filename = None
    if image:
        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        UPDATE users u
        JOIN user_info ui ON u.user_id = ui.user_id
        SET u.username = %s, ui.email = %s, ui.contact = %s, ui.date_of_birth = %s, ui.address = %s, ui.city = %s, ui.state = %s, ui.country = %s
        WHERE u.user_id = %s
    ''', (username, email, contact, date_of_birth, address, city, state, country, user_id))

    if image_filename:
        cursor.execute('UPDATE user_info SET image = %s WHERE user_id = %s', (image_filename, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Account details updated successfully', 'success')
    return redirect(url_for('account_details'))




#it will show the order details of user after completing payment of order
@app.route('/order_details')
def order_details():
    if 'user_id' not in session:
        print(f"---------------{session['user_id']}")
        flash('Please log in to view your orders', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    print(f"---------------{session['user_id']}--------------------")
    print(f"---------------{session['username']}-------------------")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT oi.order_item_id, p.product_name, p.image, p.cost, oi.quantity
        FROM OrderItems oi
        JOIN Products p ON oi.product_id = p.product_id
        JOIN Orders o ON oi.order_id = o.order_id
        WHERE o.user_id = %s
    ''', (user_id,))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('order_detail.html', orders=orders)

#this place order view function  will redirects to payment page from the cart page 
@app.route('/place_order')
def place_order():
    if 'user_id' not in session:
        flash('Please log in to place an order', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT SUM(p.cost * c.quantity) AS total_amount
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    ''', (user_id,))
    total_amount = cursor.fetchone()['total_amount']
    cursor.close()
    conn.close()

    return render_template('place_order.html', total_amount=total_amount)



#this view function display the payment page and after payment is done it will nagivate to the order detail page
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
        flash('Payment verification failed', 'danger')
        return redirect(url_for('cart'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert order into Orders table
    cursor.execute('INSERT INTO Orders (user_id, total_amount) VALUES (%s, %s)', (user_id, checkout_session.amount_total / 100))
    order_id = cursor.lastrowid

    # Insert order items into OrderItems table
    cursor.execute('''
        INSERT INTO OrderItems (order_id, product_id, quantity, price)
        SELECT %s, Cart.product_id, Cart.quantity, Products.cost
        FROM Cart
        JOIN Products ON Cart.product_id = Products.product_id
        WHERE Cart.user_id = %s
    ''', (order_id, user_id))

    # Clear the cart
    cursor.execute('DELETE FROM Cart WHERE user_id = %s', (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Payment successful and order placed', 'success')
    return redirect(url_for('order_details'))




@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'user_id' not in session:
        flash('Please log in to place an order', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.product_id, p.product_name, p.cost, c.quantity
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    ''', (user_id,))
    cart_items = cursor.fetchall()
    cursor.close()
    conn.close()

    line_items = []
    for item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['product_name'],
                },
                'unit_amount': int(item['cost'] * 100),  # Stripe expects the amount in cents
            },
            'quantity': item['quantity'],
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('process_payment', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cart', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403
    


#this view function displays the  all products in the products page through javaScript by using the fetch function
@app.route('/api/products')
def api_products():
    search_query = request.args.get('search', '')
    limit = request.args.get('limit', type=int)  # Optional limit parameter

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if search_query:
        if limit:
            cursor.execute('''
                SELECT * FROM Products
                WHERE product_name LIKE %s OR description LIKE %s
                LIMIT %s
            ''', (f'%{search_query}%', f'%{search_query}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM Products
                WHERE product_name LIKE %s OR description LIKE %s
            ''', (f'%{search_query}%', f'%{search_query}%'))
    else:
        if limit:
            cursor.execute('SELECT * FROM Products LIMIT %s', (limit,))
        else:
            cursor.execute('SELECT * FROM Products')
    
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(products) 


@app.route('/api/categories')
def api_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Categories')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(categories)

@app.route('/categories')
def categories():
    return render_template('category.html')

@app.route('/api/companies')
def api_companies():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Brands')
    companies = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(companies)

@app.route('/company')
def company():
    return render_template('company.html')


@app.route('/company/<int:company_id>')
def view_company_products(company_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT product_id, product_name, image, cost, description
        FROM Products 
        WHERE company = %s
    ''', (company_id,))
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_company_products.html', products=products)


@app.route('/all_orders_report')
def all_orders_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) FROM Orders')
    total_orders = cursor.fetchone()['COUNT(*)']
    total_pages = (total_orders + per_page - 1) // per_page

    cursor.execute('''
        SELECT o.order_id, u.username AS user_name, ui.contact, o.order_date AS date, o.total_amount, o.order_status
        FROM Orders o
        JOIN users u ON o.user_id = u.user_id
        JOIN user_info ui ON o.user_id = ui.user_id
        LIMIT %s OFFSET %s
    ''', (per_page, (page - 1) * per_page))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('all_orders_report.html', orders=orders, total_pages=total_pages, current_page=page, per_page=per_page)


@app.route('/view_order_details/<int:order_id>')
def view_order_details(order_id):
    # print (f'=====================user_id===================== {session["user_id"]}---{session["username"]}==============')
    if 'user_id' not in session:
        flash('Please log in to view order details', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT oi.order_item_id, p.product_name, p.image, p.cost, oi.quantity
        FROM OrderItems oi
        JOIN Products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    ''', (order_id,))
    order_items = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('order_detail.html', order_items=order_items)







@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT c.product_id, p.product_name, p.image, p.cost, c.quantity
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    ''', (user_id,))
    cart_items = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('cart.html', cart_items=cart_items)



@app.route('/api/cart')
def api_cart():
    if 'user_id' not in session:
        return jsonify([])

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.product_id, p.product_name, p.image, p.cost, c.quantity
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    ''', (user_id,))
    cart_items = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(cart_items)


# @app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
# def remove_from_cart(product_id):
#     if 'user_id' not in session:
#         flash('Please log in to remove items from your cart', 'danger')
#         return redirect(url_for('login'))

#     user_id = session['user_id']
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute('DELETE FROM Cart WHERE user_id = %s AND product_id = %s', (user_id, product_id))
#     conn.commit()
#     cursor.close()
#     conn.close()

#     flash('Product removed from cart successfully', 'success')
#     return redirect(url_for('cart'))










@app.route('/view_product/<int:product_id>')
def view_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT p.*, c.category_type AS category, b.name AS brand FROM Products p JOIN Categories c ON p.category_id = c.category_id JOIN Brands b ON p.brand_id = b.brand_id WHERE p.product_id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        return render_template('view_product.html', product=product)
    else:
        flash('Product not found', 'danger')
        return redirect(url_for('products'))
    


@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    category_id = request.args.get('category_id')
    category = None

    if category_id:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Categories WHERE category_id = %s', (category_id,))
        category = cursor.fetchone()
        cursor.close()
        conn.close()

    if request.method == 'POST':
        category_type = request.form['category_type']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join('static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if category:
            cursor.execute('UPDATE Categories SET category_type = %s, description = %s, image = %s WHERE category_id = %s',
                           (category_type, description, image_filename, category_id))
        else:
            cursor.execute('INSERT INTO Categories (category_type, description, image) VALUES (%s, %s, %s)',
                           (category_type, description, image_filename))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Category saved successfully', 'success')
        return redirect(url_for('category_report'))
    return render_template('add_category.html', category=category)


@app.route('/category_report')
def category_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) AS total FROM Categories')
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page

    cursor.execute('SELECT * FROM Categories LIMIT %s OFFSET %s', (per_page, (page - 1) * per_page))
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('category_report.html', categories=categories, total_pages=total_pages, current_page=page)






@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Categories WHERE category_id = %s', (category_id,))
    category = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        category_type = request.form['category_type']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('UPDATE Categories SET category_type = %s, description = %s, image = %s WHERE category_id = %s',
                       (category_type, description, image_filename, category_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Category updated successfully', 'success')
        return redirect(url_for('category_report'))

    return render_template('add_category.html', category=category)

@app.route('/delete_category/<int:category_id>')
def delete_category(category_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('DELETE FROM Categories WHERE category_id = %s', (category_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Category deleted successfully', 'success')
    return redirect(url_for('category_report'))

@app.route('/category/<int:category_id>')
def view_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.product_id, p.product_name, p.image, p.cost, p.description
        FROM Products p
        WHERE p.category_id = %s
    ''', (category_id,))
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_category.html', products=products)

@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        company_name = request.form['company_name']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('INSERT INTO Brands (name, description, image) VALUES (%s, %s, %s)',
                       (company_name, description, image_filename))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Company added successfully', 'success')
        return redirect(url_for('company_report'))

    return render_template('add_company.html', edit=False)

@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Brands WHERE brand_id = %s', (company_id,))
    company = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        company_name = request.form['company_name']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('UPDATE Brands SET brand_name = %s, description = %s, image = %s WHERE brand_id = %s',
                       (company_name, description, image_filename, company_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Company updated successfully', 'success')
        return redirect(url_for('company_report'))

    return render_template('add_company.html', company=company, edit=True)





@app.route('/company_report')
def company_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 3, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) FROM Brands')
    total_companies = cursor.fetchone()['COUNT(*)']
    total_pages = (total_companies + per_page - 1) // per_page

    cursor.execute('SELECT * FROM Brands LIMIT %s OFFSET %s', (per_page, (page - 1) * per_page))
    companies = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('company_report.html', companies=companies, total_pages=total_pages, current_page=page, per_page=per_page)


@app.route('/delete_company/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all product IDs related to the company
    cursor.execute('SELECT product_id FROM Products WHERE brand_id = %s', (company_id,))
    product_ids = cursor.fetchall()

    # Delete related records in the cart table
    for product_id in product_ids:
        cursor.execute('DELETE FROM Cart WHERE product_id = %s', (product_id['product_id'],))

    # Delete related records in the products table
    cursor.execute('DELETE FROM Products WHERE brand_id = %s', (company_id,))

    # Delete the company
    cursor.execute('DELETE FROM Brands WHERE brand_id = %s', (company_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Company deleted successfully', 'success')
    return redirect(url_for('company_report'))






@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Brands')
    companies = cursor.fetchall()
    cursor.execute('SELECT * FROM Categories')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        product_name = request.form['product_name']
        company_id = request.form['company']
        product_type = request.form['product_type']
        cost = request.form['cost']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join('static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('INSERT INTO Products (product_name, company, product_type, cost, description, image, category_id, brand_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                       (product_name, company_id, product_type, cost, description, image_filename, product_type, company_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Product added successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html', companies=companies, categories=categories)


@app.route('/product_report')
def product_report():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) FROM Products')
    total_products = cursor.fetchone()['COUNT(*)']
    total_pages = (total_products + per_page - 1) // per_page

    cursor.execute('SELECT * FROM Products LIMIT %s OFFSET %s', (per_page, (page - 1) * per_page))
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('product_report.html', products=products, total_pages=total_pages, current_page=page, per_page=per_page)




@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Products WHERE product_id = %s', (product_id,))
    product = cursor.fetchone()

    cursor.execute('SELECT brand_id, name FROM Brands')
    companies = cursor.fetchall()

    cursor.execute('SELECT category_id, category_type FROM Categories')
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.method == 'POST':
        product_name = request.form['product_name']
        company_id = request.form['company']
        product_type = request.form['product_type']
        cost = request.form['cost']
        description = request.form['description']
        image = request.files['image']

        upload_folder = os.path.join(app.root_path, 'static', 'upload')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        image_filename = image.filename
        image.save(os.path.join(upload_folder, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('UPDATE Products SET product_name = %s, company = %s, product_type = %s, cost = %s, description = %s, image = %s WHERE product_id = %s',
                       (product_name, company_id, product_type, cost, description, image_filename, product_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Product updated successfully', 'success')
        return redirect(url_for('product_report'))

    return render_template('add_product.html', product=product, companies=companies, categories=categories, edit=True)







@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Products WHERE product_id = %s', (product_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Product deleted successfully', 'success')
    return redirect(url_for('product_report'))

@app.route('/user_report')
def user_report():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) FROM user_info')
    total_users = cursor.fetchone()['COUNT(*)']
    total_pages = (total_users + per_page - 1) // per_page

    cursor.execute('''
        SELECT ui.user_id, ui.contact, ui.image, u.username
        FROM user_info ui
        JOIN users u ON ui.user_id = u.user_id
        LIMIT %s OFFSET %s
    ''', (per_page, (page - 1) * per_page))
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('user_report.html', users=users, total_pages=total_pages, current_page=page, per_page=per_page)

# @app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
# def edit_user(user_id):
#     if 'user_id' not in session or session.get('role') != 'admin':
#         flash('Access denied', 'danger')
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     if request.method == 'POST':
#         username = request.form['username']
#         mobile = request.form['mobile']
#         cursor.execute('UPDATE Users SET username = %s, contact = %s WHERE user_id = %s', (username, mobile, user_id))
#         conn.commit()
#         flash('User updated successfully', 'success')
#         return redirect(url_for('user_report'))

#     cursor.execute('SELECT user_id, username FROM Users WHERE user_id = %s', (user_id,))
#     user = cursor.fetchone()
#     cursor.close()
#     conn.close()

#     return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete related records in the cart table
    cursor.execute('DELETE FROM Cart WHERE user_id = %s', (user_id,))

    # Delete related records in the user_info table
    cursor.execute('DELETE FROM user_info WHERE user_id = %s', (user_id,))

    # Delete the user
    cursor.execute('DELETE FROM Users WHERE user_id = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash('User deleted successfully', 'success')
    return redirect(url_for('user_report'))

#user authentication route, view  for login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     print("=================Render's into login =================Now your at login page")
#     print("----------------LOGIN PAGE------------- ")
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         print(f"==========================={password}=======================password==========")
#         print(f'============================{username}===========================username===========')

#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
#         user = cursor.fetchone()
#         cursor.close()
#         conn.close()

#         if user and user['password'] == password:
#             session['role'] = user['role']
#             session['username'] = user['username']
#             session['user_id'] = user['user_id']
#             flash('Login successful', 'success')
#             print(f'=============={username}========={password}============{session["role"]}==========')
#             if user['role'] == 'admin':
#                 return redirect(url_for('admin_dashboard'))
#                 #if user role is admin it will nagivate to the admin dashboard view function
#             else:
#                 return redirect(url_for('user_dashboard'))
#                 #if user is consumer it will redirect to the user dashboard view function
#         else:
#             flash('Invalid credentials', 'danger')
#             return redirect(url_for('login'))
        
    return render_template('login.html')



if __name__ == '__main__':
    app.run(debug=True)