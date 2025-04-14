import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Secret key for session management, from the .env file or a default value
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Connection pool for PostgreSQL
db_pool = None

# Initialize PostgreSQL connection pool with the DATABASE_URL from .env
def init_connection_pool():
    global db_pool
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL is not set in the environment variables")
    
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20, database_url
    )

def get_db_connection():
    return db_pool.getconn()

def release_connection(conn):
    db_pool.putconn(conn)

# Create table for users if it doesn't exist
def create_table():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                score INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)

# Initialize the connection pool
init_connection_pool()

# Create the table if it doesn't exist
create_table()

# Register route - for user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Encode password as base64 (temporary)
    encoded_password = base64.b64encode(password.encode()).decode()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, encoded_password)
        )
        conn.commit()
        cursor.close()
        return jsonify({"message": "Registration successful!"})
    except psycopg2.errors.UniqueViolation:
        conn.rollback() 
        return jsonify({"message": "Username already exists!"}), 409
    finally:
        release_connection(conn)

# Login route - for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Encode incoming password to match what's in DB
    encoded_password = base64.b64encode(password.encode()).decode()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, encoded_password)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            return jsonify({"message": "Login successful!"})
        else:
            return jsonify({"message": "Invalid username or password."}), 401
    finally:
        release_connection(conn)

# Show leaderboard route
@app.route('/showleaderboard', methods=['GET'])
def show_leaderboard():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, score FROM users ORDER BY score DESC")
        users = cursor.fetchall()
        cursor.close()
        
        leaderboard = [{"username": user[0], "score": user[1]} for user in users]
        return jsonify(leaderboard)
    finally:
        release_connection(conn)

# Update score route
@app.route('/update_score', methods=['POST'])
def update_score():
    data = request.get_json()
    username = data.get('username', 'test')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
        current_score = cursor.fetchone()
        
        if current_score:
            new_score = current_score[0] + 10
            cursor.execute("UPDATE users SET score = %s WHERE username = %s", (new_score, username))
            conn.commit()
            response = {
                'message': 'Score updated successfully!',
                'updated_score': new_score
            }
        else:
            response = {
                'message': 'User not found.'
            }
        
        cursor.close()
        return jsonify(response)
    finally:
        release_connection(conn)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
