import os
import json
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, render_template
from flask_cors import CORS
import base64
from evaluate import run_code  
import asyncio 
import gunicorn

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Secret key for session management, from the .env
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Connection pool for PostgreSQL
db_pool = None

@app.route('/')
def home():
    return render_template('login.html')
@app.route('/mainpage')
def mainpage():
    return render_template('mainpage.html')

@app.route('/register')
def registerpage():
    return render_template('register.html')
@app.route('/leaderboard')
def leaderboard():  
    return render_template('leaderboard.html')

@app.route('/sampleq')
def sampleq():
    return render_template('sampleq.html')

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
def reset_tables():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Drop in reverse-dependency order
        cur.execute("DROP TABLE IF EXISTS user_completed_questions;")
        cur.execute("DROP TABLE IF EXISTS users;")
        conn.commit()

        # Recreate with your desired schema
        cur.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                score REAL DEFAULT 0
            );
        """)
        cur.execute("""
            CREATE TABLE user_completed_questions (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                code_length INTEGER DEFAULT 0,
                score REAL DEFAULT 0,
                UNIQUE(username, question_id)
            );
        """)
        conn.commit()
        cur.close()
        print("✅ Tables reset successfully.")
    finally:
        release_connection(conn)
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
                score REAL DEFAULT 0
            )
        ''')
    
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_completed_questions (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                code_length INTEGER DEFAULT 0,
                score REAL DEFAULT 0,
                UNIQUE(username, question_id)
            )
        ''')
        
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)

# Initialize the connection pool
init_connection_pool()
#reset_tables()  # Reset tables for development
# Create the table if it doesn't exist
create_table()

# Load questions from JSON
def load_questions():
    try:
        with open('static/questions.json', 'r') as file:
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

@app.route('/user_solutions', methods=['GET'])
def user_solutions():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Username is required"}), 400

    # Load question metadata once
    questions = load_questions()
    qmap = { q['id']: q for q in questions }

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
          SELECT question_id, code_length, score
          FROM user_completed_questions
          WHERE username = %s
          ORDER BY question_id
        """, (username,))
        rows = cur.fetchall()
        cur.close()
    finally:
        release_connection(conn)

    # Enrich
    result = []
    for qid, length, sc in rows:
        meta = qmap.get(qid, {})
        result.append({
            "question_id":      qid,
            "title":            meta.get('title'),
            "difficulty":       meta.get('difficulty'),
            "code_length":      length,
            "target_chars":     meta.get('target_chars'),
            "score":            sc
        })

    return jsonify(result)


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
    result = asyncio.run(run_code(code, language, expected_output, question_id))

    if result["correct"]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if this user has already solved this question
            cursor.execute(
                "SELECT id, score FROM user_completed_questions WHERE username = %s AND question_id = %s",
                (username, question_id)
            )
            already_completed = cursor.fetchone()
            
            # Get current user score
            cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            current_user_score = row[0] if row else 0
            
            if not already_completed:
                # This is the first time solving this question
                new_user_score = current_user_score + result["score"]
                
                # Update the user's total score
                cursor.execute(
                    "UPDATE users SET score = %s WHERE username = %s",
                    (new_user_score, username)
                )
                
                # Record the solution details
                cursor.execute(
                    "INSERT INTO user_completed_questions (username, question_id, code_length, score) VALUES (%s, %s, %s, %s)",
                    (username, question_id, result["code_length"], result["score"])
                )
                
                conn.commit()
                result["message"] = f"Correct! {result['message']} Score: {result['score']}. New total: {new_user_score} points"
            else:
                prev_score = already_completed[1]
                
                # Check if the new score is better
                if result["score"] > prev_score:
                    # Update the score difference in user's total
                    score_diff = result["score"] - prev_score
                    new_user_score = current_user_score + score_diff
                    
                    # Update the user's total score
                    cursor.execute(
                        "UPDATE users SET score = %s WHERE username = %s",
                        (new_user_score, username)
                    )
                    
                    # Update the solution record
                    cursor.execute(
                        "UPDATE user_completed_questions SET code_length = %s, score = %s WHERE username = %s AND question_id = %s",
                        (result["code_length"], result["score"], username, question_id)
                    )
                    
                    conn.commit()
                    result["message"] = f"Correct! {result['message']} Score improved by {score_diff} points! New total: {new_user_score} points"
                else:
                    result["message"] = f"Correct! {result['message']} But your previous solution had a better score ({prev_score} vs {result['score']}). Total points unchanged: {current_user_score}"
                
            cursor.close()
            
        except Exception as e:
            print(f"Database error: {e}")
            result["message"] = f"Solution correct, but there was an error updating your score: {str(e)}"
        finally:
            release_connection(conn)

    return jsonify(result)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)