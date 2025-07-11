import os
import logging
import sqlite3
import mysql.connector
from typing import Optional, List, Dict

from dotenv import load_dotenv

load_dotenv()
logging.getLogger().setLevel(logging.INFO)
run_mode = os.getenv("RUN_MODE")


def connect_db():
    """Gets a database connection."""
    if run_mode == "RENDER":
        db_path = "/var/tmp/app_database.db"
        conn = sqlite3.connect(db_path)
        return conn
    else:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return conn


def init_db():
    """Initializes the database by creating the table if it doesn't exist."""
    default_endpoints = [
        ("Gesis", "Social science research data", "https://data.gesis.org/gesiskg/sparql"),
        ("Swiss Art Research - BSO", "Swiss art and cultural heritage knowledge graph", "https://bso.swissartresearch.net/sparql"),
        ("Smithsonian Art Museum KG", "Smithsonian Institution art and cultural collections", "https://triplydb.com/smithsonian/american-art-museum/sparql"),
    ]
    conn = connect_db()
    try:
        cursor = conn.cursor()
        auto_increment = "INT PRIMARY KEY AUTO_INCREMENT" if run_mode != "RENDER" else "INTEGER PRIMARY KEY AUTOINCREMENT"

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS submissions (
                id {auto_increment},
                kg_endpoint TEXT NOT NULL,
                nl_question TEXT NOT NULL,
                sparql_query TEXT,
                username TEXT
            )
        """)
        conn.commit()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS kg_endpoints (
                id {auto_increment},
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        mid_str = "%s" if run_mode != "RENDER" else "?"
        for name, description, endpoint in default_endpoints:
            cursor.execute(f"""
                INSERT INTO kg_endpoints (name, description, endpoint)
                SELECT {mid_str}, {mid_str}, {mid_str}
                WHERE NOT EXISTS (
                    SELECT 1 FROM kg_endpoints WHERE name = {mid_str} OR endpoint = {mid_str}
                )
            """, (name, description, endpoint, name, endpoint))
            conn.commit()

        logging.info("Database initialized for submissions and endpoints.")
    finally:
        cursor.close()
        conn.close()


def insert_submission(kg_endpoint: str, nl_question: str, email: str, sparql_query: Optional[str]):
    """Inserts a new submission into the database."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        suffix = "(%s, %s, %s, %s)" if run_mode != "RENDER" else "(?, ?, ?, ?)"
        cursor.execute(
            f"INSERT INTO submissions (kg_endpoint, nl_question, username, sparql_query) VALUES {suffix}",
            (kg_endpoint, nl_question, email, sparql_query)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_kg_endpoint(name: str, description: str, endpoint: str):
    """Inserts a new KG endpoint into the database."""
    conn = connect_db()
    print(f"Inserting KG endpoint: {name}, {description}, {endpoint}")
    try:
        cursor = conn.cursor()
        suffix = "(%s, %s, %s)" if run_mode != "RENDER" else "(?, ?, ?)"
        cursor.execute(
            f"INSERT INTO kg_endpoints (name, description, endpoint) VALUES {suffix}",
            (name, description, endpoint)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_if_endpoint_exists(endpoint: str) -> bool:
    """Checks if a KG endpoint exists in the database."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        suffix = "WHERE endpoint = %s" if run_mode != "RENDER" else "WHERE endpoint = ?"
        cursor.execute(f"SELECT COUNT(*) FROM kg_endpoints {suffix}", (endpoint,))
        return cursor.fetchone()[0] > 0 
    finally:
        cursor.close()
        conn.close()


def get_all_submissions() -> List[Dict]:
    """Retrieves all submissions from the database."""
    conn = connect_db()
    try:
        if run_mode == "RENDER":
            conn.row_factory = sqlite3.Row

        cursor = conn.cursor(dictionary=True) if run_mode != "RENDER" else conn.cursor()
        cursor.execute("SELECT id, kg_endpoint, nl_question, sparql_query, username FROM submissions")
        return cursor.fetchall() if run_mode != "RENDER" else [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_all_kg_metadata(for_one: bool = False, endpoint: str = None) -> List[Dict]:
    """Retrieves all KG endpoints from the database."""
    conn = connect_db()
    try:
        if run_mode == "RENDER":
            conn.row_factory = sqlite3.Row

        cursor = conn.cursor(dictionary=True) if run_mode != "RENDER" else conn.cursor()
        if not for_one:
            cursor.execute("SELECT id, name, description, endpoint FROM kg_endpoints")
            return cursor.fetchall() if run_mode != "RENDER" else [dict(row) for row in cursor.fetchall()]
        else:
            suffix = "WHERE endpoint = %s" if run_mode != "RENDER" else "WHERE endpoint = ?"
            cursor.execute(f"SELECT name, description, endpoint FROM kg_endpoints {suffix}", (endpoint,))
            return cursor.fetchone() if run_mode != "RENDER" else dict(cursor.fetchone())
    finally:
        cursor.close()
        conn.close()


def get_unique_kg_endpoints() -> List[str]:
    """Retrieves a list of unique KG endpoints in the database."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT endpoint FROM kg_endpoints")
        res = [row[0] for row in cursor.fetchall()]
        return sorted(res)
    finally:
        cursor.close()
        conn.close()


def get_submission(id_submission: str) -> Dict:
    """Retrieves a submission by its ID."""
    conn = connect_db()
    try:
        cursor = conn.cursor(dictionary=True) if run_mode != "RENDER" else conn.cursor()
        suffix = "WHERE id = %s" if run_mode != "RENDER" else "WHERE id = ?"
        cursor.execute(
            f"SELECT id, kg_endpoint, nl_question, sparql_query, username FROM submissions {suffix}",
            (id_submission,)
        )
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def get_submissions_by_kg(kg_endpoint: str) -> List[Dict]:
    """Retrieves submissions for a specific KG endpoint."""
    conn = connect_db()
    try:
        if run_mode == "RENDER":
            conn.row_factory = sqlite3.Row

        cursor = conn.cursor(dictionary=True) if run_mode != "RENDER" else conn.cursor()
        suffix = "WHERE kg_endpoint = %s" if run_mode != "RENDER" else "WHERE kg_endpoint = ?"
        cursor.execute(
            f"SELECT id, kg_endpoint, nl_question, sparql_query, username FROM submissions {suffix}",
            (kg_endpoint,)
        )
        return cursor.fetchall() if run_mode != "RENDER" else [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def modify_submission(kg_endpoint: str, id_submission: str, email: str, nl_question: Optional[str], sparql_query: Optional[str]):
    """Modifies a submission in the database."""
    conn = connect_db()
    try:
        cursor = conn.cursor(dictionary=True) if run_mode != "RENDER" else conn.cursor()
        if not nl_question and not sparql_query:
            return

        if sparql_query and nl_question:
            cursor.execute(
                """
                UPDATE submissions
                SET nl_question = ?, sparql_query = ?
                WHERE id = ? and username = ? and kg_endpoint = ?;
                """,
                (nl_question, sparql_query, id_submission, email, kg_endpoint)
            )

        if sparql_query:
            cursor.execute(
                """
                UPDATE submissions
                SET sparql_query = ?
                WHERE id = ? and username = ? and kg_endpoint = ?;
                """,
                (sparql_query, id_submission, email, kg_endpoint)
            )

        if nl_question:
            cursor.execute(
                """
                UPDATE submissions
                SET nl_question = ?
                WHERE id = ? and username = ? and kg_endpoint = ?;
                """,
                (nl_question, id_submission, email, kg_endpoint)
            )

        conn.commit()
    finally:
        cursor.close()
        conn.close()
