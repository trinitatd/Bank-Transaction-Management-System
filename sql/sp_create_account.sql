DELIMITER $$

CREATE PROCEDURE sp_create_account(
    IN p_aadhaar VARCHAR(12),
    IN p_account_no VARCHAR(20),
    IN p_initial DECIMAL(12,2),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_cust_exists INT;

    -- Check if the customer exists
    SELECT COUNT(*) INTO v_cust_exists
    FROM bank_customer
    WHERE aadhaar_no = p_aadhaar;

    IF v_cust_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Customer not found';
    END IF;

    -- Check if the account already exists
    IF EXISTS (SELECT 1 FROM bank_account WHERE account_no = p_account_no) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Account exists';
    END IF;

    -- Start transaction
    START TRANSACTION;

    -- Insert the new account
    INSERT INTO bank_account (account_no, balance, customer_id)
    VALUES (p_account_no, 0.00, p_aadhaar);

    -- Perform initial deposit if any
    IF p_initial > 0 THEN
        CALL sp_perform_transaction(NULL, p_account_no, p_initial, 'DEPOSIT', p_by);
    END IF;

    -- Commit transaction
    COMMIT;
END$$

DELIMITER ;
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_create_account$$
CREATE PROCEDURE sp_create_account(
    IN p_aadhaar VARCHAR(12),
    IN p_account_no VARCHAR(20),
    IN p_initial DECIMAL(12,2),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;
    SELECT COUNT(*) INTO v_exists FROM bank_customer WHERE aadhaar_no = p_aadhaar;
    IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Customer not found';
    END IF;

    IF EXISTS(SELECT 1 FROM bank_account WHERE account_no = p_account_no) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account already exists';
    END IF;

    START TRANSACTION;
    INSERT INTO bank_account (account_no, balance, customer_id) VALUES (p_account_no, 0.00, p_aadhaar);
    IF p_initial > 0 THEN
        CALL sp_perform_transaction(NULL, p_account_no, p_initial, 'DEPOSIT', p_by);
    END IF;
    COMMIT;
END$$
DELIMITER ;
