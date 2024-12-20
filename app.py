from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Set the absolute path for the database
basedir = os.path.abspath(os.path.dirname(__file__))
# Secret key used for:
# 1. Session Security: Protects user session data from tampering
# 2. Flash Messages: Enables temporary message encryption between page loads
# 3. CSRF Protection: Prevents cross-site request forgery attacks on forms
# 4. Cookie Security: Signs cookies to prevent client-side manipulation
app.config['SECRET_KEY'] = 'dev-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'coffee_shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False  # Never use permanent sessions
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Short session lifetime

# Configure upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Clear sessions on each request
@app.before_request
def clear_session():
    if not request.endpoint:
        return
    # Clear any existing session
    if not current_user.is_authenticated:
        session.clear()
    # Ensure sessions are never permanent
    session.permanent = False

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

    def set_password(self, password):
        self.password = password

    def check_password(self, password):
        return self.password == password

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50), nullable=False, default='drink')  # 'drink' or 'food'

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship('Product')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def flash_message(message, category='info'):
    flash(message, category)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def menu():
    drinks = Product.query.filter_by(category='drink').all()
    foods = Product.query.filter_by(category='food').all()
    return render_template('menu.html', drinks=drinks, foods=foods)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash_message('Username already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, 
                   email=email, 
                   password=password)
        db.session.add(user)
        db.session.commit() # save aldata fe aldatabase
        flash_message('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Clear session when accessing login page
    if request.method == 'GET':
        logout_user()
        session.clear()
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash_message('Please fill in all fields')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=False)  # Never remember sessions
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash_message('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash_message('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id)
        db.session.add(cart_item)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    quantity = request.json.get('quantity', 0)
    if quantity > 0:
        cart_item.quantity = quantity
    else:
        db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/checkout', methods=['GET'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash_message('Your cart is empty', 'warning')
        return redirect(url_for('menu'))
    
    original_total = sum(item.product.price * item.quantity for item in cart_items)
    discount = original_total * 0.20  # 20% discount
    final_total = original_total - discount
    
    return render_template('checkout.html', cart_items=cart_items, 
                         original_total=original_total, 
                         discount=discount, 
                         final_total=final_total)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    payment_method = request.form.get('payment_method')
    
    if payment_method not in ['cash', 'card']:
        flash_message('Invalid payment method', 'danger')
        return redirect(url_for('checkout'))
    
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash_message('Your cart is empty', 'danger')
        return redirect(url_for('menu'))

    original_total = sum(item.product.price * item.quantity for item in cart_items)
    discount = original_total * 0.20  # 20% discount
    final_total = original_total - discount

    # Process the payment with the discounted total
    # Here you would typically integrate with a payment processor
    # For now, we'll just simulate a successful payment
    
    # Clear the cart after successful payment
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    
    flash_message(f'Payment of ${final_total:.2f} processed successfully! (Saved ${discount:.2f} with discount)', 'success')
    return redirect(url_for('menu'))

@app.route('/checkout', methods=['POST'])
@login_required
def checkout_post():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    flash_message('Order placed successfully!')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)  # Forbidden
    users = User.query.all()
    products = Product.query.all()
    cart_items = CartItem.query.all()
    return render_template('admin.html', 
                         users=users, 
                         products=products, 
                         cart_items=cart_items)

@app.route('/add_product', methods=['POST'])
@login_required
def add_product():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)  # Forbidden
    try:
        name = request.form.get('name')
        category = request.form.get('category')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        
        # Handle file upload
        if 'image' not in request.files:
            flash_message('No image file provided', 'danger')
            return redirect(url_for('admin'))
            
        file = request.files['image']
        if file.filename == '':
            flash_message('No selected file', 'danger')
            return redirect(url_for('admin'))
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create upload folder if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            # Save the file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/static/images/{filename}'
        else:
            flash_message('Invalid file type. Allowed types are: png, jpg, jpeg, gif', 'danger')
            return redirect(url_for('admin'))

        # Validate inputs
        if not all([name, category, price >= 0, description]):
            flash_message('Please fill in all fields correctly', 'danger')
            return redirect(url_for('admin'))

        # Create new product
        new_product = Product(
            name=name,
            category=category,
            price=price,
            description=description,
            image_url=image_url
        )

        db.session.add(new_product)
        db.session.commit() # save aldata fe aldatabase
        flash_message(f'Product "{name}" added successfully!', 'success')

    except Exception as e:
        db.session.rollback() # delete alchanges
        flash_message(f'Error adding product: {str(e)}', 'danger')

    return redirect(url_for('admin'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)  # Forbidden
    try:
        # Find the product
        product = Product.query.get_or_404(product_id)
        product_name = product.name

        # Delete related cart items first
        CartItem.query.filter_by(product_id=product_id).delete()
        
        # Delete the product
        db.session.delete(product)
        db.session.commit()
        
        flash_message(f'Product "{product_name}" deleted successfully!', 'success')

    except Exception as e:
        db.session.rollback()
        flash_message(f'Error deleting product: {str(e)}', 'danger')

    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        # Create instance directory if it doesn't exist
        instance_path = os.path.join(basedir, 'instance')
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
            
        # Create tables if they don't exist (don't drop existing tables)
        db.create_all()
        
        # Only add sample data if the database is empty
        if not User.query.first():
            print("Initializing database with sample data...")
        
            db.session.commit()
            print("Initial data loaded successfully!")
        
    app.run(debug=True)
