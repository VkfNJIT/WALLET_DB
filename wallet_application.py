from flask import Flask, request, jsonify
import mariadb

# Flask app setup
app = Flask(__name__)

# Database configuration
db_config = {
    'user': 'vishalfenn',          # Your MariaDB username
    'password': 'Arow@63516',          # Your MariaDB password
    'host': 'localhost',     # MariaDB server host
    'port': 3306,            # Default MariaDB port
    'database': 'WALLET'  # Name of the database
}

# Function to establish a database connection
def get_db_connection():
    try:
        conn = mariadb.connect(**db_config)
        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        raise

# API to fetch account information by SSN
@app.route('/account/<int:ssn>', methods=['GET'])
def get_account_info(ssn):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query to fetch account info
        cursor.execute("SELECT * FROM WALLET_USER_ACCOUNT WHERE SSN = ?", (ssn,))
        account = cursor.fetchone()
        cursor.close()
        conn.close()

        if account:
            return jsonify(account)
        else:
            return jsonify({'message': 'Account not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API to send money
@app.route('/send-money', methods=['POST'])
def send_money():
    try:
        data = request.json
        sender_ssn = data['senderSSN']
        recipient = data['recipient']  # Email or phone number
        amount = data['amount']
        memo = data.get('memo', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Start a transaction
        conn.autocommit = False

        # Deduct amount from sender
        cursor.execute("UPDATE WALLET_USER_ACCOUNT SET BALANCE = BALANCE - ? WHERE SSN = ?", (amount, sender_ssn))

        # Add amount to recipient
        cursor.execute("""
            UPDATE WALLET_USER_ACCOUNT 
            SET BALANCE = BALANCE + ?
            WHERE SSN IN (SELECT WASSN FROM ELECTRO_ADDR WHERE IDENTIFIER = ?)
        """, (amount, recipient))

        # Log the transaction
        cursor.execute("""
            INSERT INTO SEND_TRANS (SSSN, STO, SAMOUNT, IN_DATE_TIME, SMEMO)
            VALUES (?, ?, ?, NOW(), ?)
        """, (sender_ssn, recipient, amount, memo))

        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Transaction successful'})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500

# API to fetch transaction statements
@app.route('/statements/<int:ssn>', methods=['GET'])
def get_statements(ssn):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query to fetch statements within date range
        cursor.execute("""
            SELECT SAMOUNT, IN_DATE_TIME, SMEMO
            FROM SEND_TRANS
            WHERE SSSN = ? AND IN_DATE_TIME BETWEEN ? AND ?
        """, (ssn, start_date, end_date))
        statements = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(statements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API to modify personal details
@app.route('/account/<int:ssn>', methods=['PUT'])
def modify_account_info(ssn):
    try:
        data = request.json
        fname = data.get('FNAME')
        lname = data.get('LNAME')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update personal details
        cursor.execute("""
            UPDATE WALLET_USER_ACCOUNT
            SET FNAME = ?, LNAME = ?
            WHERE SSN = ?
        """, (fname, lname, ssn))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Account details updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API to add or remove email or phone
@app.route('/account/contact/<int:ssn>', methods=['POST'])
def modify_contact_info(ssn):
    try:
        data = request.json
        identifier = data['IDENTIFIER']
        contact_type = data['TYPE']
        action = data['ACTION']  # 'add' or 'remove'

        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'add':
            # Add email or phone
            cursor.execute("""
                INSERT INTO ELECTRO_ADDR (IDENTIFIER, WASSN, TYPE, VERIFIED)
                VALUES (?, ?, ?, FALSE)
            """, (identifier, ssn, contact_type))
        elif action == 'remove':
            # Remove email or phone
            cursor.execute("""
                DELETE FROM ELECTRO_ADDR WHERE IDENTIFIER = ? AND WASSN = ?
            """, (identifier, ssn))
        else:
            return jsonify({'error': 'Invalid action'}), 400

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Contact info updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)
