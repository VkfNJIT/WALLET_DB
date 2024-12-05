from flask import Flask, flash, render_template, request, redirect, url_for, session
import mariadb
import os
import secrets

app = Flask(__name__)

# Set a secret key for session management and security
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Connect to the MariaDB database
def get_db_connection():
    conn = mariadb.connect(
        user="vishalfenn",        # Replace with your MariaDB username
        password="Arow@63516",    # Replace with your MariaDB password
        host="localhost",
        port=3306,
        database="WALLET"            # Replace with your database name
    )
    return conn

@app.route('/')
def main_menu():
    if 'ssn' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT FNAME, LNAME FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (session['ssn'],))
    user_data = cursor.fetchone()
    conn.close()

    # Ensure user data is available
    if user_data:
        first_name, last_name = user_data
    else:
        first_name, last_name = "User", "Unknown"  # Default values in case of missing data

    return render_template('main_menu.html', ssn=session['ssn'], first_name=first_name, last_name=last_name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ssn = request.form['ssn']  # Get SSN from the form

        # Check if SSN exists in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (ssn,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            # Store the SSN in the session
            session['ssn'] = user_data[0]
            return redirect(url_for('main_menu'))  # Redirect to main menu after successful login
        else:
            return "SSN not found! Please try again."
    return render_template('login.html')

@app.route('/account_info/<int:ssn>')
def account_info(ssn):
    if 'ssn' not in session:
        return redirect(url_for('login'))
    # Display phone and email address
    #Add functionality to modify personal details (Name, email, phone)
    # Fetch user data from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (ssn,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        user = {
            'ssn': user_data[0],
            'first_name': user_data[1],
            'last_name': user_data[2],
            'balance': user_data[3],
            'confirmed': user_data[4]
        }
        return render_template('account_info.html', user=user)
    return f"User with SSN {ssn} not found!"

