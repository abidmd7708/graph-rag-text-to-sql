-- ==========================================
-- RAG + TEXT-TO-SQL DEMO DATABASE
-- ==========================================

-- Clean existing tables if they exist
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;


-- ==========================================
-- CUSTOMERS
-- ==========================================

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL
);


-- ==========================================
-- PRODUCTS
-- ==========================================

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);


-- ==========================================
-- ORDERS
-- ==========================================

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
);


-- ==========================================
-- ORDER ITEMS
-- ==========================================

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,

    CONSTRAINT fk_order
        FOREIGN KEY (order_id)
        REFERENCES orders(id),

    CONSTRAINT fk_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
);


-- ==========================================
-- CUSTOMERS DATA
-- ==========================================

INSERT INTO customers (name, city, email) VALUES
('Rahul Sharma', 'Hyderabad', 'rahul@example.com'),
('Ananya Reddy', 'Bangalore', 'ananya@example.com'),
('Arjun Kumar', 'Hyderabad', 'arjun@example.com'),
('Sneha Rao', 'Chennai', 'sneha@example.com'),
('Vikram Singh', 'Mumbai', 'vikram@example.com'),
('Priya Nair', 'Kochi', 'priya@example.com'),
('Karthik Reddy', 'Hyderabad', 'karthik@example.com'),
('Meera Iyer', 'Bangalore', 'meera@example.com'),
('Rohan Das', 'Kolkata', 'rohan@example.com'),
('Ishita Patel', 'Pune', 'ishita@example.com');


-- ==========================================
-- PRODUCTS DATA
-- ==========================================

INSERT INTO products (name, category, price) VALUES
('Laptop Pro 15', 'Electronics', 75000.00),
('Wireless Mouse', 'Accessories', 1500.00),
('Mechanical Keyboard', 'Accessories', 4500.00),
('4K Monitor', 'Electronics', 32000.00),
('USB-C Hub', 'Accessories', 3500.00),
('Gaming Headset', 'Gaming', 6500.00),
('Gaming Laptop', 'Gaming', 95000.00),
('Webcam HD', 'Electronics', 5500.00),
('Office Chair', 'Furniture', 18000.00),
('Desk Lamp', 'Furniture', 2500.00);


-- ==========================================
-- ORDERS DATA
-- ==========================================

INSERT INTO orders (customer_id, order_date, status) VALUES
(1, '2026-08-01', 'completed'),
(1, '2026-08-15', 'completed'),
(2, '2026-08-03', 'completed'),
(2, '2026-08-20', 'completed'),
(3, '2026-08-05', 'completed'),
(3, '2026-08-18', 'cancelled'),
(4, '2026-08-07', 'completed'),
(5, '2026-08-10', 'completed'),
(5, '2026-08-22', 'completed'),
(6, '2026-08-12', 'completed'),
(7, '2026-08-14', 'completed'),
(7, '2026-08-25', 'completed'),
(8, '2026-08-16', 'completed'),
(9, '2026-08-19', 'completed'),
(10, '2026-08-21', 'completed');


-- ==========================================
-- ORDER ITEMS DATA
-- ==========================================

INSERT INTO order_items (order_id, product_id, quantity) VALUES

-- Rahul
(1, 1, 1),
(1, 2, 2),
(2, 4, 1),

-- Ananya
(3, 7, 1),
(3, 6, 1),
(4, 3, 2),

-- Arjun
(5, 1, 1),
(5, 5, 1),
(6, 2, 1),

-- Sneha
(7, 8, 2),
(7, 2, 1),

-- Vikram
(8, 4, 1),
(8, 3, 1),
(9, 7, 1),

-- Priya
(10, 9, 1),
(10, 10, 2),

-- Karthik
(11, 1, 1),
(11, 6, 1),
(12, 4, 1),

-- Meera
(13, 3, 1),
(13, 5, 2),

-- Rohan
(14, 7, 1),
(14, 2, 1),

-- Ishita
(15, 9, 1),
(15, 10, 1);