DELIMITER //

CREATE TRIGGER update_account_balance
AFTER INSERT ON bank_transaction
FOR EACH ROW
BEGIN
    -- normalize type and guard amount
    DECLARE ttype VARCHAR(64);
    SET ttype = UPPER(COALESCE(NEW.transaction_type, ''));

    -- ensure amount is present, then apply credit/debit logic
    IF NEW.amount IS NOT NULL THEN
        -- credit cases
        IF ttype IN ('DEPOSIT', 'DEPOSITED', 'CREDIT', 'CR') OR ttype LIKE '%IN%' THEN
            UPDATE bank_account
            SET balance = balance + NEW.amount
            WHERE id = NEW.account_id;

        -- debit / withdrawal cases
        ELSEIF ttype IN ('WITHDRAW', 'WITHDRAWAL', 'DEBIT', 'DR') OR ttype LIKE '%OUT%' THEN
            UPDATE bank_account
            SET balance = balance - NEW.amount
            WHERE id = NEW.account_id;

        END IF;
    END IF;
END;
//

DELIMITER ;
