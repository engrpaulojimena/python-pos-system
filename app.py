from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime, timedelta
import hashlib, json, os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'pos_secret_key_2024'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    conn = get_db()
    c = get_cursor(conn)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'cashier',
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#6366f1'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            low_stock_alert INTEGER DEFAULT 5,
            category_id INTEGER,
            barcode TEXT,
            image_url TEXT,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            receipt_no TEXT UNIQUE NOT NULL,
            cashier_id INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL NOT NULL,
            amount_paid REAL NOT NULL,
            change_due REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'cash',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cashier_id) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transaction_items (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Seed users
    pw = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING",
              ('admin', pw, 'admin', 'Administrator'))
    pw2 = hashlib.sha256('cashier123'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING",
              ('cashier1', pw2, 'cashier', 'Juan Cruz'))

    # New users
    pw3 = hashlib.sha256('Admin@2025'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING",
              ('admin2', pw3, 'admin', 'Admin Two'))
    pw4 = hashlib.sha256('Cash@2025'.encode()).hexdigest()
    c.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING",
              ('cashier2', pw4, 'cashier', 'Cashier Two'))

    # Seed categories
    cats = [('Food & Beverages', '#f59e0b'), ('Electronics', '#6366f1'), ('Clothing', '#ec4899'), ('Household', '#10b981')]
    for cat in cats:
        c.execute("INSERT INTO categories (name, color) VALUES (%s,%s) ON CONFLICT DO NOTHING", cat)

    # Seed products
    products = [
        ('Bottled Water 500ml', 15.00, 8.00, 100, 20, 1),
        ('Rice (1kg)', 55.00, 45.00, 50, 10, 1),
        ('Instant Noodles', 12.00, 8.00, 200, 30, 1),
        ('Soft Drink 1.5L', 75.00, 55.00, 80, 15, 1),
        ('USB Flash Drive 32GB', 350.00, 250.00, 30, 5, 2),
        ('Phone Case', 150.00, 80.00, 50, 8, 2),
        ('T-Shirt (L)', 250.00, 150.00, 40, 5, 3),
        ('Detergent 1kg', 90.00, 65.00, 60, 10, 4),
        ('Shampoo 200ml', 85.00, 60.00, 45, 8, 4),
        ('Chips 100g', 35.00, 22.00, 150, 25, 1),
    ]
    for p in products:
        c.execute("INSERT INTO products (name, price, cost, stock, low_stock_alert, category_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", p)

    conn.commit()
    c.close()
    conn.close()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('pos'))
        return f(*args, **kwargs)
    return decorated

def gen_receipt():
    conn = get_db()
    c = get_cursor(conn)
    c.execute("SELECT COUNT(*) as cnt FROM transactions")
    count = c.fetchone()['cnt']
    c.close()
    conn.close()
    return f"RCP-{datetime.now().strftime('%Y%m%d')}-{count+1:04d}"

