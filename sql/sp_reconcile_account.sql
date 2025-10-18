DELIMITER $$

CREATE PROCEDURE sp_reconcile_account(
    IN p_account_no VARCHAR(20),
    IN p_fix TINYINT(1)
)
BEGIN
    DECLARE v_acc_id BIGINT DEFAULT NULL;
    DECLARE v_calc DECIMAL(15,2) DEFAULT 0;
    DECLARE v_balance DECIMAL(15,2) DEFAULT 0;

    -- Start a transaction to ensure data consistency
    START TRANSACTION;

    -- Lock and fetch account details
    SELECT id, balance 
    INTO v_acc_id, v_balance
    FROM bank_account
    WHERE account_no = p_account_no
    FOR UPDATE;

    -- If no such account exists
    IF v_acc_id IS NULL THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account not found';
    END IF;

    -- Calculate the computed balance from transactions
    SELECT 
        COALESCE(SUM(
            CASE 
                WHEN transaction_type = 'DEPOSIT' THEN amount 
                WHEN transaction_type = 'WITHDRAW' THEN -amount 
                ELSE 0 
            END
        ), 0)
    INTO v_calc
    FROM bank_transaction
    WHERE account_id = v_acc_id;

    -- If mismatch detected
    IF v_calc <> v_balance THEN
        IF p_fix = 1 THEN
            -- Fix the balance and log it
            UPDATE bank_account 
            SET balance = v_calc 
            WHERE id = v_acc_id;

            INSERT INTO reconciliation_audit (account_id, old_balance, new_balance, created_at)
            VALUES (v_acc_id, v_balance, v_calc, NOW());
        END IF;
    END IF;

    -- Commit transaction
    COMMIT;

    -- Return a summary result
    SELECT 
        v_acc_id AS account_id,
        v_balance AS db_balance,
        v_calc AS computed_balance,
        (v_calc - v_balance) AS discrepancy;
END$$

DELIMITER ;
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_reconcile_account$$
CREATE PROCEDURE sp_reconcile_account(
    IN p_account_no VARCHAR(20),
    IN p_fix TINYINT(1)
)
BEGIN
    DECLARE v_acc_id BIGINT;
    DECLARE v_db_balance DECIMAL(15,2);
    DECLARE v_calc DECIMAL(15,2);

    SELECT id, balance INTO v_acc_id, v_db_balance FROM bank_account WHERE account_no = p_account_no FOR UPDATE;
    IF v_acc_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account not found';
    END IF;

    SELECT SUM(CASE WHEN transaction_type='DEPOSIT' THEN amount WHEN transaction_type='WITHDRAW' THEN -amount ELSE 0 END) INTO v_calc FROM bank_transaction WHERE account_id = v_acc_id;
    IF v_calc IS NULL THEN SET v_calc = 0; END IF;

    IF v_calc <> v_db_balance THEN
        IF p_fix = 1 THEN
            UPDATE bank_account SET balance = v_calc WHERE id = v_acc_id;
            INSERT INTO reconciliation_audit (account_id, old_balance, new_balance, created_at) VALUES (v_acc_id, v_db_balance, v_calc, NOW());
        END IF;
    END IF;

    SELECT v_acc_id AS account_id, v_db_balance AS db_balance, v_calc AS computed_balance, v_calc - v_db_balance AS discrepancy;
END$$
DELIMITER ;
