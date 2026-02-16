import os
import logging
import base64
import secrets
import time
import mysql.connector
from flask import Flask, jsonify, request

app = Flask(__name__)


LOG_FILE = "/app/logs/app.log"
TOKEN_FILE = "/app/tokens/auth_token"


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def get_db_connection():
    return mysql.connector.connect(
        host="mysql-db",       
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "secret"),
        database=os.getenv("MYSQL_DATABASE", "app_db")
    )

def init_db():
    """
    Initializes the MySQL database with the required 'requests' table.
    Includes a retry mechanism to handle race conditions where MySQL 
    might not be fully ready when the Python container starts.
    """
    retries = 10
    while retries > 0:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    endpoint VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully.")
            return
        except Exception as e:
            retries -= 1
            logging.error(f"DB Init failed: {e}. Retrying in 5 seconds... ({retries} left)")
            time.sleep(5)
    logging.error("Could not initialize DB after multiple retries.")

init_db()

@app.route('/token', methods=['GET'])
def generate_token():
    """
    Generates a secure, random base64 token.
    Stores the token in a shared volume file ('auth_token') 
    to be verified later. The file timestamp serves as the start time.
    """
    token = secrets.token_urlsafe(32)
    b64_token = base64.b64encode(token.encode()).decode()
    
    with open(TOKEN_FILE, "w") as f:
        f.write(b64_token)
    
    logging.info("Token generated successfully.")
    return jsonify({"token": b64_token, "expires_in": "10 minutes"})

@app.route('/track', methods=['POST']) 
def track_request():
    """
    Logs a 'track' event to the MySQL database.
    This endpoint is protected by Nginx auth_request.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO requests (endpoint) VALUES ('track')")
        conn.commit()
        conn.close()
        
        logging.info("Track request logged to DB.")
        return jsonify({"message": "Request tracked in DB"})
    except Exception as e:
        logging.error(f"Track failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/count', methods=['GET'])
def count_requests():
    """
    Returns the total count of requests logged in the database.
    This endpoint is protected by Nginx auth_request.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM requests")
        count = cursor.fetchone()[0]
        conn.close()
        
        logging.info(f"Count requested. Total: {count}")
        return jsonify({"count": count})
    except Exception as e:
        logging.error(f"Count failed: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/validate_token', methods=['GET'])
def validate_token():
    """
    Internal endpoint used by Nginx (via auth_request) to verify tokens.
    Checks if:
    1. Authorization header exists.
    2. Token file exists.
    3. Token is not expired (> 10 minutes).
    4. Token matches the stored value.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Missing Authorization Header"}), 401
    
    if not os.path.exists(TOKEN_FILE):
        return jsonify({"error": "No token generated yet"}), 401

    # Check expiration (10 minutes = 600 seconds)
    file_mod_time = os.path.getmtime(TOKEN_FILE)
    if time.time() - file_mod_time > 600:
        return jsonify({"error": "Token expired"}), 401

    with open(TOKEN_FILE, "r") as f:
        stored_token = f.read().strip()
    
    if auth_header == stored_token:
        return jsonify({"status": "valid"}), 200
    else:
        return jsonify({"error": "Invalid token"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)