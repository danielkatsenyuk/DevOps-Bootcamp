# Module 1 - Docker: Secure Token System

## Project Overview
This project demonstrates a secure, containerized web application using **Docker** and **Python (Flask)**. It implements a secure token authentication system where an **Nginx** reverse proxy validates requests against the Python backend before allowing access to protected endpoints.

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

## Prerequisites
- Docker
- Docker Compose

## Installation & Usage

1.  **Clone the repository** (if applicable) or navigate to the project folder.
2.  **Build and Start** the containers:
    ```bash
    docker-compose up --build
    ```
3.  The application will be available at `http://localhost:8080`.

## API Documentation

### 1. Generate Token
Generates a secure, base64-encoded token valid for 10 minutes.

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
Logs a request to the database. Requires a valid token.

- **URL**: `/track`
- **Method**: `POST`
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

## Design Decisions

### Nginx `auth_request`
Instead of implementing authentication logic in every endpoint or using a complex API Gateway, we leverage Nginx's `auth_request` module.
- **How it works**: For every request to `/` or Protected Endpoints, Nginx makes a purely internal sub-request to `/validate_token` (mapped to Python's `/validate_token`).
- **Benefit**: Decouples authentication enforcement from business logic. Nginx acts as a tough gatekeeper.

### Token Expiration
Tokens are valid for **10 minutes**.
- **Implementation**: The Python app checks the filesystem modification time of the token file (`auth_token`). If `Time.now() - File.mtime > 600 seconds`, the token is rejected.
- **Why**: Simple, stateless (no complex redis/db required for TTL), and effective for this scope.