# ─── AUTH ───────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u, p = request.form['username'], request.form['password']
        pw = hashlib.sha256(p.encode()).hexdigest()
        conn = get_db()
        c = get_cursor(conn)
        c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, pw))
        user = c.fetchone()
        c.close(); conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            return redirect(url_for('dashboard') if user['role']=='admin' else url_for('pos'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ──────────────────────────────────────────────────────────
@app.route('/')
@admin_required
def dashboard():
    conn = get_db()
    c = get_cursor(conn)
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')

    c.execute("SELECT COALESCE(SUM(total),0) as v FROM transactions WHERE DATE(created_at)=%s", (today,))
    today_sales = c.fetchone()['v']
    c.execute("SELECT COUNT(*) as v FROM transactions WHERE DATE(created_at)=%s", (today,))
    today_txn = c.fetchone()['v']
    c.execute("SELECT COUNT(*) as v FROM products WHERE active=1")
    total_products = c.fetchone()['v']
    c.execute("SELECT COUNT(*) as v FROM products WHERE stock<=low_stock_alert AND active=1")
    low_stock = c.fetchone()['v']

    stats = {'today_sales': today_sales, 'today_txn': today_txn,
             'total_products': total_products, 'low_stock': low_stock}

    c.execute("""
        SELECT DATE(created_at) as day, COALESCE(SUM(total),0) as total, COUNT(*) as txn
        FROM transactions WHERE DATE(created_at) >= %s GROUP BY day ORDER BY day
    """, (week_ago,))
    daily = c.fetchall()

    c.execute("""
        SELECT p.*, c.name as cat_name FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.stock<=p.low_stock_alert AND p.active=1 ORDER BY p.stock LIMIT 10
    """)
    low_stock_items = c.fetchall()

    c.execute("""
        SELECT t.*, u.full_name FROM transactions t
        JOIN users u ON t.cashier_id=u.id ORDER BY t.created_at DESC LIMIT 8
    """)
    recent_txn = c.fetchall()

    c.execute("""
        SELECT ti.product_name, SUM(ti.quantity) as qty, SUM(ti.subtotal) as revenue
        FROM transaction_items ti GROUP BY ti.product_name ORDER BY qty DESC LIMIT 5
    """)
    top_products = c.fetchall()

    c.close(); conn.close()
    return render_template('dashboard.html', stats=stats, daily=daily,
                           low_stock_items=low_stock_items, recent_txn=recent_txn,
                           top_products=top_products)

# ─── POS ────────────────────────────────────────────────────────────────
@app.route('/pos')
@login_required
def pos():
    conn = get_db()
    c = get_cursor(conn)
    c.execute("""
        SELECT p.*, c.name as cat_name, c.color as cat_color FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.active=1 AND p.stock>0 ORDER BY p.name
    """)
    products = c.fetchall()
    c.execute("SELECT * FROM categories")
    categories = c.fetchall()
    c.close(); conn.close()
    return render_template('pos.html', products=products, categories=categories)

@app.route('/pos/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.get_json()
    cart = data.get('cart', [])
    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'})

    conn = get_db()
    c = get_cursor(conn)
    try:
        subtotal = sum(i['price'] * i['qty'] for i in cart)
        discount = float(data.get('discount', 0))
        tax_rate = float(data.get('tax_rate', 0))
        tax = (subtotal - discount) * tax_rate / 100
        total = subtotal - discount + tax
        amount_paid = float(data.get('amount_paid', 0))
        if amount_paid < total:
            return jsonify({'success': False, 'message': 'Insufficient payment'})
        change = amount_paid - total
        receipt_no = gen_receipt()

        c.execute("""
            INSERT INTO transactions (receipt_no, cashier_id, subtotal, discount, tax, total, amount_paid, change_due, payment_method)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (receipt_no, session['user_id'], subtotal, discount, tax, total, amount_paid, change, data.get('payment_method','cash')))
        txn_id = c.fetchone()['id']

        for item in cart:
            c.execute("SELECT * FROM products WHERE id=%s", (item['id'],))
            prod = c.fetchone()
            if not prod or prod['stock'] < item['qty']:
                conn.rollback()
                return jsonify({'success': False, 'message': f"Insufficient stock for {item['name']}"})
            c.execute("INSERT INTO transaction_items (transaction_id, product_id, product_name, quantity, price, subtotal) VALUES (%s,%s,%s,%s,%s,%s)",
                      (txn_id, item['id'], item['name'], item['qty'], item['price'], item['price']*item['qty']))
            c.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (item['qty'], item['id']))

        conn.commit()
        return jsonify({'success': True, 'receipt_no': receipt_no, 'change': change, 'total': total, 'txn_id': txn_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        c.close(); conn.close()

@app.route('/pos/receipt/<int:txn_id>')
@login_required
def receipt(txn_id):
    conn = get_db()
    c = get_cursor(conn)
    c.execute("SELECT t.*, u.full_name FROM transactions t JOIN users u ON t.cashier_id=u.id WHERE t.id=%s", (txn_id,))
    txn = c.fetchone()
    c.execute("SELECT * FROM transaction_items WHERE transaction_id=%s", (txn_id,))
    items = c.fetchall()
    c.close(); conn.close()
    if not txn:
        flash('Transaction not found.', 'error')
        return redirect(url_for('pos'))
    return render_template('receipt.html', txn=txn, items=items)

# ─── INVENTORY ──────────────────────────────────────────────────────────
@app.route('/inventory')
@admin_required
def inventory():
    conn = get_db()
    c = get_cursor(conn)
    c.execute("""
        SELECT p.*, c.name as cat_name, c.color as cat_color FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.active=1 ORDER BY p.name
    """)
    products = c.fetchall()
    c.execute("SELECT * FROM categories")
    categories = c.fetchall()
    c.close(); conn.close()
    return render_template('inventory.html', products=products, categories=categories)

@app.route('/inventory/add', methods=['POST'])
@admin_required
def add_product():
    d = request.form
    conn = get_db()
    c = get_cursor(conn)
    c.execute("INSERT INTO products (name, price, cost, stock, low_stock_alert, category_id, barcode) VALUES (%s,%s,%s,%s,%s,%s,%s)",
              (d['name'], float(d['price']), float(d.get('cost',0)),
               int(d.get('stock',0)), int(d.get('low_stock_alert',5)),
               d.get('category_id') or None, d.get('barcode','')))
    conn.commit(); c.close(); conn.close()
    flash('Product added!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/edit/<int:pid>', methods=['POST'])
@admin_required
def edit_product(pid):
    d = request.form
    conn = get_db()
    c = get_cursor(conn)
    c.execute("UPDATE products SET name=%s, price=%s, cost=%s, stock=%s, low_stock_alert=%s, category_id=%s, barcode=%s WHERE id=%s",
              (d['name'], float(d['price']), float(d.get('cost',0)),
               int(d.get('stock',0)), int(d.get('low_stock_alert',5)),
               d.get('category_id') or None, d.get('barcode',''), pid))
    conn.commit(); c.close(); conn.close()
    flash('Product updated!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/delete/<int:pid>', methods=['POST'])
@admin_required
def delete_product(pid):
    conn = get_db()
    c = get_cursor(conn)
    c.execute("UPDATE products SET active=0 WHERE id=%s", (pid,))
    conn.commit(); c.close(); conn.close()
    flash('Product removed.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/restock/<int:pid>', methods=['POST'])
@admin_required
def restock(pid):
    qty = int(request.form.get('qty', 0))
    conn = get_db()
    c = get_cursor(conn)
    c.execute("UPDATE products SET stock=stock+%s WHERE id=%s", (qty, pid))
    conn.commit(); c.close(); conn.close()
    flash(f'Added {qty} units to stock.', 'success')
    return redirect(url_for('inventory'))

# ─── USERS ──────────────────────────────────────────────────────────────
@app.route('/users')
@admin_required
def users():
    conn = get_db()
    c = get_cursor(conn)
    c.execute("SELECT id, username, role, full_name, created_at FROM users")
    all_users = c.fetchall()
    c.close(); conn.close()
    return render_template('users.html', users=all_users)

@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    d = request.form
    pw = hashlib.sha256(d['password'].encode()).hexdigest()
    conn = get_db()
    c = get_cursor(conn)
    try:
        c.execute("INSERT INTO users (username, password, role, full_name) VALUES (%s,%s,%s,%s)",
                  (d['username'], pw, d['role'], d['full_name']))
        conn.commit()
        flash('User added!', 'success')
    except:
        conn.rollback()
        flash('Username already exists.', 'error')
    finally:
        c.close(); conn.close()
    return redirect(url_for('users'))

@app.route('/users/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    if uid == session['user_id']:
        flash("Cannot delete your own account.", 'error')
        return redirect(url_for('users'))
    conn = get_db()
    c = get_cursor(conn)
    c.execute("DELETE FROM users WHERE id=%s", (uid,))
    conn.commit(); c.close(); conn.close()
    flash('User deleted.', 'success')
    return redirect(url_for('users'))

# ─── REPORTS ────────────────────────────────────────────────────────────
@app.route('/reports')
@admin_required
def reports():
    conn = get_db()
    c = get_cursor(conn)
    date_from = request.args.get('from', (datetime.now()-timedelta(days=29)).strftime('%Y-%m-%d'))
    date_to = request.args.get('to', datetime.now().strftime('%Y-%m-%d'))

    c.execute("""
        SELECT t.*, u.full_name FROM transactions t
        JOIN users u ON t.cashier_id=u.id
        WHERE DATE(t.created_at) BETWEEN %s AND %s
        ORDER BY t.created_at DESC
    """, (date_from, date_to))
    transactions = c.fetchall()

    c.execute("""
        SELECT COUNT(*) as txn_count, COALESCE(SUM(total),0) as total_sales,
               COALESCE(SUM(discount),0) as total_discount,
               COALESCE(AVG(total),0) as avg_sale
        FROM transactions WHERE DATE(created_at) BETWEEN %s AND %s
    """, (date_from, date_to))
    summary = c.fetchone()

    c.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as txn, SUM(total) as total
        FROM transactions WHERE DATE(created_at) BETWEEN %s AND %s
        GROUP BY day ORDER BY day
    """, (date_from, date_to))
    daily = c.fetchall()

    c.execute("""
        SELECT ti.product_name, SUM(ti.quantity) as qty, SUM(ti.subtotal) as revenue
        FROM transaction_items ti
        JOIN transactions t ON ti.transaction_id=t.id
        WHERE DATE(t.created_at) BETWEEN %s AND %s
        GROUP BY ti.product_name ORDER BY revenue DESC LIMIT 10
    """, (date_from, date_to))
    top_items = c.fetchall()

    c.close(); conn.close()
    return render_template('reports.html', transactions=transactions, summary=summary,
                           daily=daily, top_items=top_items, date_from=date_from, date_to=date_to)

# ─── CATEGORIES ─────────────────────────────────────────────────────────
@app.route('/categories')
@admin_required
def categories():
    conn = get_db()
    c = get_cursor(conn)
    c.execute("""
        SELECT c.*, COUNT(p.id) as product_count FROM categories c
        LEFT JOIN products p ON c.id=p.category_id AND p.active=1
        GROUP BY c.id ORDER BY c.name
    """)
    cats = c.fetchall()
    c.close(); conn.close()
    return render_template('categories.html', categories=cats)

@app.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    d = request.form
    conn = get_db()
    c = get_cursor(conn)
    c.execute("INSERT INTO categories (name, color) VALUES (%s,%s)", (d['name'], d.get('color','#6366f1')))
    conn.commit(); c.close(); conn.close()
    flash('Category added!', 'success')
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_category(cid):
    conn = get_db()
    c = get_cursor(conn)
    c.execute("UPDATE products SET category_id=NULL WHERE category_id=%s", (cid,))
    c.execute("DELETE FROM categories WHERE id=%s", (cid,))
    conn.commit(); c.close(); conn.close()
    flash('Category deleted.', 'success')
    return redirect(url_for('categories'))

# ─── API ─────────────────────────────────────────────────────────────────
@app.route('/api/product/<int:pid>')
@login_required
def api_product(pid):
    conn = get_db()
    c = get_cursor(conn)
    c.execute("SELECT * FROM products WHERE id=%s AND active=1", (pid,))
    p = c.fetchone()
    c.close(); conn.close()
    if p: return jsonify(dict(p))
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '')
    conn = get_db()
    c = get_cursor(conn)
    c.execute("""
        SELECT p.*, cat.name as cat_name FROM products p
        LEFT JOIN categories cat ON p.category_id=cat.id
        WHERE p.active=1 AND p.stock>0 AND (p.name ILIKE %s OR p.barcode=%s)
        LIMIT 20
    """, (f'%{q}%', q))
    products = c.fetchall()
    c.close(); conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/debug-db')
def debug_db():
    url = os.environ.get('DATABASE_URL', 'NOT SET')
    masked = url[:40] + '...' if len(url) > 40 else url
    try:
        conn = get_db()
        c = get_cursor(conn)
        c.execute('SELECT version()')
        version = c.fetchone()
        c.close(); conn.close()
        return jsonify({'db_url': masked, 'connected': True, 'version': str(version)})
    except Exception as e:
        return jsonify({'db_url': masked, 'connected': False, 'error': str(e)})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))