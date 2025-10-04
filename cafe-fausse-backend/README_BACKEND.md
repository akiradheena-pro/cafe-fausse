# Café Fausse — Backend API (Flask & PostgreSQL)

This repository contains the backend API for Café Fausse, a fictional fine-dining restaurant. The API is built with Flask and SQLAlchemy, powered by a PostgreSQL database, and is fully containerized with Docker for easy setup and deployment.

It provides endpoints for making reservations, checking table availability, managing newsletter subscriptions, and a simple admin view for listing daily bookings.

---

## Features

-   **Reservations:** Create and manage customer table reservations.
-   **Availability Check:** Real-time endpoint to check available tables for a given time slot.
-   **Newsletter:** Robust newsletter signup with atomic UPSERT logic to prevent duplicate entries.
-   **Admin View:** Secure endpoint for administrators to list all reservations for a specific day.
-   **Dockerized:** One-command startup using Docker Compose for the API and PostgreSQL database.
-   **Database Migrations:** Schema managed by Alembic, ensuring a single source of truth.
-   **Data Seeding:** Includes a CLI command to populate the database with realistic test data.
-   **Validated & Tested:** API endpoints feature robust input validation with Pydantic and are covered by a Pytest suite.

---

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose
-   A Unix-like shell (e.g., Git Bash on Windows, or any standard Linux/macOS terminal)

### Installation & Startup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-folder>/backend
    ```

2.  **Run the startup script:**
    This script will handle everything: create a `.env` file, build the Docker images, start the database, run migrations, and launch the API server.
    ```bash
    chmod +x start.sh
    ./start.sh
    ```

    Once complete, the API will be running and accessible.

    -   **Health Check:** `http://localhost:8000/health`
    -   **Base API URL:** `http://localhost:8000/api`

---

## Usage

### Configuration

Environment variables are managed in the `.env` file. A `.env.example` is provided as a template.

-   `DATABASE_URL`: Connection string for the PostgreSQL database.
-   `PORT`: The port on which the Flask API will run.
-   `SLOT_MINUTES`: The duration of a reservation slot (e.g., 30 minutes).
-   `TOTAL_TABLES`: The total number of tables available in the restaurant.
-   `ADMIN_TOKEN`: A secret bearer token for accessing admin-only endpoints.

### Populating the Database (Seeding)

To fill the database with sample customers and reservations for development, run the following command:

```bash
docker compose exec api flask seed
```

### Running Tests

The project includes a black-box test suite using Pytest. To run the tests:

1.  Ensure the application is running via `./start.sh`.
2.  Install development dependencies:
    ```bash
    pip install -r requirements-dev.txt
    ```
3.  Run Pytest:
    ```bash
    pytest
    ```

---

## API Endpoints

A brief overview of the available endpoints. For full details, see the API reference or source code.

#### Health Check

-   `GET /health`
    -   **Description:** Checks if the API is running and available.
    -   **Success Response (200 OK):** `{"status": "ok"}`

#### Reservations

-   `GET /api/reservations/availability?time=<ISO_8601_STRING>`
    -   **Description:** Checks how many tables are available for a given time slot.
-   `POST /api/reservations`
    -   **Description:** Creates a new reservation.
-   `GET /api/reservations?date=<YYYY-MM-DD>`
    -   **Description:** (Admin only) Lists all reservations for a given date. Supports pagination and filtering.
    -   **Headers:** `Authorization: Bearer <your_admin_token>`
    -   **Query Params:** `page`, `page_size`, `customer_email`.

#### Newsletter

-   `POST /api/newsletter`
    -   **Description:** Subscribes a user to the newsletter. If the email already exists, it updates their opt-in status.

---

## Contributing

Contributions are welcome. Please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Ensure all tests pass (`pytest`).
5.  Commit your changes (`git commit -m 'Add some feature'`).
6.  Push to the branch (`git push origin feature/your-feature-name`).
7.  Open a Pull Request.


