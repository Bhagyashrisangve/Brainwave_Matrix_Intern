from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import csv
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# ===== Models =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50), default='user')  # 'admin' or 'user'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    category = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    sku = db.Column(db.String(100))
    threshold = db.Column(db.Integer)

# ===== Routes =====
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        else:
            new_user = User(username=username, password=password, role='admin' if username == 'admin' else 'user')
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. You can login now.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        user = User.query.filter_by(username=uname, password=pwd).first()
        if user:
            session['user'] = user.username
            session['role'] = user.role
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    products = Product.query.all()
    low_stock = Product.query.filter(Product.quantity <= Product.threshold).count()
    return render_template('dashboard.html', products=products, low_stock=low_stock)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        new_product = Product(
            name=request.form['name'],
            category=request.form['category'],
            quantity=int(request.form['quantity']),
            price=float(request.form['price']),
            sku=request.form['sku'],
            threshold=int(request.form['threshold'])
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.quantity = int(request.form['quantity'])
        product.price = float(request.form['price'])
        product.sku = request.form['sku']
        product.threshold = int(request.form['threshold'])
        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_product.html', product=product)

@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/reports')
def reports():
    low_stock = Product.query.filter(Product.quantity <= Product.threshold).all()
    return render_template('reports.html', low_stock=low_stock)

@app.route('/export')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'SKU', 'Threshold'])
    products = Product.query.all()
    for p in products:
        writer.writerow([p.name, p.category, p.quantity, p.price, p.sku, p.threshold])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv',
                     as_attachment=True, download_name='inventory_report.csv')

# ===== Run App =====
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
