-- Create audit table if not exists
CREATE TABLE IF NOT EXISTS transaction_audit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_id BIGINT,
    account_id BIGINT,
    amount DECIMAL(12,2),
    transaction_type VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

DELIMITER $$
DROP TRIGGER IF EXISTS trg_audit_transaction$$
CREATE TRIGGER trg_audit_transaction AFTER INSERT ON bank_transaction
FOR EACH ROW
BEGIN
    INSERT INTO transaction_audit (transaction_id, account_id, amount, transaction_type, created_at)
    VALUES (NEW.id, NEW.account_id, NEW.amount, NEW.transaction_type, NOW());
END$$
DELIMITER ;
