-- Stored procedure: sp_perform_transaction
-- Purpose: perform atomic account transactions (DEPOSIT, WITHDRAW, TRANSFER)
-- Assumes tables: bank_account(account_no, balance, customer_id, ...), bank_transaction(id, account_id, date, amount, transaction_type)
-- This procedure updates balances and inserts transaction records in a transaction-safe way.

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_perform_transaction$$

CREATE PROCEDURE sp_perform_transaction(
    IN p_from_account VARCHAR(20),
    IN p_to_account VARCHAR(20),
    IN p_amount DECIMAL(12,2),
    IN p_type ENUM('DEPOSIT','WITHDRAW','TRANSFER'),
    IN p_txn_by VARCHAR(50)
)
BEGIN
    DECLARE v_from_acc_id BIGINT;
    DECLARE v_to_acc_id BIGINT;
    DECLARE v_from_balance DECIMAL(15,2);
    DECLARE v_to_balance DECIMAL(15,2);
    DECLARE v_now DATETIME;

    SET v_now = NOW();

    -- Basic validations
    IF p_amount <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Amount must be greater than zero';
    END IF;

    -- Lookup account IDs and balances when account numbers provided
    IF p_from_account IS NOT NULL AND p_from_account <> '' THEN
        SELECT id, balance INTO v_from_acc_id, v_from_balance
        FROM bank_account WHERE account_no = p_from_account FOR UPDATE;
        IF v_from_acc_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'From account not found';
        END IF;
    ELSE
        SET v_from_acc_id = NULL;
        SET v_from_balance = NULL;
    END IF;

    IF p_to_account IS NOT NULL AND p_to_account <> '' THEN
        SELECT id, balance INTO v_to_acc_id, v_to_balance
        FROM bank_account WHERE account_no = p_to_account FOR UPDATE;
        IF v_to_acc_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'To account not found';
        END IF;
    ELSE
        SET v_to_acc_id = NULL;
        SET v_to_balance = NULL;
    END IF;

    -- Begin transaction block
    START TRANSACTION;
    
    IF p_type = 'DEPOSIT' THEN
        -- Deposit into to_account
        IF v_to_acc_id IS NULL THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'To account required for deposit';
        END IF;

        UPDATE bank_account SET balance = balance + p_amount WHERE id = v_to_acc_id;
        INSERT INTO bank_transaction (account_id, date, amount, transaction_type) VALUES (v_to_acc_id, v_now, p_amount, 'DEPOSIT');

    ELSEIF p_type = 'WITHDRAW' THEN
        -- Withdraw from from_account
        IF v_from_acc_id IS NULL THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'From account required for withdraw';
        END IF;

        -- Check sufficient funds
        IF v_from_balance < p_amount THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient funds';
        END IF;

        UPDATE bank_account SET balance = balance - p_amount WHERE id = v_from_acc_id;
        INSERT INTO bank_transaction (account_id, date, amount, transaction_type) VALUES (v_from_acc_id, v_now, p_amount, 'WITHDRAW');

    ELSEIF p_type = 'TRANSFER' THEN
        -- Transfer: debit from_account and credit to_account
        IF v_from_acc_id IS NULL OR v_to_acc_id IS NULL THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Both from_account and to_account required for transfer';
        END IF;

        IF v_from_acc_id = v_to_acc_id THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'From and To account cannot be the same';
        END IF;

        IF v_from_balance < p_amount THEN
            ROLLBACK;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient funds in from_account';
        END IF;

        UPDATE bank_account SET balance = balance - p_amount WHERE id = v_from_acc_id;
        UPDATE bank_account SET balance = balance + p_amount WHERE id = v_to_acc_id;

        INSERT INTO bank_transaction (account_id, date, amount, transaction_type) VALUES (v_from_acc_id, v_now, p_amount, 'WITHDRAW');
        INSERT INTO bank_transaction (account_id, date, amount, transaction_type) VALUES (v_to_acc_id, v_now, p_amount, 'DEPOSIT');

    ELSE
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid transaction type';
    END IF;

    COMMIT;

END$$

DELIMITER ;
