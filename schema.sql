CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS SETOF json
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY EXECUTE query;
END;
$$;

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(100),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    credit_card_number VARCHAR(20),
    credit_card_expiry VARCHAR(10),
    credit_card_cvv VARCHAR(4),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending',
    payment_method VARCHAR(50),
    payment_details TEXT,
    shipping_address TEXT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_status VARCHAR(50) DEFAULT 'processing'
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    product_name VARCHAR(200),
    quantity INTEGER NOT NULL,
    price_at_time DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password, email, credit_card_number, credit_card_cvv, is_admin) VALUES
('admin', 'admin123', 'admin@example.com', '4111-1111-1111-1111', '123', TRUE);

INSERT INTO products (name, description, price, category, stock_quantity) VALUES
('Premium Headphones', 'Wireless noise cancelling headphones', 199.99, 'Electronics', 50),
('Smart Watch', 'Fitness tracker with GPS and heart rate', 299.99, 'Electronics', 30),
('Cotton T-Shirt', '100% organic cotton t-shirt', 29.99, 'Clothing', 100),
('Water Bottle', 'Stainless steel insulated water bottle', 24.99, 'Home', 75),
('Mechanical Keyboard', 'RGB gaming mechanical keyboard', 149.99, 'Electronics', 25),
('Yoga Mat', 'Non-slip premium yoga mat', 39.99, 'Sports', 60),
('Coffee Maker', '12-cup programmable coffee maker', 89.99, 'Home', 20),
('Bluetooth Speaker', 'Waterproof portable bluetooth speaker', 79.99, 'Electronics', 45);
