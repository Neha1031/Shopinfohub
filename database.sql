CREATE DATABASE IF NOT EXISTS shopinfo;
USE shopinfo;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS shops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_name VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    shop_photo LONGTEXT,
    address TEXT,
    map_link VARCHAR(500),
    description TEXT,
    user_email VARCHAR(255) NOT NULL,
    is_open BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_email VARCHAR(255) NOT NULL, -- kept for legacy/fallback
    shop_id INT, -- New strict mapping
    product_name VARCHAR(255) NOT NULL,
    product_photo LONGTEXT,
    price DECIMAL(10, 2) NOT NULL,
    details TEXT,
    voice_description TEXT,
    status VARCHAR(100) NOT NULL,
    quantity INT DEFAULT 0,
    weight VARCHAR(50),
    quality VARCHAR(100) DEFAULT 'Standard',
    FOREIGN KEY (shop_email) REFERENCES users(email) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
);
