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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the main account details
    cursor.execute('SELECT * FROM WALLET_USER_ACCOUNT WHERE SSN = ?', (ssn,))
    user_data = cursor.fetchone()
    
    # Get the email and phone
    cursor.execute('''
        SELECT 
            CASE 
                WHEN TYPE = 'email' THEN IDENTIFIER 
                ELSE NULL 
            END AS email,
            CASE 
                WHEN TYPE = 'phone' THEN IDENTIFIER 
                ELSE NULL 
            END AS phone
        FROM ELECTRO_ADDR 
        WHERE WASSN = ?
    ''', (ssn,))
    contacts = cursor.fetchall()
    
    conn.close()

    if user_data:
        # Extract email and phone from the results
        email = next((c[0] for c in contacts if c[0]), None)
        phone = next((c[1] for c in contacts if c[1]), None)

        user = {
            'ssn': user_data[0],
            'first_name': user_data[1],
            'last_name': user_data[2],
            'balance': user_data[3],
            'confirmed': user_data[4],
            'email': email,
            'phone': phone
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
                    UPDATE ELECTRO_ADDR 
                    SET IDENTIFIER = ?, VERIFIED = TRUE
                    WHERE WASSN = ? AND TYPE = 'email'
                ''', (email, ssn))
            
            # Update phone in ELECTRO_ADDR
            if phone:
                cursor.execute('''
                    UPDATE ELECTRO_ADDR 
                    SET IDENTIFIER = ?, VERIFIED = TRUE
                    WHERE WASSN = ? AND TYPE = 'phone'
                ''', (phone, ssn))

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
        smemo = request.form.get('memo', '') 

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
                INSERT INTO SEND_TRANS (SSSN, STO, SAMOUNT, IN_DATE_TIME, SMEMO)
                VALUES (?, ?, ?, NOW(), ?)
            ''', (sender_ssn, recipient, amount, smemo))

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

# Request 
@app.route('/request_money', methods=['GET', 'POST'])
def request_money():
    if 'ssn' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ssn = request.form['ssn']
        requester = request.form['requester']  # The person you are requesting money from
        amount = float(request.form['amount'])
        rmemo = request.form.get('memo', '')  # Optional memo
        percentage = float(request.form['percentage']) if 'percentage' in request.form else 0.0  # Default to 0% if not provided

        # Insert request transaction into database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert into REQUEST_TRANS table
        cursor.execute('''INSERT INTO REQUEST_TRANS (RSSN, RAMOUNT, RT_DATE_TIME, RMEMO)
                          VALUES (%s, %s, NOW(), %s)''',
                       (ssn, amount, rmemo))
        
        # Get the last inserted RTID for the request (Using cursor.lastrowid)
        last_rt_id = cursor.lastrowid  # This works in MariaDB for getting the last insert ID

        # Insert into REQUESTED_FROM table
        cursor.execute('''INSERT INTO REQUESTED_FROM (RTID, RFROM, PERCENTAGE)
                          VALUES (%s, %s, %s)''',
                       (last_rt_id, requester, percentage))

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
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch send transactions
        cursor.execute(
            '''
            SELECT ST.STID, ST.SSSN, ST.STO, ST.SAMOUNT, ST.IN_DATE_TIME, 
                   ST.COMP_DATE_TIME, ST.SMEMO, C.CANCELLATION_REASON
            FROM SEND_TRANS ST
            LEFT JOIN CANCELLED_SEND_TRANS C ON ST.STID = C.STID
            WHERE ST.SSSN = ? AND ST.IN_DATE_TIME BETWEEN ? AND ?
            ''',
            (ssn, start_date, end_date)
        )
        transactions = cursor.fetchall()

        # Fetch request transactions
        cursor.execute(
            '''
            SELECT RT.RTID, RT.RSSN, RT.RAMOUNT, RT.RT_DATE_TIME, RT.RMEMO, 
                   RF.RFROM, RF.PERCENTAGE
            FROM REQUEST_TRANS RT
            JOIN REQUESTED_FROM RF ON RT.RTID = RF.RTID
            WHERE RT.RSSN = ? AND RT.RT_DATE_TIME BETWEEN ? AND ?
            ''',
            (ssn, start_date, end_date)
        )
        request_transactions = cursor.fetchall()
        print("DEBUG: Request Transactions:", request_transactions)  # Debug log

        # Fetch user contact information
        cursor.execute(
            '''
            SELECT IDENTIFIER, TYPE
            FROM ELECTRO_ADDR
            WHERE WASSN = ?
            ''',
            (ssn,)
        )
        user_contact_info = cursor.fetchall()
        conn.close()

        # Prepare contact info for display
        email_list = [item[0] for item in user_contact_info if item[1] == 'email']
        phone_list = [item[0] for item in user_contact_info if item[1] == 'phone']

        # Render the results
        return render_template(
            'search_results.html',
            transactions=transactions,
            request_transactions=request_transactions,
            user_contact_info={'email': email_list, 'phone': phone_list}
        )

    return render_template('search_transactions.html')


@app.route('/sign_out')
def sign_out():
    session.pop('ssn', None)  # Clear session
    return redirect(url_for('main_menu'))

if __name__ == '__main__':
    app.run(debug=True)
