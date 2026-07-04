import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-helpdesk-secret")


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    schema = """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """
    connection = None

    try:
        connection = get_connection()
        connection.execute(schema)
        connection.commit()
    except sqlite3.DatabaseError:
        if connection:
            connection.close()

        backup_path = DATABASE.with_suffix(".db.bak")
        if DATABASE.exists():
            DATABASE.replace(backup_path)

        with get_connection() as connection:
            connection.execute(schema)
    finally:
        if connection:
            connection.close()


def fetch_tickets():
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM tickets ORDER BY id DESC"
        ).fetchall()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        issue_type = request.form.get("issue_type", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        description = request.form.get("description", "").strip()

        if not all([name, department, issue_type, priority, description]):
            flash("Please complete all ticket details before submitting.", "error")
            return redirect(url_for("home"))

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO tickets
                    (name, department, issue_type, priority, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                """,
                (
                    name,
                    department,
                    issue_type,
                    priority,
                    description,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                ),
            )

        flash("Ticket submitted successfully.", "success")
        return redirect(url_for("tickets"))

    return render_template("index.html")


@app.route("/tickets")
def tickets():

    search = request.args.get("search", "")

    with get_connection() as connection:

        tickets = connection.execute(
            """
            SELECT *
            FROM tickets
            WHERE name LIKE ?
            OR department LIKE ?
            OR issue_type LIKE ?
            ORDER BY id DESC
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()

    return render_template(
        "tickets.html",
        tickets=tickets,
        search=search
    )


@app.route("/dashboard")
def dashboard():
    tickets_list = fetch_tickets()
    total_tickets = len(tickets_list)
    pending_tickets = sum(1 for ticket in tickets_list if ticket["status"] == "Pending")
    resolved_tickets = sum(1 for ticket in tickets_list if ticket["status"] == "Resolved")
    high_priority_tickets = sum(
        1 for ticket in tickets_list if ticket["priority"] in ["High", "Critical"]
    )

    department_counts = {}
    for ticket in tickets_list:
        department = ticket["department"]
        department_counts[department] = department_counts.get(department, 0) + 1

    return render_template(
        "dashboard.html",
        tickets=tickets_list,
        total_tickets=total_tickets,
        pending_tickets=pending_tickets,
        resolved_tickets=resolved_tickets,
        high_priority_tickets=high_priority_tickets,
        department_counts=department_counts,
    )


@app.route("/resolve/<int:ticket_id>", methods=["POST"])
def resolve_ticket(ticket_id):
    with get_connection() as connection:
        connection.execute(
            "UPDATE tickets SET status = 'Resolved' WHERE id = ?",
            (ticket_id,),
        )

    flash("Ticket marked as resolved.", "success")
    return redirect(url_for("tickets"))


@app.route("/login")
def login():
    return render_template("login.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
@app.route("/delete/<int:ticket_id>", methods=["POST"])
def delete_ticket(ticket_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM tickets WHERE id = ?",
            (ticket_id,)
        )

    flash("Ticket deleted successfully!", "success")
    return redirect(url_for("tickets"))
@app.route("/progress/<int:ticket_id>", methods=["POST"])
def progress_ticket(ticket_id):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET status = 'In Progress'
            WHERE id = ?
            """,
            (ticket_id,)
        )

    flash("Ticket marked as In Progress!", "success")
    return redirect(url_for("tickets"))