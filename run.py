import os
import hmac
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, session
from backend.config import ADMIN_PASSWORD, DATABASE_URL, DB_CONFIG, SECRET_KEY

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.secret_key = SECRET_KEY

def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)

    return wrapped_view

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    conn = psycopg2.connect(
        dbname=DB_CONFIG['dbname'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            is_verified BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS services (
            service_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            image_url TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS time_slots (
            slot_id SERIAL PRIMARY KEY,
            slot_date VARCHAR(20) NOT NULL,
            start_time VARCHAR(20) NOT NULL,
            is_available BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS bookings (
            booking_id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES users(user_id),
            service_id INTEGER REFERENCES services(service_id),
            slot_id INTEGER REFERENCES time_slots(slot_id),
            cleaner_id INTEGER,
            location VARCHAR(150) NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending'
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(booking_id),
            amount NUMERIC(10, 2) NOT NULL,
            method VARCHAR(50) NOT NULL,
            mpesa_receipt VARCHAR(50),
            status VARCHAR(50) DEFAULT 'Completed'
        );

        CREATE TABLE IF NOT EXISTS reviews (
            review_id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(booking_id),
            service_id INTEGER REFERENCES services(service_id),
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clients (
            client_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            location VARCHAR(100) NOT NULL,
            notes TEXT
        );
        """)
        cursor.execute(
            'ALTER TABLE reviews ADD COLUMN IF NOT EXISTS service_id INTEGER REFERENCES services(service_id)'
        )
        
        cursor.execute('SELECT COUNT(*) FROM services')
        count = cursor.fetchone()['count']
        if count == 0:
            cursor.execute("INSERT INTO users (full_name, email, phone, password_hash, role) VALUES ('Admin Owner', 'admin@florasparkle.co.ke', '0712345678', 'hash', 'admin') ON CONFLICT (email) DO NOTHING;")
            cursor.execute("INSERT INTO users (full_name, email, phone, password_hash, role) VALUES ('Cleaner John', 'john@florasparkle.co.ke', '0722334455', 'hash', 'cleaner') ON CONFLICT (email) DO NOTHING;")
            cursor.execute("INSERT INTO users (full_name, email, phone, password_hash, role) VALUES ('Alice Customer', 'alice@gmail.com', '0733445566', 'hash', 'customer') ON CONFLICT (email) DO NOTHING;")

            services_data = [
                ('Office Cleaning', 'Professional cleaning for small and medium offices in Nairobi. Dusting, vacuuming, and desk sanitization.', 3500.00, 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=600&q=80'),
                ('Airbnb Cleaning', 'Quick turnaround cleaning for Airbnb hosts. Linen change, restocking supplies, deep sanitize.', 2500.00, 'https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?auto=format&fit=crop&w=600&q=80'),
                ('Empty House Cleaning', 'Thorough move-in / move-out cleaning for landlords and tenants. Walls, floors, windows, and cupboards.', 5000.00, 'https://images.unsplash.com/photo-1628177142898-93e36e4e3a50?auto=format&fit=crop&w=600&q=80'),
                ('Kitchen Deep Cleaning', 'Grease removal, oven cleaning, fridge sanitization, and tile scrubbing.', 3000.00, 'https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=600&q=80'),
                ('Washroom Cleaning', 'Sanitization, stain removal, disinfection, and deodorizing of all washroom facilities.', 2000.00, 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=600&q=80')
            ]
            for s in services_data:
                cursor.execute("INSERT INTO services (name, description, price, image_url) VALUES (%s, %s, %s, %s)", s)

            cursor.execute("INSERT INTO time_slots (slot_date, start_time, is_available) VALUES ('2026-11-05', '08:00', TRUE)")
            cursor.execute("INSERT INTO time_slots (slot_date, start_time, is_available) VALUES ('2026-11-05', '11:00', FALSE)")
            cursor.execute("INSERT INTO time_slots (slot_date, start_time, is_available) VALUES ('2026-11-05', '14:00', TRUE)")

            cursor.execute("INSERT INTO clients (full_name, email, phone, location, notes) VALUES ('Mary Wanjiku', 'mary@gmail.com', '0712345678', 'Westlands, Nairobi', 'Prefers morning slots') ON CONFLICT (email) DO NOTHING;")

        conn.commit()
        print("PostgreSQL Database connected and initialized successfully.")
    except Exception as e:
        raise RuntimeError(
            f"Could not initialize PostgreSQL database '{DB_CONFIG['dbname']}': {e}"
        ) from e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM services')
    services = cursor.fetchall()
    
    cursor.execute('''
        SELECT r.*, s.name AS service_name
        FROM reviews r
        LEFT JOIN bookings b ON r.booking_id = b.booking_id
        JOIN services s ON s.service_id = COALESCE(r.service_id, b.service_id)
        ORDER BY r.review_id DESC
    ''')
    reviews = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', services=services, reviews=reviews)

@app.route('/reviews', methods=('POST',))
def submit_review():
    try:
        service_id = int(request.form.get('service_id', ''))
        rating = int(request.form.get('rating', ''))
    except ValueError:
        flash('Choose a service and a rating from 1 to 5.', 'error')
        return redirect(url_for('index'))

    comment = request.form.get('comment', '').strip()
    if not 1 <= rating <= 5 or not comment or len(comment) > 1000:
        flash('Enter a review (up to 1000 characters) and a rating from 1 to 5.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT service_id FROM services WHERE service_id = %s', (service_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        flash('Please choose one of the listed services.', 'error')
        return redirect(url_for('index'))

    cursor.execute(
        'INSERT INTO reviews (service_id, rating, comment) VALUES (%s, %s, %s)',
        (service_id, rating, comment)
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash('Thank you for sharing your review!', 'success')
    return redirect(url_for('index'))

@app.route('/booking', methods=('GET', 'POST'))
def booking():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        service_id = request.form['service_id']
        slot_id = request.form['slot_id']
        location = request.form['location']
        payment_method = request.form['payment_method']
        
        cursor.execute('INSERT INTO bookings (customer_id, service_id, slot_id, location, status) VALUES (%s, %s, %s, %s, %s) RETURNING booking_id',
                         (3, service_id, slot_id, location, 'Confirmed'))
        booking_id = cursor.fetchone()['booking_id']
        
        cursor.execute('UPDATE time_slots SET is_available = FALSE WHERE slot_id = %s', (slot_id,))
        
        cursor.execute('SELECT price FROM services WHERE service_id = %s', (service_id,))
        service = cursor.fetchone()
        
        cursor.execute('INSERT INTO payments (booking_id, amount, method, mpesa_receipt, status) VALUES (%s, %s, %s, %s, %s)',
                         (booking_id, service['price'], payment_method, 'MPESA99281' if payment_method=='M-Pesa' else 'CASH', 'Completed'))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Booking locked and payment processed successfully!', 'success')
        return redirect(url_for('index'))
        
    cursor.execute('SELECT * FROM services')
    services = cursor.fetchall()
    cursor.execute('SELECT * FROM time_slots WHERE is_available = TRUE')
    slots = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('booking.html', services=services, slots=slots)

@app.route('/clients', methods=('GET', 'POST'))
@admin_required
def clients():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        location = request.form['location']
        notes = request.form['notes']
        
        try:
            cursor.execute(
                'INSERT INTO clients (full_name, email, phone, location, notes) VALUES (%s, %s, %s, %s, %s)',
                (full_name, email, phone, location, notes)
            )
            conn.commit()
            flash('New client successfully registered!', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error: Email already exists or invalid entry.', 'error')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('clients'))
        
    cursor.execute('SELECT * FROM clients ORDER BY client_id DESC')
    clients_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('clients.html', clients=clients_list)

@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.booking_id, u.full_name as customer_name, s.name as service_name, 
               t.slot_date, t.start_time, b.location, b.status, p.amount, p.method
        FROM bookings b
        JOIN users u ON b.customer_id = u.user_id
        JOIN services s ON b.service_id = s.service_id
        JOIN time_slots t ON b.slot_id = t.slot_id
        JOIN payments p ON b.booking_id = p.booking_id
    """)
    bookings = cursor.fetchall()
    
    cursor.execute("SELECT SUM(amount) as total FROM payments WHERE status='Completed'")
    res = cursor.fetchone()
    total_revenue = res['total'] if res and res['total'] else 0
    
    cursor.execute("SELECT COUNT(*) as count FROM bookings")
    total_bookings = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role='cleaner'")
    pending_cleaners = cursor.fetchone()['count']
    
    cursor.close()
    conn.close()
    return render_template('admin.html', bookings=bookings, total_revenue=total_revenue, total_bookings=total_bookings, pending_cleaners=pending_cleaners)

@app.route('/admin/login', methods=('GET', 'POST'))
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin'))

    if not ADMIN_PASSWORD:
        return render_template('admin_login.html', login_enabled=False), 503

    if request.method == 'POST':
        password = request.form.get('password', '')
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session['is_admin'] = True
            return redirect(url_for('admin'))
        flash('Incorrect password.', 'error')

    return render_template('admin_login.html', login_enabled=True)

@app.route('/admin/logout', methods=('POST',))
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    print("Launching Flora Sparkle Cleaning Website with PostgreSQL at http://127.0.0.1:5000")
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', port=5000)
