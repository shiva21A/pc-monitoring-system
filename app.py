ADMIN_EMAIL = "sshivpajan6560@gmail.com"   # <-- अपना admin email
ADMIN_PASSWORD = "1234"            # <-- simple password



from flask import Flask, render_template, request, redirect, session
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory
import os


app = Flask(__name__)

app.secret_key = "PC_MONITOR_SECRET_2026"

def get_db():
    return sqlite3.connect("/home/ubuntu/pc-monitoring/server/database.db")


def generate_api_key():
    return secrets.token_hex(16)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        # 1️⃣ check duplicate email
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            db.close()
            return "Email already registered"

        # 2️⃣ hash password
        hashed_password = generate_password_hash(password)

        # 3️⃣ generate API key
        api_key = generate_api_key()

        # 4️⃣ insert user with api key
        cur.execute(
            "INSERT INTO users (email, password, api_key) VALUES (?, ?, ?)",
            (email, hashed_password, api_key)
        )

        db.commit()
        db.close()

        # 5️⃣ login user
        session["user"] = email

        # 6️⃣ redirect dashboard
        return redirect("/dashboard")

    return render_template("register.html")

@app.route("/api/pc-data", methods=["POST"])
def receive_pc_data():
    try:
        data = request.get_json(force=True)

        api_key = data["api_key"]
        cpu = data.get("cpu")
        ram = data.get("ram")
        battery = data.get("battery")
        ip = data.get("ip")
        brand = data.get("brand")

        db = get_db()
        cur = db.cursor()

        cur.execute("SELECT id FROM users WHERE api_key = ?", (api_key,))
        if not cur.fetchone():
            db.close()
            return {"error": "Invalid API key"}, 401

        cur.execute("""
            INSERT INTO pc_stats
            (api_key, cpu, ram, battery, ip, brand, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (api_key, cpu, ram, battery, ip, brand))

        db.commit()
        db.close()

        return {"status": "ok"}, 200

    except Exception as e:
        print("API ERROR:", e)
        return {"error": str(e)}, 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()

        cur.execute("SELECT password FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        db.close()

        if user and check_password_hash(user[0], password):
            session["user"] = email
            return redirect("/dashboard")
        else:
            return "Invalid email or password"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]
    print("DASHBOARD EMAIL =", email)

    db = get_db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # 🔹 Get user's API key
    cur.execute(
        "SELECT api_key FROM users WHERE email = ?",
        (email,)
    )
    user = cur.fetchone()

    if not user:
        db.close()
        return "API key not found for user"

    api_key = user["api_key"]
    print("API KEY =", api_key)

    # 🔹 Fetch PC stats with Indian Time (IST)
    cur.execute("""
        SELECT
            cpu,
            ram,
            battery,
            ip,
            brand,
            datetime(last_seen, '+5 hours', '+30 minutes') AS last_seen
        FROM pc_stats
        WHERE api_key = ?
        ORDER BY id DESC
        LIMIT 20
    """, (api_key,))

    rows = cur.fetchall()
    print("ROWS FROM DB =", rows)

    pcs = []
    for r in rows:
        pcs.append({
            "cpu": r["cpu"],
            "ram": r["ram"],
            "battery": r["battery"],
            "ip": r["ip"],
            "brand": r["brand"],
            "last_seen": r["last_seen"]  # ✅ IST time
        })

    print("PCS SENT TO TEMPLATE =", pcs)

    db.close()

    return render_template(
        "dashboard.html",
        api_key=api_key,
        pcs=pcs
    )
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT password FROM users WHERE email=?", (email,))
        row = cur.fetchone()
        db.close()

        if not row or email != ADMIN_EMAIL:
            return "Not admin"

        if not check_password_hash(row[0], password):
            return "Wrong password"

        session["admin"] = email
        return redirect("/admin")

    return render_template("admin_login.html")


@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/admin-login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT u.email, p.cpu, p.ram, p.battery, p.ip, p.brand,
        datetime(p.last_seen, '+5 hours', '+30 minutes')
        FROM users u
        JOIN pc_stats p ON u.api_key = p.api_key
        WHERE p.id IN (
            SELECT MAX(id) FROM pc_stats GROUP BY api_key
        )
    """)
    rows = cur.fetchall()
    db.close()

    return render_template("admin.html", users=rows)


@app.route("/download/agent")
def download_agent():
    if "user" not in session:
        return redirect("/login")

    agents_dir = os.path.join(os.getcwd(), "agent")
    return send_from_directory(
        directory=agents_dir,
        path="agent.py",
        as_attachment=True
    )




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run()
