import sqlite3
import os

def create_registry(db_path="data/registry.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS property_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_number TEXT NOT NULL,
        village TEXT,
        taluk TEXT,
        district TEXT,
        current_owner TEXT NOT NULL,
        last_transaction_type TEXT,      -- 'Sale Deed', 'Gift Deed', 'Mortgage', etc.
        last_transaction_date TEXT,      -- ISO format YYYY-MM-DD
        document_number TEXT,
        status TEXT DEFAULT 'ACTIVE'     -- ACTIVE / DISPUTED / ENCUMBERED
    )
    """)
    
    # Clear existing data just in case
    cur.execute("DELETE FROM property_records")

    # Sample seed data
    sample_records = [
        ("45/1", "Whitefield", "Bengaluru East", "Bengaluru Urban",
         "Rahul Sharma", "Sale Deed", "2026-03-15", "DOC2026-00123", "ACTIVE"),
        ("45/2", "Whitefield", "Bengaluru East", "Bengaluru Urban",
         "Anita Rao", "Sale Deed", "2025-11-02", "DOC2025-08876", "ACTIVE"),
        ("78/3", "Marathahalli", "Bengaluru East", "Bengaluru Urban",
         "Suresh Kumar", "Mortgage", "2024-07-20", "DOC2024-04532", "ENCUMBERED"),
    ]

    cur.executemany("""
        INSERT INTO property_records
        (survey_number, village, taluk, district, current_owner,
         last_transaction_type, last_transaction_date, document_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_records)

    conn.commit()
    conn.close()
    print(f"Registry created at {db_path} with {len(sample_records)} sample records.")

if __name__ == "__main__":
    create_registry()
