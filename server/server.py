import os
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS
import base64
from evaluate import run_code  
import asyncio 

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Secret key for session management, from the .env
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
        
        # Also create a table to track completed questions
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_completed_questions (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                UNIQUE(username, question_id)
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

# Load questions from JSON
def load_questions():
    try:
        with open('questions.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []

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
            "SELECT id, username, score FROM users WHERE username = %s AND password = %s",
            (username, encoded_password)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            # Store user info in session
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['score'] = user[2]
            
            return jsonify({
                "message": "Login successful!",
                "username": user[1],
                "score": user[2]
            })
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
    username = data.get('username', 'test2')  # Default to test2 for now
    points = data.get('points', 10)  # Default 10 points per correct answer
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
        current_score = cursor.fetchone()
        
        if current_score:
            new_score = current_score[0] + points
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

@app.route('/evaluate_code', methods=['POST'])
def evaluate_code():
    data = request.get_json()
    username = data.get('username', 'test2')  # Default to test2 for testing
    code = data.get('code')
    language = data.get('language')
    question_id = data.get('question_id')
    expected_output = data.get('expected_output')
    
    # If expected_output wasn't provided directly, try to get it from the JSON file
    if not expected_output:
        questions = load_questions()
        for q in questions:
            if q['id'] == question_id:
                expected_output = q['sample_output']
                break
    
    # Run the async function synchronously
    result = asyncio.run(run_code(code, language, expected_output))

    if result["correct"]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if this user has already solved this question
            cursor.execute(
                "SELECT id FROM user_completed_questions WHERE username = %s AND question_id = %s",
                (username, question_id)
            )
            already_completed = cursor.fetchone()
            
            if not already_completed:
                # Update the user's score only if they haven't solved this question before
                cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
                row = cursor.fetchone()
                current_score = row[0] if row else 0
                new_score = current_score + result["score"]
                
                cursor.execute(
                    "UPDATE users SET score = %s WHERE username = %s",
                    (new_score, username)
                )
                
                # Mark the question as completed by this user
                cursor.execute(
                    "INSERT INTO user_completed_questions (username, question_id) VALUES (%s, %s)",
                    (username, question_id)
                )
                
                conn.commit()
                result["message"] = f"Correct! Score updated. New total: {new_score} points"
            else:
                # User already solved this question
                cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
                current_score = cursor.fetchone()[0]
                result["message"] = f"Correct! You've already received points for this question. Current score: {current_score}"
                
            cursor.close()
            
        except Exception as e:
            print(f"Database error: {e}")
            result["message"] = "Solution correct, but there was an error updating your score."
        finally:
            release_connection(conn)

    return jsonify(result)

@app.route('/get_questions', methods=['GET'])
def get_questions():
    questions = load_questions()
    return jsonify(questions)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)