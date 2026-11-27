import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room
from database import get_db, init_db
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'thriftin_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
socketio = SocketIO(app)

# Track user online
online_users = {}

with app.app_context():
    init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── LANDING ────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))  # sudah login → ke home
    return render_template('landing.html')  # belum login → landing

# ─── AUTH ───────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        email = request.form.get('email', '').strip()
        if len(password) < 6:
            return render_template('register.html', error='Password minimal 6 karakter.')
        if len(username) < 3:
            return render_template('register.html', error='Username minimal 3 karakter.')
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            db.close()
            return render_template('register.html', error='Username sudah dipakai.')
        hashed = generate_password_hash(password)
        db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, hashed))
        db.commit()
        db.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?',
                  (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['avatar'] = user['avatar'] if 'avatar' in user.keys() else ''
            return redirect(url_for('home'))
        return render_template('login.html', error='Username atau password salah.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        online_users.pop(uid, None)
        socketio.emit('seller_status', {'seller_id': uid, 'online': False}, namespace='/')
    session.clear()
    return redirect(url_for('index'))

# ─── HOME ───────────────────────────────────────────

@app.route('/home')
def home():
    category  = request.args.get('category', '')
    location  = request.args.get('location', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    sort      = request.args.get('sort', '')

    db = get_db()
    query  = 'SELECT * FROM products WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)
    if location:
        query += ' AND location = ?'
        params.append(location)
    if min_price:
        query += ' AND price >= ?'
        params.append(int(min_price))
    if max_price:
        query += ' AND price <= ?'
        params.append(int(max_price))

    if sort == 'termurah':
        query += ' ORDER BY price ASC'
    elif sort == 'termahal':
        query += ' ORDER BY price DESC'
    else:
        query += ' ORDER BY created_at DESC'

    per_page = 8
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    total = db.execute(query.replace('SELECT *', 'SELECT COUNT(*)', 1).split(' ORDER BY')[0],
                    params).fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    query += ' LIMIT ? OFFSET ?'
    products = db.execute(query, params + [per_page, (page - 1) * per_page]).fetchall()
    
    wishlist_ids = []
    if 'user_id' in session:
        rows = db.execute('SELECT product_id FROM wishlist WHERE user_id = ?',
                          (session['user_id'],)).fetchall()
        wishlist_ids = [r['product_id'] for r in rows]

    db.close()
    return render_template('index.html',
                           products=products,
                           selected_category=category,
                           selected_location=location,
                           min_price=min_price,
                           max_price=max_price,
                           sort=sort,
                           wishlist_ids=wishlist_ids,
                           page=page,
                           total_pages=total_pages,
                           total=total,)

# ─── SEARCH ─────────────────────────────────────────

@app.route('/search')
def search():
    q  = request.args.get('q', '').strip()
    db = get_db()
    products = []
    if q:
        products = db.execute(
            'SELECT * FROM products WHERE (title LIKE ? OR description LIKE ?) AND status != "sold"',
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    db.close()
    return render_template('search.html', products=products, q=q)

# ─── PRODUK ─────────────────────────────────────────

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        price       = request.form.get('price', 0)
        category    = request.form.get('category', '')
        location    = request.form.get('location', '')
        wa_number   = request.form.get('wa_number', '')
        description = request.form.get('description', '')
        size        = request.form.get('size', '-')
        condition   = request.form.get('condition', 'Baik')
        defect      = request.form.get('defect', '-')
        stock       = int(request.form.get('stock', 1))
        discount    = int(request.form.get('discount', 0))

        image_filename = 'no-image.png'
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        db = get_db()
        db.execute('''
            INSERT INTO products
            (user_id, title, price, discount, category, location,
             description, size, condition, defect, stock, wa_number, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], title, price, discount, category, location,
              description, size, condition, defect, stock, wa_number, image_filename))
        db.commit()
        db.close()
        return redirect(url_for('home'))
    return render_template('add_product.html')

@app.route('/product/<int:id>')
def product_detail(id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    seller         = None
    seller_trusted = False
    seller_fast    = False
    is_wishlisted  = False

    if product:
        seller = db.execute('SELECT * FROM users WHERE id = ?',
                            (product['user_id'],)).fetchone()
        if seller:
            total_done = db.execute('''
                SELECT COUNT(*) as cnt FROM orders
                JOIN products ON orders.product_id = products.id
                WHERE products.user_id = ? AND orders.status = "Selesai"
            ''', (seller['id'],)).fetchone()['cnt']

            avg_row    = db.execute(
                'SELECT AVG(rating) as avg FROM reviews WHERE seller_id = ?',
                (seller['id'],)
            ).fetchone()
            avg_rating = avg_row['avg'] or 0

            msg_count = db.execute('''
                SELECT COUNT(*) as cnt FROM messages
                JOIN products ON messages.product_id = products.id
                WHERE products.user_id = ? AND messages.username != ?
            ''', (seller['id'], seller['username'])).fetchone()['cnt']

            seller_trusted = total_done >= 1 or avg_rating >= 4.0
            seller_fast    = msg_count > 0

        if 'user_id' in session:
            w = db.execute(
                'SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?',
                (session['user_id'], id)
            ).fetchone()
            is_wishlisted = w is not None

    db.close()
    if product is None:
        return redirect(url_for('home'))
    return render_template('product_detail.html',
                           product=product, seller=seller,
                           seller_trusted=seller_trusted,
                           seller_fast=seller_fast,
                           is_wishlisted=is_wishlisted)

@app.route('/product/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ? AND user_id = ?',
                         (id, session['user_id'])).fetchone()
    if product:
        db.execute('DELETE FROM products WHERE id = ?', (id,))
        db.execute('DELETE FROM messages WHERE product_id = ?', (id,))
        db.execute('DELETE FROM orders WHERE product_id = ?', (id,))
        db.commit()
    db.close()
    return redirect(url_for('seller_dashboard'))

@app.route('/product/<int:id>/update_stock', methods=['POST'])
@login_required
def update_stock(id):
    new_stock = int(request.form.get('stock', 1))
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ? AND user_id = ?',
                         (id, session['user_id'])).fetchone()
    if product:
        if new_stock <= 0:
            db.execute('UPDATE products SET stock = 0, status = "sold" WHERE id = ?', (id,))
        else:
            db.execute('UPDATE products SET stock = ?, status = "available" WHERE id = ?',
                       (new_stock, id))
        db.commit()
    db.close()
    return redirect(url_for('product_detail', id=id))

# ─── CHECKOUT ───────────────────────────────────────

@app.route('/checkout/<int:id>', methods=['GET', 'POST'])
@login_required
def checkout(id):
    db      = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if product is None or product['status'] != 'available':
        db.close()
        return redirect(url_for('home'))

    if request.method == 'POST':
        pickup_method  = request.form['pickup_method']
        payment_method = request.form['payment_method']
        schedule       = request.form['schedule']

        db.execute('''
            INSERT INTO orders
            (product_id, buyer_id, payment_method, pickup_method, schedule, status)
            VALUES (?, ?, ?, ?, ?, 'Menunggu Pembayaran')
        ''', (id, session['user_id'], payment_method, pickup_method, schedule))
        db.execute('UPDATE products SET status = "locked" WHERE id = ?', (id,))
        db.commit()

        order        = db.execute(
            'SELECT * FROM orders WHERE product_id = ? ORDER BY id DESC LIMIT 1', (id,)
        ).fetchone()
        product_owner = db.execute(
            'SELECT user_id FROM products WHERE id = ?', (id,)
        ).fetchone()
        db.close()

        socketio.emit('order_notification', {
            'message': 'Pesanan baru masuk untuk: ' + product['title'],
            'order_id': order['id']
        }, to='seller_' + str(product_owner['user_id']), namespace='/')

        return redirect(url_for('order_detail', order_id=order['id']))

    db.close()
    return render_template('checkout.html', product=product)

# ─── ORDER ──────────────────────────────────────────

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    db      = get_db()
    order   = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    product = db.execute('SELECT * FROM products WHERE id = ?',
                         (order['product_id'],)).fetchone()
    db.close()
    show_motivation = order['status'] == 'Selesai'
    is_buyer  = session['user_id'] == order['buyer_id']
    is_seller = product and session['user_id'] == product['user_id']
    return render_template('order_detail.html', order=order, product=product,
                           show_motivation=show_motivation,
                           is_buyer=is_buyer, is_seller=is_seller)

@app.route('/order/<int:order_id>/upload_proof', methods=['POST'])
@login_required
def upload_proof(order_id):
    file = request.files.get('proof')
    if file and allowed_file(file.filename):
        filename = 'proof_' + secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        db.execute('UPDATE orders SET payment_proof = ?, status = "Dibayar" WHERE id = ?',
                   (filename, order_id))
        db.commit()
        db.close()
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/order/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_order(order_id):
    status = request.form['status']
    db     = get_db()
    order  = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))

    if status == 'Selesai':
        product = db.execute('SELECT * FROM products WHERE id = ?',
                             (order['product_id'],)).fetchone()
        if product:
            new_stock = max(0, product['stock'] - 1)
            if new_stock <= 0:
                db.execute('UPDATE products SET stock = 0, status = "sold" WHERE id = ?',
                           (order['product_id'],))
            else:
                db.execute('UPDATE products SET stock = ?, status = "available" WHERE id = ?',
                           (new_stock, order['product_id']))
    elif status == 'Dibatalkan':
        db.execute('UPDATE products SET status = "available" WHERE id = ?',
                   (order['product_id'],))

    db.commit()
    db.close()
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/my_orders')
@login_required
def my_orders():
    db = get_db()
    orders = db.execute('''
        SELECT orders.*, products.title, products.price, products.image,
               products.user_id as seller_id,
               users.username as seller_username,
               users.avatar as seller_avatar
        FROM orders
        JOIN products ON orders.product_id = products.id
        JOIN users ON products.user_id = users.id
        WHERE orders.buyer_id = ?
        ORDER BY orders.created_at DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('my_orders.html', orders=orders)

# ─── SELLER ─────────────────────────────────────────

@app.route('/dashboard')
@login_required
def seller_dashboard():
    db       = get_db()
    products = db.execute(
        'SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    items = []
    for product in products:
        orders = db.execute(
            'SELECT * FROM orders WHERE product_id = ? ORDER BY created_at DESC',
            (product['id'],)
        ).fetchall()
        class Item: pass
        item         = Item()
        item.product = product
        item.orders  = orders
        items.append(item)
    db.close()
    return render_template('seller_dashboard.html', items=items)

@app.route('/seller/<username>')
def seller_profile(username):
    db     = get_db()
    seller = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if seller is None:
        db.close()
        return redirect(url_for('home'))

    products = db.execute(
        'SELECT * FROM products WHERE user_id = ? AND status != "sold" ORDER BY created_at DESC',
        (seller['id'],)
    ).fetchall()

    reviews = db.execute('''
        SELECT reviews.*, users.username as reviewer_name, users.avatar as reviewer_avatar
        FROM reviews
        JOIN users ON reviews.reviewer_id = users.id
        WHERE reviews.seller_id = ?
        ORDER BY reviews.created_at DESC
    ''', (seller['id'],)).fetchall()

    avg_rating = 0
    if reviews:
        avg_rating = sum(r['rating'] for r in reviews) / len(reviews)

    total_done = db.execute('''
        SELECT COUNT(*) as cnt FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE products.user_id = ? AND orders.status = "Selesai"
    ''', (seller['id'],)).fetchone()['cnt']

    msg_count = db.execute('''
        SELECT COUNT(*) as cnt FROM messages
        JOIN products ON messages.product_id = products.id
        WHERE products.user_id = ? AND messages.username != ?
    ''', (seller['id'], username)).fetchone()['cnt']

    is_fast_response = msg_count > 0
    is_trusted       = total_done >= 1 or avg_rating >= 4.0
    is_online        = seller['id'] in online_users

    db.close()
    return render_template('seller_profile.html',
                           seller=seller, products=products,
                           reviews=reviews, avg_rating=round(avg_rating, 1),
                           total_done=total_done,
                           is_fast_response=is_fast_response,
                           is_trusted=is_trusted,
                           is_online=is_online)

@app.route('/seller/<username>/review', methods=['POST'])
@login_required
def submit_review(username):
    db     = get_db()
    seller = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if seller and seller['id'] != session['user_id']:
        try:
            rating = int(request.form.get('rating', 5))
        except ValueError:
            rating = 0
        comment = request.form.get('comment', '').strip()

        pernah_beli = db.execute('''
            SELECT COUNT(*) FROM orders
            JOIN products ON orders.product_id = products.id
            WHERE orders.buyer_id = ? AND products.user_id = ?
              AND orders.status = 'Selesai'
        ''', (session['user_id'], seller['id'])).fetchone()[0]

        sudah_ulas = db.execute(
            'SELECT COUNT(*) FROM reviews WHERE reviewer_id = ? AND seller_id = ?',
            (session['user_id'], seller['id'])
        ).fetchone()[0]

        if 1 <= rating <= 5 and pernah_beli > 0 and sudah_ulas == 0:
            db.execute('''
                INSERT INTO reviews (reviewer_id, seller_id, product_id, rating, comment)
                VALUES (?, ?, 0, ?, ?)
            ''', (session['user_id'], seller['id'], rating, comment))
            db.commit()
    db.close()
    return redirect(url_for('seller_profile', username=username))

# ─── SETTINGS ───────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    db      = get_db()
    user    = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    error   = None
    success = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'profile':
            bio      = request.form.get('bio', '').strip()
            location = request.form.get('location', '').strip()
            db.execute('UPDATE users SET bio = ?, location = ? WHERE id = ?',
                       (bio, location, session['user_id']))
            db.commit()
            success = 'Profil berhasil diperbarui!'
            user = db.execute('SELECT * FROM users WHERE id = ?',
                              (session['user_id'],)).fetchone()

        elif action == 'username':
            new_username = request.form.get('username', '').strip()
            if len(new_username) < 3:
                error = 'Username minimal 3 karakter.'
            else:
                existing = db.execute(
                    'SELECT id FROM users WHERE username = ? AND id != ?',
                    (new_username, session['user_id'])
                ).fetchone()
                if existing:
                    error = 'Username sudah dipakai.'
                else:
                    db.execute('UPDATE users SET username = ? WHERE id = ?',
                               (new_username, session['user_id']))
                    db.commit()
                    session['username'] = new_username
                    success = 'Username berhasil diubah!'
                    user = db.execute('SELECT * FROM users WHERE id = ?',
                                      (session['user_id'],)).fetchone()

        elif action == 'password':
            old_pass = request.form.get('old_password', '')
            new_pass = request.form.get('new_password', '')
            if not check_password_hash(user['password'], old_pass):
                error = 'Password lama salah.'
            elif len(new_pass) < 6:
                error = 'Password baru minimal 6 karakter.'
            else:
                db.execute('UPDATE users SET password = ? WHERE id = ?',
                        (generate_password_hash(new_pass), session['user_id']))
                db.commit()
                success = 'Password berhasil diubah!'

    db.close()
    return render_template('settings.html', user=user, error=error, success=success)

@app.route('/settings/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if file and allowed_file(file.filename):
        filename = 'avatar_' + str(session['user_id']) + '_' + secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db = get_db()
        db.execute('UPDATE users SET avatar = ? WHERE id = ?',
                   (filename, session['user_id']))
        db.commit()
        db.close()
        session['avatar'] = filename
    return redirect(url_for('settings'))

# ─── WISHLIST ───────────────────────────────────────

@app.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    db       = get_db()
    existing = db.execute(
        'SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?',
        (session['user_id'], product_id)
    ).fetchone()
    if existing:
        db.execute('DELETE FROM wishlist WHERE user_id = ? AND product_id = ?',
                   (session['user_id'], product_id))
        in_wishlist = False
    else:
        db.execute('INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)',
                   (session['user_id'], product_id))
        in_wishlist = True
    db.commit()
    db.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'in_wishlist': in_wishlist})
    return redirect(request.referrer or url_for('home'))

@app.route('/wishlist')
@login_required
def my_wishlist():
    db       = get_db()
    products = db.execute('''
        SELECT products.* FROM wishlist
        JOIN products ON wishlist.product_id = products.id
        WHERE wishlist.user_id = ?
        ORDER BY wishlist.created_at DESC
    ''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('wishlist.html', products=products)

# ─── LAPORAN ────────────────────────────────────────

@app.route('/report/<int:product_id>', methods=['GET', 'POST'])
@login_required
def report_product(product_id):
    db      = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        db.close()
        return redirect(url_for('home'))

    seller = db.execute('SELECT * FROM users WHERE id = ?', (product['user_id'],)).fetchone()

    if request.method == 'POST':
        reason = request.form.get('reason', '')
        detail = request.form.get('detail', '').strip()
        db.execute('''
            INSERT INTO reports (reporter_id, product_id, reported_user_id, reason, detail)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], product_id, product['user_id'], reason, detail))
        db.commit()
        db.close()
        return redirect(url_for('product_detail', id=product_id))

    db.close()
    return render_template('report.html', product=product, seller=seller)

# ─── CHAT ───────────────────────────────────────────

@app.route('/chat/<int:product_id>')
@login_required
def chat(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if product is None:
        db.close()
        return redirect(url_for('home'))

    messages = db.execute(
        'SELECT * FROM messages WHERE product_id = ? ORDER BY created_at ASC',
        (product_id,)
    ).fetchall()

    # Ambil data seller produk
    seller = db.execute('SELECT * FROM users WHERE id = ?',
                        (product['user_id'],)).fetchone()

    # Ambil avatar semua user yang ada di chat
    usernames_in_chat = list(set([m['username'] for m in messages] + [session['username']]))
    user_avatars = {}
    for uname in usernames_in_chat:
        u = db.execute('SELECT avatar FROM users WHERE username = ?', (uname,)).fetchone()
        if u:
            user_avatars[uname] = u['avatar'] or ''

    # Avatar user yang sedang login
    me = db.execute('SELECT avatar FROM users WHERE id = ?',
                    (session['user_id'],)).fetchone()
    my_avatar = me['avatar'] if me and me['avatar'] else ''

    db.close()
    return render_template('chat.html',
                           product=product,
                           messages=messages,
                           username=session['username'],
                           seller=seller,
                           user_avatars=user_avatars,
                           my_avatar=my_avatar)

# ─── SOCKETIO ───────────────────────────────────────

@socketio.on('join')
def on_join(data):
    join_room(str(data['product_id']))

@socketio.on('join_seller')
def on_join_seller(data):
    join_room('seller_' + str(data['seller_id']))

@socketio.on('user_online')
def on_user_online(data):
    user_id = data.get('user_id', 0)
    if user_id:
        online_users.setdefault(user_id, set()).add(request.sid)
        socketio.emit('seller_status', {'seller_id': user_id, 'online': True})

@socketio.on('disconnect')
def on_disconnect():
    for uid in list(online_users):
        online_users[uid].discard(request.sid)
        if not online_users[uid]:
            del online_users[uid]
            socketio.emit('seller_status', {'seller_id': uid, 'online': False})

@socketio.on('send_message')
def handle_message(data):
    room       = str(data['product_id'])
    username   = data['username']
    message    = data['message']
    product_id = data['product_id']

    db = get_db()
    db.execute('INSERT INTO messages (product_id, username, message) VALUES (?, ?, ?)',
               (product_id, username, message))
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    db.commit()
    db.close()

    emit('receive_message', {'username': username, 'message': message}, room=room)

    if product and str(product['user_id']) != str(data.get('user_id', '')):
        socketio.emit('chat_notification', {
            'message': username + ' mengirim pesan di: ' + product['title'],
            'product_id': product_id
        }, to='seller_' + str(product['user_id']), namespace='/')

# ─── ERROR HANDLERS ─────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0',
                 port=int(os.environ.get('PORT', 5000)))