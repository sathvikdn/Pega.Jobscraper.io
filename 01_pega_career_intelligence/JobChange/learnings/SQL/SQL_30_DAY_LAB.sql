CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(60) NOT NULL,
    city VARCHAR(60),
    signup_date DATE NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('paid', 'pending', 'refunded')),
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0)
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    line_number INTEGER NOT NULL,
    product_name VARCHAR(60) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, line_number)
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    employee_name VARCHAR(60) NOT NULL,
    department VARCHAR(40) NOT NULL,
    salary NUMERIC(12,2) NOT NULL,
    manager_id INTEGER REFERENCES employees(employee_id)
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(30) NOT NULL
);

INSERT INTO customers VALUES
(1, 'Asha', 'Hyderabad', '2026-01-01'),
(2, 'Bala', 'Chennai', '2026-01-02'),
(3, 'Charu', 'Hyderabad', '2026-01-03'),
(4, 'Dev', NULL, '2026-01-04'),
(5, 'Esha', 'Pune', '2026-01-05'),
(6, 'Farah', 'Pune', '2026-01-06');

INSERT INTO orders VALUES
(101, 1, '2026-01-05', 'paid', 100),
(102, 1, '2026-01-05', 'paid', 200),
(103, 2, '2026-01-07', 'paid', 100),
(104, 2, '2026-02-01', 'refunded', 150),
(105, 3, '2026-02-02', 'pending', 300),
(106, 1, '2026-02-03', 'paid', 50),
(107, 4, '2026-02-04', 'paid', 0),
(108, 3, '2026-02-05', 'paid', 200),
(109, 2, '2026-03-01', 'paid', 200),
(110, 6, '2026-03-02', 'pending', 80);

INSERT INTO order_items VALUES
(101, 1, 'Notebook', 2, 30),
(101, 2, 'Pen', 2, 20),
(102, 1, 'Bag', 1, 200),
(103, 1, 'Notebook', 2, 50),
(104, 1, 'Book', 1, 150),
(105, 1, 'Bag', 1, 300),
(106, 1, 'Pen', 1, 50),
(107, 1, 'Gift', 1, 0),
(108, 1, 'Bag', 1, 180),
(109, 1, 'Book', 2, 100),
(110, 1, 'Pen', 4, 20);

INSERT INTO employees VALUES
(1, 'Mira', 'Engineering', 150, NULL),
(2, 'Nikhil', 'Engineering', 120, 1),
(3, 'Omar', 'Engineering', 120, 1),
(4, 'Pia', 'Engineering', 90, 2),
(5, 'Ravi', 'Sales', 100, 1),
(6, 'Sara', 'Sales', 80, 5),
(7, 'Tara', 'Sales', 80, 5);

INSERT INTO events VALUES
(1, 1, '2026-01-05 09:00:00', 'view'),
(2, 1, '2026-01-05 09:10:00', 'cart'),
(3, 1, '2026-01-05 09:20:00', 'paid'),
(4, 1, '2026-01-05 10:00:00', 'view'),
(5, 2, '2026-01-07 10:00:00', 'view'),
(6, 2, '2026-01-07 10:30:00', 'cart'),
(7, 2, '2026-01-07 11:01:00', 'paid'),
(8, 3, '2026-02-02 12:00:00', 'view'),
(9, 3, '2026-02-02 12:00:00', 'view');
