DELIMITER $$

CREATE PROCEDURE sp_pay_loan(
    IN p_loan_no VARCHAR(20),
    IN p_from_account VARCHAR(20),
    IN p_amount DECIMAL(15,2),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_outstanding DECIMAL(15,2);

    -- Start transaction
    START TRANSACTION;

    -- Lock the loan row
    SELECT amount 
    INTO v_outstanding
    FROM loans 
    WHERE loan_no = p_loan_no
    FOR UPDATE;

    -- Check if loan exists
    IF v_outstanding IS NULL THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Loan not found';
    END IF;

    -- Perform withdrawal from account
    CALL sp_perform_transaction(p_from_account, NULL, p_amount, 'WITHDRAW', p_by);

    -- Update loan amount
    UPDATE loans 
    SET amount = amount - p_amount 
    WHERE loan_no = p_loan_no;

    -- Optionally: Insert into loan_payments table here

    -- Commit transaction
    COMMIT;
END$$

DELIMITER ;
DELIMITER $$
DROP PROCEDURE IF EXISTS sp_pay_loan$$
CREATE PROCEDURE sp_pay_loan(
    IN p_loan_no VARCHAR(20),
    IN p_from_account VARCHAR(20),
    IN p_amount DECIMAL(15,2),
    IN p_by VARCHAR(50)
)
BEGIN
    DECLARE v_outstanding DECIMAL(15,2);
    SELECT amount INTO v_outstanding FROM loans WHERE loan_no = p_loan_no FOR UPDATE;
    IF v_outstanding IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Loan not found';
    END IF;

    START TRANSACTION;
    CALL sp_perform_transaction(p_from_account, NULL, p_amount, 'WITHDRAW', p_by);
    UPDATE loans SET amount = amount - p_amount WHERE loan_no = p_loan_no;
    COMMIT;
END$$
DELIMITER ;