@app.route('/modify_account/<int:ssn>', methods=['GET', 'POST'])
def modify_account(ssn):
    # Ensure the user is logged in and authorized to modify this account
    if 'ssn' not in session or session['ssn'] != ssn:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Get updated data from the form
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        try:
            # Update the user's first and last name
            if fname and lname:
                cursor.execute('''
                    UPDATE WALLET_USER_ACCOUNT 
                    SET FNAME = ?, LNAME = ?
                    WHERE SSN = ?
                ''', (fname, lname, ssn))

            # Update email in ELECTRO_ADDR
            if email:
                cursor.execute('''
                    INSERT INTO ELECTRO_ADDR (IDENTIFIER, WASSN, TYPE, VERIFIED)
                    VALUES (?, ?, 'email', TRUE)
                    ON DUPLICATE KEY UPDATE IDENTIFIER = ?, VERIFIED = TRUE
                ''', (email, ssn, email))

            # Update phone in ELECTRO_ADDR
            if phone:
                cursor.execute('''
                    INSERT INTO ELECTRO_ADDR (IDENTIFIER, WASSN, TYPE, VERIFIED)
                    VALUES (?, ?, 'phone', TRUE)
                    ON DUPLICATE KEY UPDATE IDENTIFIER = ?, VERIFIED = TRUE
                ''', (phone, ssn, phone))

            conn.commit()
            return redirect(url_for('account_info', ssn=ssn))
        except mariadb.Error as e:
            conn.rollback()
            return f"An error occurred: {e}"
        finally:
            conn.close()

    # Fetch current user data to pre-fill the form
    cursor.execute('SELECT FNAME, LNAME FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (ssn,))
    user_data = cursor.fetchone()

    cursor.execute('SELECT IDENTIFIER, TYPE FROM ELECTRO_ADDR WHERE WASSN = ?', (ssn,))
    contact_info = cursor.fetchall()
    conn.close()

    # Organize contact information
    emails = [entry[0] for entry in contact_info if entry[1] == 'email']
    phones = [entry[0] for entry in contact_info if entry[1] == 'phone']

    return render_template(
        'modify_account.html', 
        user_data={'fname': user_data[0], 'lname': user_data[1]}, 
        emails=emails, 
        phones=phones,
        ssn=ssn
    )


@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if 'ssn' not in session:
        return redirect(url_for('login'))

    sender_ssn = session['ssn']

    if request.method == 'POST':
        recipient = request.form['recipient']
        amount = request.form.get('amount', type=float)

        # Validate input
        if not recipient or not amount or amount <= 0:
            flash("Please provide a valid recipient and amount greater than 0.", "error")
            return redirect(url_for('send_money'))

        # Insert send transaction into database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Insert into SEND_TRANS for sender
            cursor.execute('''
                INSERT INTO SEND_TRANS (SSSN, STO, SAMOUNT, IN_DATE_TIME)
                VALUES (?, ?, ?, NOW())
            ''', (sender_ssn, recipient, amount))

            # Check if recipient exists
            cursor.execute('SELECT COUNT(*) FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (recipient,))
            recipient_exists = cursor.fetchone()[0]

            # If recipient exists, insert a corresponding transaction for them
            if recipient_exists:
                cursor.execute('''
                    INSERT INTO REQUEST_TRANS (RSSN, RFROM, RAMOUNT, RT_DATE_TIME, STATUS)
                    VALUES (?, ?, ?, NOW(), 'completed')
                ''', (recipient, sender_ssn, amount))

            conn.commit()
            flash("Transaction successful!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"An error occurred: {e}", "error")
        finally:
            conn.close()

        return redirect(url_for('main_menu'))

    return render_template('send_money.html')


@app.route('/request_money', methods=['GET', 'POST'])
def request_money():
    if 'ssn' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ssn = request.form['ssn']
        requester = request.form['requester']
        amount = float(request.form['amount'])

        # Insert request transaction into database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO REQUEST_TRANS (RSSN, RAMOUNT, RT_DATE_TIME) VALUES (?, ?, NOW())',
                       (ssn, amount))
        conn.commit()
        conn.close()

        return redirect(url_for('main_menu'))

    return render_template('request_money.html')

@app.route('/statements', methods=['GET'])
def statements():
    # Retrieve the SSN from the session
    ssn = session.get('ssn')

    # If SSN is not in session, redirect to login page
    if not ssn:
        return redirect(url_for('login'))

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query: Total amount sent and received per month
        cursor.execute('''
            SELECT 
                YEAR(IN_DATE_TIME) AS year,
                MONTH(IN_DATE_TIME) AS month,
                SUM(SAMOUNT) AS total_sent
            FROM SEND_TRANS
            WHERE SSSN = ?
            GROUP BY YEAR(IN_DATE_TIME), MONTH(IN_DATE_TIME)
        ''', (ssn,))
        sent_data = cursor.fetchall()

        cursor.execute('''
            SELECT 
                YEAR(RT_DATE_TIME) AS year,
                MONTH(RT_DATE_TIME) AS month,
                SUM(RAMOUNT) AS total_received
            FROM REQUEST_TRANS
            WHERE RSSN = ?
            GROUP BY YEAR(RT_DATE_TIME), MONTH(RT_DATE_TIME)
        ''', (ssn,))
        received_data = cursor.fetchall()

        # Query: Maximum transaction amounts per month for sent and received
        cursor.execute('''
            SELECT 
                YEAR(IN_DATE_TIME) AS year,
                MONTH(IN_DATE_TIME) AS month,
                MAX(SAMOUNT) AS max_transaction_sent
            FROM SEND_TRANS
            WHERE SSSN = ?
            GROUP BY YEAR(IN_DATE_TIME), MONTH(IN_DATE_TIME)
        ''', (ssn,))
        max_transactions_sent = cursor.fetchall()

        cursor.execute('''
            SELECT 
                YEAR(RT_DATE_TIME) AS year,
                MONTH(RT_DATE_TIME) AS month,
                MAX(RAMOUNT) AS max_transaction_received
            FROM REQUEST_TRANS
            WHERE RSSN = ?
            GROUP BY YEAR(RT_DATE_TIME), MONTH(RT_DATE_TIME)
        ''', (ssn,))
        max_transactions_received = cursor.fetchall()

        # Query: Top 5 users who sent the most money
        cursor.execute('''
            SELECT 
                SSSN, SUM(SAMOUNT) AS total_sent
            FROM SEND_TRANS
            GROUP BY SSSN
            ORDER BY total_sent DESC
            LIMIT 5
        ''')
        best_users = cursor.fetchall()

        # Query: Top 5 users who received the most money
        cursor.execute('''
            SELECT 
                RSSN, SUM(RAMOUNT) AS total_received
            FROM REQUEST_TRANS
            GROUP BY RSSN
            ORDER BY total_received DESC
            LIMIT 5
        ''')
        top_receivers = cursor.fetchall()

    except Exception as e:
        conn.rollback()
        return f"An error occurred while fetching statements: {e}"
    finally:
        conn.close()

    # Render template with all fetched data
    return render_template(
        'statements.html', 
        sent_data=sent_data,
        received_data=received_data,
        max_transactions_sent=max_transactions_sent,
        max_transactions_received=max_transactions_received,
        best_users=best_users,
        top_receivers=top_receivers
    )





@app.route('/search_transactions', methods=['GET', 'POST'])
def search_transactions():
    if 'ssn' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ssn = request.form['ssn']
        # Shows the email address and phone number 
        # Add transaction type (4 options)
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # Fetch transactions from the database based on SSN and date range
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM SEND_TRANS WHERE SSSN = ? AND IN_DATE_TIME BETWEEN ? AND ?',
                       (ssn, start_date, end_date))
        transactions = cursor.fetchall()
        conn.close()

        return render_template('search_results.html', transactions=transactions)

    return render_template('search_transactions.html')

@app.route('/sign_out')
def sign_out():
    session.pop('ssn', None)  # Clear session
    return redirect(url_for('main_menu'))

if __name__ == '__main__':
    app.run(debug=True)
