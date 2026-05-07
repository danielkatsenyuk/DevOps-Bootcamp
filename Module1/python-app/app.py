import os
import logging
import base64
import secrets
import time
import json
import boto3
import mysql.connector
from flask import Flask, jsonify, request

app = Flask(__name__)

LOG_FILE = "/app/logs/app.log"
AWS_REGION = "us-east-1"
SECRET_NAME = "task1-dev-us-east-1-daniel-katsenyuk-generated-token"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mysql-service.mysql.svc.cluster.local"),       
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "secret"),
        database=os.getenv("MYSQL_DATABASE", "app_db")
    )

def init_db():
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
    token = secrets.token_urlsafe(32)
    b64_token = base64.b64encode(token.encode()).decode()
    
    secret_data = {
        "token": b64_token,
        "created_at": time.time()
    }
    
    try:
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        client.put_secret_value(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(secret_data)
        )
        logging.info("Token generated and saved to AWS Secrets Manager successfully.")
        return jsonify({
            "message": "System Unlocked for 10 minutes",
            "token": b64_token, 
            "expires_in": "10 minutes"
        })
    except Exception as e:
        logging.error(f"Failed to save token to AWS: {e}")
        return jsonify({"error": "Failed to save token to AWS"}), 500

@app.route('/track', methods=['GET', 'POST']) 
def track_request():
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
    try:
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=SECRET_NAME)
        secret_string = response.get('SecretString', '{}')
        
        secret_data = json.loads(secret_string)
        created_at = secret_data.get("created_at", 0)
        
        time_passed = time.time() - created_at
        
        if time_passed <= 600:
            logging.info(f"System UNLOCKED. Token is valid ({int(time_passed)} seconds old).")
            return jsonify({"status": "valid"}), 200
        else:
            logging.error(f"System LOCKED. Token expired ({int(time_passed)} seconds old).")
            return jsonify({"error": "Token expired"}), 401
            
    except Exception as e:
        logging.error(f"Token validation failed at AWS: {e}")
        return jsonify({"error": "Failed to validate token with AWS"}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM requests")
        count = cursor.fetchone()[0]
        conn.close()
        
        metrics_data = f"# HELP app_requests_total The total number of requests in the DB.\n"
        metrics_data += f"# TYPE app_requests_total gauge\n"
        metrics_data += f"app_requests_total {count}\n"
        
        return metrics_data, 200, {'Content-Type': 'text/plain; version=0.0.4'}
    except Exception as e:
        logging.error(f"Metrics failed: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)