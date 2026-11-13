SELECT order_id, amount FROM orders
WHERE status = 'paid' AND order_date >= '2026-01-01' AND order_date < '2026-02-01'
ORDER BY order_id;

SELECT COUNT(*) AS customers, COUNT(city) AS known_cities, COUNT(DISTINCT city) AS distinct_cities
FROM customers;

SELECT customer_id, customer_name FROM customers WHERE city IS NULL ORDER BY customer_id;

SELECT status, COUNT(*) AS order_count, SUM(amount) AS total_amount
FROM orders GROUP BY status ORDER BY status;

SELECT customer_id, SUM(amount) AS paid_revenue FROM orders
WHERE status = 'paid' GROUP BY customer_id HAVING SUM(amount) >= 300 ORDER BY customer_id;

SELECT customer.customer_id, COUNT(purchase.order_id) AS paid_orders,
       COALESCE(SUM(purchase.amount), 0) AS paid_revenue
FROM customers customer
LEFT JOIN orders purchase ON purchase.customer_id = customer.customer_id AND purchase.status = 'paid'
GROUP BY customer.customer_id ORDER BY customer.customer_id;

SELECT customer.customer_id FROM customers customer
WHERE NOT EXISTS (SELECT 1 FROM orders purchase WHERE purchase.customer_id = customer.customer_id)
ORDER BY customer.customer_id;

SELECT customer.customer_id FROM customers customer
WHERE NOT EXISTS (SELECT 1 FROM orders purchase WHERE purchase.customer_id = customer.customer_id AND purchase.status = 'paid')
ORDER BY customer.customer_id;

SELECT customer.customer_id FROM customers customer
WHERE EXISTS (SELECT 1 FROM orders purchase WHERE purchase.customer_id = customer.customer_id AND purchase.status = 'paid')
ORDER BY customer.customer_id;

SELECT employee.employee_id, manager.employee_name AS manager_name
FROM employees employee LEFT JOIN employees manager ON employee.manager_id = manager.employee_id
ORDER BY employee.employee_id;

SELECT SUM(amount) AS paid_revenue FROM orders WHERE status = 'paid';

WITH item_totals AS (
    SELECT order_id, SUM(quantity * unit_price) AS item_total FROM order_items GROUP BY order_id
)
SELECT purchase.order_id, purchase.amount, totals.item_total
FROM orders purchase LEFT JOIN item_totals totals ON totals.order_id = purchase.order_id
WHERE totals.order_id IS NULL OR purchase.amount <> totals.item_total
ORDER BY purchase.order_id;

SELECT SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) AS paid,
       SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END) AS pending,
       SUM(CASE WHEN status = 'refunded' THEN amount ELSE 0 END) AS refunded
FROM orders;

SELECT 100.0 * SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS paid_percentage
FROM orders;

WITH ranked AS (
    SELECT order_id, customer_id,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS row_position
    FROM orders
)
SELECT customer_id, order_id FROM ranked WHERE row_position = 1 ORDER BY customer_id;

WITH ranked AS (
    SELECT employee_id, department, salary,
           DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
    FROM employees
)
SELECT department, employee_id, salary FROM ranked WHERE salary_rank = 2 ORDER BY department, employee_id;

WITH ranked AS (
    SELECT employee_id, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC, employee_id) AS row_position
    FROM employees
)
SELECT department, employee_id, salary FROM ranked WHERE row_position <= 2 ORDER BY department, row_position;

SELECT order_id, customer_id,
       SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_paid
FROM orders WHERE status = 'paid' ORDER BY customer_id, order_date, order_id;

SELECT order_id, customer_id,
       amount - LAG(amount) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS change_from_previous_paid
FROM orders WHERE status = 'paid' ORDER BY customer_id, order_date, order_id;

WITH spending AS (
    SELECT customer_id, SUM(amount) AS revenue FROM orders WHERE status = 'paid' GROUP BY customer_id
)
SELECT customer_id, revenue, 100.0 * revenue / NULLIF(SUM(revenue) OVER (), 0) AS revenue_share
FROM spending ORDER BY customer_id;

SELECT customer_id FROM orders WHERE status = 'paid'
EXCEPT
SELECT customer_id FROM orders WHERE status = 'refunded'
ORDER BY customer_id;

SELECT customer_id, event_time, event_type, COUNT(*) AS copies
FROM events GROUP BY customer_id, event_time, event_type HAVING COUNT(*) > 1
ORDER BY customer_id, event_time, event_type;

WITH ranked AS (
    SELECT event_id, ROW_NUMBER() OVER (PARTITION BY customer_id, event_time, event_type ORDER BY event_id) AS row_position
    FROM events
)
SELECT event_id FROM ranked WHERE row_position = 1 ORDER BY event_id;

WITH RECURSIVE hierarchy AS (
    SELECT employee_id, employee_name, 0 AS depth FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT employee.employee_id, employee.employee_name, hierarchy.depth + 1
    FROM employees employee JOIN hierarchy ON employee.manager_id = hierarchy.employee_id
    WHERE hierarchy.depth < 10
)
SELECT employee_id, depth FROM hierarchy ORDER BY employee_id;
