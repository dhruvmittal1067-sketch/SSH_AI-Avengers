import os
import hashlib
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# --- DATABASE CONNECTION FACTORY ---
def get_db_connection():
    """Returns an active MySQL connection configured for Aiven SSL."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 24500)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        ssl_disabled=False  # Enforces SSL connection for Aiven
    )

# --- AUTO-INITIALIZE SCHEMA & MISSING TABLES ---
def init_db():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Ensure password_hash exists in businesses
        try:
            cur.execute("ALTER TABLE businesses ADD COLUMN password_hash VARCHAR(255) DEFAULT NULL;")
            conn.commit()
        except Exception:
            pass  # Column already exists

        # 2. Ensure business_catalog table exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS business_catalog (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_id INT NOT NULL,
            item_name VARCHAR(150) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            description TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # 3. Ensure business_offers table exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS business_offers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_id INT NOT NULL,
            title VARCHAR(150) NOT NULL,
            description TEXT,
            discount_percentage INT DEFAULT 0,
            valid_until DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # 4. Location Requests table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS location_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_id INT NOT NULL,
            requested_type VARCHAR(50),
            location_name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # 5. Category Requests table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS category_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_id INT NOT NULL,
            category_name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        conn.commit()
    except Exception as e:
        print("Database init warning:", e)
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()

# Run DB initialization automatically
init_db()

# --- LOCATION FETCHERS ---
def fetch_countries():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM countries")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def fetch_states(country_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM states WHERE country_id=%s", (country_id,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def fetch_districts(state_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM districts WHERE state_id=%s", (state_id,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def fetch_cities(district_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM cities WHERE district_id=%s", (district_id,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def fetch_categories():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM categories")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

# --- BUSINESS AUTH & MANAGEMENT ---
def register_business_with_auth(owner_name, b_name, cat_id, country_id, state_id, district_id, city_id, desc, phone, email, website, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
        INSERT INTO businesses 
        (owner_name, business_name, category_id, country_id, state_id, district_id, city_id, description, contact_no, email, website, password_hash, status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """
        cur.execute(query, (owner_name, b_name, cat_id, country_id, state_id, district_id, city_id, desc, phone, email, website, hashed_pw))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print("Registration Error:", e)
        return False
    finally:
        cur.close()
        conn.close()

