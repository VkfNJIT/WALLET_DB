from flask import Flask, render_template, request, redirect, url_for, session
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
    return render_template('main_menu.html', ssn=session['ssn'])

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

@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if 'ssn' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        ssn = request.form['ssn']
        recipient = request.form['recipient']
        amount = float(request.form['amount'])

        # Insert send transaction into database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO SEND_TRANS (SSSN, STO, SAMOUNT, IN_DATE_TIME) VALUES (?, ?, ?, NOW())',
                       (ssn, recipient, amount))
        conn.commit()
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
    ssn = session.get('ssn')  # Retrieve SSN from session

    # If SSN is not in session, redirect to login page
    if not ssn:
        return redirect(url_for('login'))

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query to calculate total amount sent and received by the user per month
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

    # Query to find the transactions with the maximum amount per month
    cursor.execute('''
        SELECT 
            YEAR(IN_DATE_TIME) AS year,
            MONTH(IN_DATE_TIME) AS month,
            MAX(SAMOUNT) AS max_transaction
        FROM SEND_TRANS
        WHERE SSSN = ?
        GROUP BY YEAR(IN_DATE_TIME), MONTH(IN_DATE_TIME)
    ''', (ssn,))
    max_transactions = cursor.fetchall()

    # Query to find the best users (users who have sent the most money)
    cursor.execute('''
        SELECT 
            SSSN, SUM(SAMOUNT) AS total_sent
        FROM SEND_TRANS
        GROUP BY SSSN
        ORDER BY total_sent DESC
        LIMIT 5
    ''')
    best_users = cursor.fetchall()

    conn.close()

    # Return the rendered template with the fetched data
    return render_template('statements.html', 
                           sent_data=sent_data,
                           received_data=received_data,
                           max_transactions=max_transactions,
                           best_users=best_users)




@app.route('/search_transactions', methods=['GET', 'POST'])
def search_transactions():
    if 'ssn' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        ssn = request.form['ssn']
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
