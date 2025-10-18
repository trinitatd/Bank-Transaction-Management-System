-- Test script for sp_perform_transaction
-- Edit account numbers to match two existing accounts in your DB before running.

-- 1) Install the procedure file (if not already installed)
-- SOURCE C:/Users/trini/Downloads/BTMS/sql/sp_perform_transaction.sql;

-- 2) Show balances before
SELECT account_no, balance FROM bank_account WHERE account_no IN ('ACC1','ACC2');

-- 3) Test deposit into ACC1
CALL sp_perform_transaction(NULL, 'ACC1', 100.00, 'DEPOSIT', 'test_runner');
SELECT account_no, balance FROM bank_account WHERE account_no = 'ACC1';
SELECT * FROM bank_transaction WHERE account_id = (SELECT id FROM bank_account WHERE account_no='ACC1') ORDER BY date DESC LIMIT 5;

-- 4) Test withdraw from ACC1
CALL sp_perform_transaction('ACC1', NULL, 10.00, 'WITHDRAW', 'test_runner');
SELECT account_no, balance FROM bank_account WHERE account_no = 'ACC1';
SELECT * FROM bank_transaction WHERE account_id = (SELECT id FROM bank_account WHERE account_no='ACC1') ORDER BY date DESC LIMIT 5;

-- 5) Test transfer from ACC1 to ACC2
CALL sp_perform_transaction('ACC1', 'ACC2', 25.00, 'TRANSFER', 'test_runner');
SELECT account_no, balance FROM bank_account WHERE account_no IN ('ACC1','ACC2');
SELECT * FROM bank_transaction WHERE account_id IN (SELECT id FROM bank_account WHERE account_no IN ('ACC1','ACC2')) ORDER BY date DESC LIMIT 10;

-- Notes:
-- - If the procedure raises a SIGNAL, the CALL will fail with an error message.
-- - Adjust ACC1/ACC2 to real account numbers from your DB before running.
