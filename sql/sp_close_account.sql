DELIMITER $$

CREATE PROCEDURE sp_close_account(
    IN p_account_no VARCHAR(20),
    IN p_transfer_to VARCHAR(20),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_acc_id BIGINT;
    DECLARE v_balance DECIMAL(12,2);

    -- Start transaction
    START TRANSACTION;

    -- Lock the account row for update
    SELECT id, balance 
    INTO v_acc_id, v_balance
    FROM bank_account
    WHERE account_no = p_account_no
    FOR UPDATE;

    -- Check if account exists
    IF v_acc_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account not found';
    END IF;

    -- Handle balance transfer if needed
    IF v_balance > 0 THEN
        IF p_transfer_to IS NULL OR p_transfer_to = '' THEN
            SIGNAL SQLSTATE '45000' 
                SET MESSAGE_TEXT = 'Balance must be zero or provide transfer_to';
        ELSE
            CALL sp_perform_transaction(p_account_no, p_transfer_to, v_balance, 'TRANSFER', p_by);
        END IF;
    END IF;

    -- Close the account
    UPDATE bank_account 
    SET is_closed = 1 
    WHERE id = v_acc_id;

    -- Commit transaction
    COMMIT;
END$$

DELIMITER ;
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_close_account$$
CREATE PROCEDURE sp_close_account(
    IN p_account_no VARCHAR(20),
    IN p_transfer_to VARCHAR(20),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_acc_id BIGINT;
    DECLARE v_balance DECIMAL(15,2);

    SELECT id, balance INTO v_acc_id, v_balance FROM bank_account WHERE account_no = p_account_no FOR UPDATE;
    IF v_acc_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account not found';
    END IF;

    IF v_balance > 0 THEN
        IF p_transfer_to IS NULL OR p_transfer_to = '' THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Balance must be zero or provide transfer_to';
        ELSE
            CALL sp_perform_transaction(p_account_no, p_transfer_to, v_balance, 'TRANSFER', p_by);
        END IF;
    END IF;

    -- soft close: set is_closed flag (add column if missing)
    UPDATE bank_account SET is_closed = 1 WHERE id = v_acc_id;
END$$
DELIMITER ;
