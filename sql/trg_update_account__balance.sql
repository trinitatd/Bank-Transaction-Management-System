DELIMITER //

CREATE TRIGGER update_account_balance
AFTER INSERT ON bank_transaction
FOR EACH ROW
BEGIN
    IF NEW.transaction_type = 'Deposit' THEN
        UPDATE bank_account
        SET balance = balance + NEW.amount
        WHERE id = NEW.account_id;
    ELSEIF NEW.transaction_type = 'Withdrawal' THEN
        UPDATE bank_account
        SET balance = balance - NEW.amount
        WHERE id = NEW.account_id;
    END IF;
END;
//

DELIMITER ;
