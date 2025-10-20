-- Create queue table if not exists
CREATE TABLE IF NOT EXISTS customer_sync_queue (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    aadhaar_no VARCHAR(12) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed TINYINT(1) DEFAULT 0,
    processed_at DATETIME NULL
);

DELIMITER $$
DROP TRIGGER IF EXISTS trg_enqueue_customer_sync$$
CREATE TRIGGER trg_enqueue_customer_sync AFTER INSERT ON bank_customer
FOR EACH ROW
BEGIN
    INSERT INTO customer_sync_queue (aadhaar_no, created_at, processed) VALUES (NEW.aadhaar_no, NOW(), 0);
END$$
DELIMITER ;
