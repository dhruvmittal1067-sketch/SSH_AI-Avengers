USE defaultdb;


-- Location Tables
CREATE TABLE IF NOT EXISTS countries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS states (
    id INT AUTO_INCREMENT PRIMARY KEY,
    country_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS districts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    state_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY (state_id) REFERENCES states(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    district_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE CASCADE
);

-- Business Categories
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Main Business Table
CREATE TABLE IF NOT EXISTS businesses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    country_id INT NOT NULL,
    state_id INT NOT NULL,
    district_id INT NOT NULL,
    city_id INT NOT NULL,
    description TEXT,
    contact_no VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    website VARCHAR(100),
    status ENUM('Pending', 'Approved', 'Rejected', 'Suspended') DEFAULT 'Pending',
    rating INT DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (country_id) REFERENCES countries(id),
    FOREIGN KEY (state_id) REFERENCES states(id),
    FOREIGN KEY (district_id) REFERENCES districts(id),
    FOREIGN KEY (city_id) REFERENCES cities(id)
);

-- Media Management
CREATE TABLE IF NOT EXISTS business_media (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    file_type VARCHAR(20),
    file_path VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);

-- Seed Initial Data
INSERT IGNORE INTO countries (id, name) VALUES (1, 'INDIA');
INSERT IGNORE INTO states (id, country_id, name) VALUES (1, 1, 'RAJASTHAN'), (2, 1, 'UTTAR PRADESH');
INSERT IGNORE INTO districts (id, state_id, name) VALUES (1, 1, 'JAIPUR'), (2, 2, 'GUTAM BUDDH NAGAR');
INSERT IGNORE INTO cities (id, district_id, name) VALUES (1, 1, 'JAIPUR CITY'), (2, 2, 'NOIDA');

INSERT IGNORE INTO categories (name) VALUES 
('HOTEL'), ('RESTAURANT'), ('TRAVEL AGENCY'), ('TAXI SERVICE'), 
('VEHICLE RENTAL'), ('TOUR GUIDE'), ('HERITAGE SITE'), ('ADVENTURE SPORTS');



USE defaultdb;
CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin (Password: admin123)
-- In production, store SHA-256 or bcrypt hashes. For a hackathon demo, SHA2 works directly in SQL:
INSERT INTO admin_users (username, password_hash) 
VALUES ('admin', SHA2('admin123', 256));


CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin account (Username: admin | Password: admin123)
INSERT INTO admin_users (username, password_hash) 
VALUES ('admin', SHA2('admin123', 256));


-- Add password column to existing businesses table
ALTER TABLE businesses ADD COLUMN password_hash VARCHAR(255) DEFAULT NULL;

-- Table for Business Offers/Deals
CREATE TABLE IF NOT EXISTS business_offers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    discount_percentage INT DEFAULT 0,
    valid_until DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);

-- Table for Business Catalog Services/Items
CREATE TABLE IF NOT EXISTS business_catalog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS category_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    category_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS location_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    requested_type VARCHAR(50),
    location_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
) ENGINE=InnoDB;



-- 1. Create Users Table First
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Create Business Reviews Table
CREATE TABLE IF NOT EXISTS business_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. Create Saved Favorites Table
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    business_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    UNIQUE KEY user_fav_unique (user_id, business_id)
) ENGINE=InnoDB;

-- 4. Create User Search History Table
CREATE TABLE IF NOT EXISTS user_search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    city_name VARCHAR(100),
    category_name VARCHAR(100),
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- 1. Create the missing 'tourists' table
CREATE TABLE IF NOT EXISTS tourists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255),
    points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create the eco-action submissions table (used for Go Green & Earn)
CREATE TABLE IF NOT EXISTS eco_submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tourist_id INT NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    video_path VARCHAR(500) NOT NULL,
    ai_verdict VARCHAR(50),
    ai_confidence FLOAT,
    ai_reasoning TEXT,
    points_suggested INT DEFAULT 0,
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    points_awarded INT DEFAULT 0,
    reviewed_by VARCHAR(100),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tourist_id) REFERENCES tourists(id) ON DELETE CASCADE
);

-- 3. Create the vouchers table (if not already present)
CREATE TABLE IF NOT EXISTS vouchers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    partner_name VARCHAR(255) NOT NULL,
    points_required INT NOT NULL,
    stock INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1
);

-- 4. Create the user search history table
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tourist_id INT NOT NULL,
    city_id INT NOT NULL,
    category_id INT NOT NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tourist_id) REFERENCES tourists(id) ON DELETE CASCADE
);

-- 5. Create the user favorites table
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tourist_id INT NOT NULL,
    business_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tourist_id) REFERENCES tourists(id) ON DELETE CASCADE
);
show tables;

