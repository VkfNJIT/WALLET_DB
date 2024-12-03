-- Disable foreign key checks
SET FOREIGN_KEY_CHECKS = 0;

-- Drop the tables
DROP TABLE IF EXISTS WALLET_USER_ACCOUNT;
DROP TABLE IF EXISTS ELECTRO_ADDR;
DROP TABLE IF EXISTS SEND_TRANS;
DROP TABLE IF EXISTS REQUEST_TRANS;
DROP TABLE IF EXISTS REQUESTED_FROM;
DROP TABLE IF EXISTS CANCELLED_SEND_TRANS;
DROP TABLE IF EXISTS LINKED_TO;
DROP TABLE IF EXISTS BANK_ACCOUNT;

-- Enable foreign key checks again
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE WALLET_USER_ACCOUNT(
	SSN INTEGER PRIMARY KEY,
	FNAME VARCHAR(50),
	LNAME VARCHAR(50),
	BALANCE DECIMAL DEFAULT 0,
	CONFIRMED BOOLEAN
);

CREATE TABLE BANK_ACCOUNT(
	BANKID INTEGER,
	BANUMBER INTEGER,
	PRIMARY KEY (BANKID, BANUMBER)
);

CREATE TABLE LINKED_TO(
	BANKID INTEGER,
	BANUMBER INTEGER,
	WSSN INTEGER,
	BVERIFIED BOOLEAN,
	PRIMARY KEY (BANKID, BANUMBER, WSSN),
	FOREIGN KEY (BANKID, BANUMBER) REFERENCES BANK_ACCOUNT(BANKID, BANUMBER),
	FOREIGN KEY (WSSN) REFERENCES WALLET_USER_ACCOUNT(SSN)
);

CREATE TABLE ELECTRO_ADDR(
	IDENTIFIER VARCHAR(100) PRIMARY KEY,
	WASSN INTEGER,
	TYPE VARCHAR(10),
	VERIFIED BOOLEAN,
	FOREIGN KEY (WASSN) REFERENCES WALLET_USER_ACCOUNT(SSN)
);

CREATE TABLE SEND_TRANS(
	STID INTEGER PRIMARY KEY,
	SSSN INTEGER,
	STO VARCHAR(100),
	SAMOUNT DECIMAL,
	IN_DATE_TIME DATETIME,
	COMP_DATE_TIME DATETIME,
	SMEMO VARCHAR(250),
	FOREIGN KEY (SSSN) REFERENCES WALLET_USER_ACCOUNT(SSN),
	FOREIGN KEY (STO) REFERENCES ELECTRO_ADDR(IDENTIFIER)
);

CREATE TABLE CANCELLED_SEND_TRANS(
	STID INTEGER PRIMARY KEY,
	CANCELLATION_REASON VARCHAR(250),
	FOREIGN KEY (STID) REFERENCES SEND_TRANS(STID)
);

CREATE TABLE REQUEST_TRANS(
	RTID INTEGER PRIMARY KEY,
	RSSN INTEGER,
	RAMOUNT DECIMAL,
	RT_DATE_TIME DATETIME,
	RMEMO VARCHAR(250),
	FOREIGN KEY (RSSN) REFERENCES WALLET_USER_ACCOUNT(SSN)
);

CREATE TABLE REQUESTED_FROM(
	RTID INTEGER,
	RFROM VARCHAR(100),
	PERCENTAGE REAL CHECK (PERCENTAGE >= 0 AND PERCENTAGE <= 100),
	PRIMARY KEY (RTID, RFROM),
	FOREIGN KEY (RTID) REFERENCES REQUEST_TRANS(RTID),
	FOREIGN KEY (RFROM) REFERENCES ELECTRO_ADDR(IDENTIFIER)
);
# TO BE CONTINUED
-- Populate WALLET_USER_ACCOUNT
INSERT INTO WALLET_USER_ACCOUNT (SSN, FNAME, LNAME, BALANCE, CONFIRMED)
VALUES
(1001, 'Alice', 'Johnson', 500.00, TRUE),
(1002, 'Bob', 'Smith', 300.00, TRUE),
(1003, 'Charlie', 'Brown', 1000.00, TRUE),
(1004, 'Diana', 'Evans', 200.00, FALSE),
(1005, 'Eve', 'Taylor', 150.00, TRUE);

-- Populate BANK_ACCOUNT
INSERT INTO BANK_ACCOUNT (BANKID, BANUMBER)
VALUES
(1, 123456),
(2, 654321),
(3, 789012);

-- Populate LINKED_TO
INSERT INTO LINKED_TO (BANKID, BANUMBER, WSSN, BVERIFIED)
VALUES
(1, 123456, 1001, TRUE),
(2, 654321, 1002, FALSE),
(3, 789012, 1003, TRUE);

-- Populate ELECTRO_ADDR
INSERT INTO ELECTRO_ADDR (IDENTIFIER, WASSN, TYPE, VERIFIED)
VALUES
('alice@example.com', 1001, 'email', TRUE),
('bob@example.com', 1002, 'email', TRUE),
('+1234567890', 1003, 'phone', TRUE),
('+1987654321', 1004, 'phone', FALSE),
('eve@example.com', 1005, 'email', TRUE);

-- Populate SEND_TRANS
INSERT INTO SEND_TRANS (STID, SSSN, STO, SAMOUNT, IN_DATE_TIME, COMP_DATE_TIME, SMEMO)
VALUES
(1, 1001, 'bob@example.com', 50.00, '2024-12-01 10:00:00', '2024-12-01 10:15:00', 'Lunch payment'),
(2, 1002, '+1234567890', 75.00, '2024-12-01 11:00:00', '2024-12-01 11:30:00', 'Rent contribution'),
(3, 1003, 'alice@example.com', 20.00, '2024-11-30 09:00:00', '2024-11-30 09:10:00', 'Book payment'),
(4, 1001, 'eve@example.com', 30.00, '2024-12-01 15:00:00', NULL, 'Pending grocery payment');

-- Populate CANCELLED_SEND_TRANS
INSERT INTO CANCELLED_SEND_TRANS (STID, CANCELLATION_REASON)
VALUES
(4, 'Insufficient funds');

-- Populate REQUEST_TRANS
INSERT INTO REQUEST_TRANS (RTID, RSSN, RAMOUNT, RT_DATE_TIME, RMEMO)
VALUES
(1, 1002, 100.00, '2024-11-29 08:30:00', 'Dinner reimbursement'),
(2, 1004, 50.00, '2024-11-28 10:45:00', 'Carpool gas share');

-- Populate REQUESTED_FROM
INSERT INTO REQUESTED_FROM (RTID, RFROM, PERCENTAGE)
VALUES
(1, 'alice@example.com', 50),
(1, '+1234567890', 50),
(2, 'bob@example.com', 100);
