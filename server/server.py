import os
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import base64
from flask import Flask, request, render_template, redirect, url_for, flash
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key') 

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('my_database.db')  
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            score REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

create_table()

# Register route - for user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Encode password as base64 (temporary, not secure for production)
    encoded_password = base64.b64encode(password.encode()).decode()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, encoded_password)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Registration successful!"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Username already exists!"}), 409

# Login route - for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Encode incoming password to match what's in DB
    encoded_password = base64.b64encode(password.encode()).decode()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, encoded_password)
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Login successful!"})
    else:
        return jsonify({"message": "Invalid username or password."}), 401
@app.route('/showleaderboard', methods=['GET'])
def show_leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, score FROM users ORDER BY score DESC")
    users = cursor.fetchall()
    conn.close()

    leaderboard = [{"username": user['username'], "score": user['score']} for user in users]
    return jsonify(leaderboard)
@app.route('/update_core', methods=['POST'])
def update_score():
    conn = get_db_connection()
    cursor = conn.cursor()

    username = 'test'

    cursor.execute("SELECT score FROM users WHERE username = ?", (username,))
    current_score = cursor.fetchone()

    if current_score:
        new_score = current_score['score'] + 10
        cursor.execute("UPDATE users SET score = ? WHERE username = ?", (new_score, username))
        conn.commit()
        response = {
            'message': 'Score updated successfully!',
            'updated_score': new_score
        }
    else:
        response = {
            'message': 'User not found.'
        }

    conn.close()
    return jsonify(response)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


