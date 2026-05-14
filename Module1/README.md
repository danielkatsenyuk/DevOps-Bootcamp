# Module 1 – Docker: Secure Token System

## Project Overview
This project demonstrates a secure, containerized web application using **Docker** and **Python (Flask)**. It implements a token authentication system where an **Nginx** reverse proxy validates every request against the Python backend using `auth_request` before forwarding to protected endpoints. Tokens are stored in **AWS Secrets Manager** and expire after 10 minutes.

## Architecture

The system consists of three isolated containers:

1.  **Nginx Proxy (`nginx-proxy`)**:
    - Acts as the entry point (Port 8080).
    - Handles Reverse Proxying to the Python App.
    - **Security Feature**: Uses `auth_request` to verify tokens with the Python App before serving protected routes.
    - Connected to the `front-net`.

2.  **Python Application (`python-container`)**:
    - A Flask API that handles business logic.
    - Generates and Validates secure tokens.
    - Logs requests to MySQL.
    - Connected to both `front-net` (to talk to Nginx) and `back-net` (to talk to MySQL).

3.  **MySQL Database (`mysql-db`)**:
    - Stores request logs (`requests` table).
    - Isolated in the `back-net` (not accessible from Nginx directly).

## Installation & Usage

1. **Copy the env example** and fill in your values:
    ```bash
    cp mysql-db/.env.example mysql-db/.env
    # Edit mysql-db/.env with your passwords
    ```
2. **Build and Start** the containers:
    ```bash
    docker-compose up --build
    ```
3. The application will be available at `http://localhost:8080`.

## API Documentation

### 1. Generate Token
Generates a secure, base64-encoded token valid for 10 minutes and stores it in **AWS Secrets Manager**.

- **URL**: `/token`
- **Method**: `GET`
- **Response**:
    ```json
    {
        "token": "...",
        "expires_in": "10 minutes"
    }
    ```

### 2. Track Request (Protected)
Logs a request to the MySQL database. Requires a valid token.

- **URL**: `/track`
- **Method**: `GET` or `POST`
- **Headers**:
    - `Authorization`: `<your_token>`
- **Response**:
    - `200 OK`: `{"message": "Request tracked in DB"}`
    - `401 Unauthorized`: If token is missing, invalid, or expired.

### 3. Count Requests (Protected)
Returns the total number of tracked requests from the database.

- **URL**: `/count`
- **Method**: `GET`
- **Headers**:
    - `Authorization`: `<your_token>`
- **Response**:
    ```json
    {
        "count": 42
    }
    ```

### 4. Metrics (Prometheus)
Exposes the request count as a Prometheus gauge metric.

- **URL**: `/metrics`
- **Method**: `GET`
- **Response**: Prometheus text format (`app_requests_total`)

## Design Decisions

### Nginx `auth_request`
Nginx delegates authentication to the Python app using the `auth_request` module.
- For every request to a protected route, Nginx makes an internal sub-request to `/validate_token`.
- If the response is `200`, the original request is forwarded. If `401`, the client is rejected.
- The `/token` endpoint bypasses auth so users can obtain a new token.

### Token Storage (AWS Secrets Manager)
Tokens are generated with `secrets.token_urlsafe(32)`, base64-encoded, and stored in AWS Secrets Manager.
- The secret stores both the token value and the `created_at` timestamp as JSON.
- `/validate_token` reads the secret and checks `time.now() - created_at <= 600 seconds`.
- Tokens are **not** written to logs (only `"Token generated"` is logged, not the token value).

### Network Isolation
Two Docker networks enforce the principle of least privilege:
- **`front-net`**: Nginx ↔ Python App only
- **`back-net`**: Python App ↔ MySQL only
- Nginx **cannot** reach MySQL directly.
