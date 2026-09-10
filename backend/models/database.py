"""
Database persistence and connection management for TruLabel. (FR-9)
Provides zero-dependency SQLite persistence using Python's built-in sqlite3.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "trulabel.db"


def get_db_connection():
    """Returns a sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """FastAPI dependency for yielding database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initializes SQLite database tables matching the Design Document schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            category TEXT,
            sugars_100g REAL,
            additives_count INTEGER DEFAULT 0,
            nutriscore_grade TEXT,
            ingredients_text TEXT,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            brand TEXT,
            marketing_text TEXT,
            mas_score INTEGER,
            claims_json TEXT,
            evidence_json TEXT,
            report_text TEXT,
            created_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            claim_text TEXT NOT NULL,
            claim_type TEXT,
            FOREIGN KEY (report_id) REFERENCES reports(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS verdicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id INTEGER,
            result TEXT,
            explanation TEXT,
            source TEXT,
            regulation_ref TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims(id)
        )
        """
    )

    conn.commit()
    conn.close()


def save_verification_report(
    product_name: str,
    marketing_text: str,
    evidence: dict | None,
    result: dict,
) -> int | None:
    """
    Persists a verified product, its claims, and MAS verdict to the database.
    Returns the new report_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.utcnow().isoformat()

        product_id = None
        if evidence:
            cursor.execute(
                """
                INSERT INTO products (name, brand, category, sugars_100g, additives_count, nutriscore_grade, ingredients_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.get("name", product_name),
                    evidence.get("brand", "unknown"),
                    evidence.get("categories", ""),
                    evidence.get("sugars_100g"),
                    evidence.get("additives_count", 0),
                    evidence.get("nutriscore_grade"),
                    evidence.get("ingredients_text", ""),
                    now_str,
                ),
            )
            product_id = cursor.lastrowid

        claims = result.get("claims", [])
        claims_json = json.dumps(claims)
        evidence_json = json.dumps(evidence) if evidence else None

        cursor.execute(
            """
            INSERT INTO reports (product_id, product_name, brand, marketing_text, mas_score, claims_json, evidence_json, report_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                evidence.get("name", product_name) if evidence else product_name,
                evidence.get("brand", "unknown") if evidence else "unknown",
                marketing_text,
                result.get("MAS"),
                claims_json,
                evidence_json,
                result.get("report", ""),
                now_str,
            ),
        )
        report_id = cursor.lastrowid

        for c in claims:
            cursor.execute(
                """
                INSERT INTO claims (report_id, claim_text, claim_type)
                VALUES (?, ?, ?)
                """,
                (report_id, c.get("claim", ""), c.get("claim_type", "")),
            )
            claim_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO verdicts (claim_id, result, explanation, source, regulation_ref)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    claim_id,
                    c.get("result", ""),
                    c.get("explanation", ""),
                    c.get("source", ""),
                    c.get("regulation_ref", ""),
                ),
            )

        conn.commit()
        conn.close()
        return report_id
    except Exception as e:
        print(f"[database] Error saving report: {e}")
        return None


def get_recent_reports(limit: int = 10) -> list[dict]:
    """Retrieves recent verification reports."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, product_name, brand, mas_score, claims_json, created_at
        FROM reports
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        claims = json.loads(r["claims_json"]) if r["claims_json"] else []
        items.append({
            "report_id": r["id"],
            "product_name": r["product_name"],
            "brand": r["brand"],
            "mas_score": r["mas_score"],
            "claims_count": len(claims),
            "created_at": r["created_at"],
        })
    return items


def get_report_by_id(report_id: int) -> dict | None:
    """Retrieves detailed historical report by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, product_name, brand, marketing_text, mas_score, claims_json, evidence_json, report_text, created_at
        FROM reports
        WHERE id = ?
        """,
        (report_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "report_id": row["id"],
        "product_name": row["product_name"],
        "brand": row["brand"],
        "marketing_text": row["marketing_text"],
        "MAS": row["mas_score"],
        "claims": json.loads(row["claims_json"]) if row["claims_json"] else [],
        "evidence_used": json.loads(row["evidence_json"]) if row["evidence_json"] else None,
        "report": row["report_text"],
        "created_at": row["created_at"],
    }