def verify_business_login(email, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT * FROM businesses WHERE email = %s AND password_hash = %s"
    cur.execute(query, (email, hashed_pw))
    biz = cur.fetchone()
    cur.close()
    conn.close()
    return biz

def update_business_profile(biz_id, b_name, owner_name, phone, website, desc):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "UPDATE businesses SET business_name=%s, owner_name=%s, contact_no=%s, website=%s, description=%s WHERE id=%s"
    cur.execute(query, (b_name, owner_name, phone, website, desc, biz_id))
    conn.commit()
    cur.close()
    conn.close()

def change_business_password(biz_id, new_password):
    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor()
    query = "UPDATE businesses SET password_hash=%s WHERE id=%s"
    cur.execute(query, (hashed_pw, biz_id))
    conn.commit()
    cur.close()
    conn.close()

# --- OFFERS, CATALOG & REQUESTS ---
def add_catalog_item(business_id, item_name, price, desc):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "INSERT INTO business_catalog (business_id, item_name, price, description) VALUES (%s, %s, %s, %s)"
    cur.execute(query, (business_id, item_name, price, desc))
    conn.commit()
    cur.close()
    conn.close()

def add_business_offer(business_id, title, desc, discount, valid_until):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "INSERT INTO business_offers (business_id, title, description, discount_percentage, valid_until) VALUES (%s, %s, %s, %s, %s)"
    cur.execute(query, (business_id, title, desc, discount, valid_until))
    conn.commit()
    cur.close()
    conn.close()

def fetch_business_catalog(business_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM business_catalog WHERE business_id = %s", (business_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def fetch_business_offers(business_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM business_offers WHERE business_id = %s", (business_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def submit_location_request(biz_id, req_type, loc_name):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "INSERT INTO location_requests (business_id, requested_type, location_name) VALUES (%s, %s, %s)"
    cur.execute(query, (biz_id, req_type, loc_name))
    conn.commit()
    cur.close()
    conn.close()

def submit_category_request(biz_id, cat_name):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "INSERT INTO category_requests (business_id, category_name) VALUES (%s, %s)"
    cur.execute(query, (biz_id, cat_name))
    conn.commit()
    cur.close()
    conn.close()

# --- DIRECTORY & ADMIN ---
def search_businesses(city_id, category_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.*, c.name as category_name 
    FROM businesses b
    JOIN categories c ON b.category_id = c.id
    WHERE b.city_id = %s AND b.category_id = %s AND b.status = 'Approved'
    """
    cur.execute(query, (city_id, category_id))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def get_pending_businesses():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.id, b.business_name, b.owner_name, b.contact_no, c.name as category 
    FROM businesses b
    JOIN categories c ON b.category_id = c.id
    WHERE b.status = 'Pending'
    """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def update_status(business_id, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE businesses SET status=%s WHERE id=%s", (status, business_id))
    conn.commit()
    cur.close()
    conn.close()

def update_rating(business_id, rating):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE businesses SET rating=%s WHERE id=%s", (rating, business_id))
    conn.commit()
    cur.close()
    conn.close()

def verify_admin(username, password):
    hashed_input = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT * FROM admin_users WHERE username = %s AND password_hash = %s"
    cur.execute(query, (username, hashed_input))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user is not None

def add_new_admin(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)"
        cur.execute(query, (username, hashed_pw))
        conn.commit()
        return True
    except Exception as e:
        print("Error adding admin:", e)
        return False
    finally:
        cur.close()
        conn.close()

# --- USER AUTHENTICATION ---
def register_user(full_name, email, phone, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "INSERT INTO users (full_name, email, phone, password_hash) VALUES (%s, %s, %s, %s)"
        cur.execute(query, (full_name, email, phone, hashed_pw))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print("User Registration Error:", e)
        return False
    finally:
        cur.close()
        conn.close()

def verify_user_login(email, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT id, full_name, email, phone FROM users WHERE email = %s AND password_hash = %s"
    cur.execute(query, (email, hashed_pw))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

# --- USER FAVORITES & SEARCH HISTORY ---
def add_favorite(user_id, business_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "INSERT IGNORE INTO user_favorites (user_id, business_id) VALUES (%s, %s)"
        cur.execute(query, (user_id, business_id))
        conn.commit()
        return True
    except Exception as e:
        print("Error saving favorite:", e)
        return False
    finally:
        cur.close()
        conn.close()

def remove_favorite(user_id, business_id):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "DELETE FROM user_favorites WHERE user_id = %s AND business_id = %s"
    cur.execute(query, (user_id, business_id))
    conn.commit()
    cur.close()
    conn.close()

def fetch_user_favorites(user_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.*, c.name as category_name 
    FROM user_favorites uf
    JOIN businesses b ON uf.business_id = b.id
    JOIN categories c ON b.category_id = c.id
    WHERE uf.user_id = %s
    """
    cur.execute(query, (user_id,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def save_search_history(user_id, city_name, category_name):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "INSERT INTO user_search_history (user_id, city_name, category_name) VALUES (%s, %s, %s)"
    cur.execute(query, (user_id, city_name, category_name))
    conn.commit()
    cur.close()
    conn.close()

def fetch_user_search_history(user_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT city_name, category_name, searched_at FROM user_search_history WHERE user_id = %s ORDER BY searched_at DESC LIMIT 10"
    cur.execute(query, (user_id,))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

# --- ADMIN EXTENSIONS ---
def fetch_location_requests():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT lr.*, b.business_name 
    FROM location_requests lr
    JOIN businesses b ON lr.business_id = b.id
    WHERE lr.status = 'Pending'
    """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def approve_location_request(req_id, req_type, loc_name, parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if req_type == "City":
            cur.execute("INSERT INTO cities (district_id, name) VALUES (%s, %s)", (parent_id, loc_name))
        elif req_type == "District":
            cur.execute("INSERT INTO districts (state_id, name) VALUES (%s, %s)", (parent_id, loc_name))
        elif req_type == "State":
            cur.execute("INSERT INTO states (country_id, name) VALUES (%s, %s)", (parent_id, loc_name))
            
        cur.execute("UPDATE location_requests SET status = 'Approved' WHERE id = %s", (req_id,))
        conn.commit()
        return True
    except Exception as e:
        print("Error approving location:", e)
        return False
    finally:
        cur.close()
        conn.close()

def fetch_category_requests():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT cr.*, b.business_name 
    FROM category_requests cr
    JOIN businesses b ON cr.business_id = b.id
    WHERE cr.status = 'Pending'
    """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res

def approve_category_request(req_id, cat_name):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (%s)", (cat_name,))
        cur.execute("UPDATE category_requests SET status = 'Approved' WHERE id = %s", (req_id,))
        conn.commit()
        return True
    except Exception as e:
        print("Error approving category:", e)
        return False
    finally:
        cur.close()
        conn.close()

def fetch_all_businesses():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.id, b.business_name, b.owner_name, b.contact_no, b.status, b.rating, c.name as category 
    FROM businesses b
    JOIN categories c ON b.category_id = c.id
    ORDER BY b.id DESC
    """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res
