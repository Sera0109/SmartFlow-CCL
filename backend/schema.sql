CREATE DATABASE IF NOT EXISTS smartflow;
USE smartflow;

CREATE TABLE IF NOT EXISTS customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS agents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  status ENUM('Free', 'Busy', 'Offline') NOT NULL DEFAULT 'Free',
  lat DOUBLE NOT NULL,
  lng DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  item VARCHAR(200),
  pickup_lat DOUBLE,
  pickup_lng DOUBLE,
  drop_address VARCHAR(255),
  status ENUM('Placed', 'Assigned', 'Out for Delivery', 'Delivered') DEFAULT 'Placed',
  agent_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES customers(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  INDEX idx_orders_status (status),
  INDEX idx_orders_agent (agent_id)
);

CREATE TABLE IF NOT EXISTS deliveries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL UNIQUE,
  agent_id INT,
  proof_key VARCHAR(255) NOT NULL,
  delivered_at DATETIME NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS delivery_status (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT,
  status VARCHAR(30),
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  INDEX idx_status_order_time (order_id, changed_at)
);

INSERT IGNORE INTO agents (name, email, status, lat, lng) VALUES
  ('Ravi', 'ravi@smartflow.test', 'Free', 19.2183, 72.9781),
  ('Priya', 'priya@smartflow.test', 'Free', 19.0760, 72.8777),
  ('Imran', 'imran@smartflow.test', 'Free', 19.1197, 72.8464),
  ('Sneha', 'sneha@smartflow.test', 'Free', 19.0330, 73.0297);
