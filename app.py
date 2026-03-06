import os
import psycopg2
import bcrypt
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)

DB_URL = os.getenv("DB_URL")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS links (
 id SERIAL PRIMARY KEY,
 code TEXT UNIQUE NOT NULL,
 target_url TEXT NOT NULL,
 password_hash TEXT NOT NULL
)
""")

conn.commit()


login_html = """
<h2>Access {{code}}</h2>
<form method="post">
<input type="password" name="password" placeholder="password">
<button type="submit">Login</button>
</form>
"""


@app.route("/create", methods=["GET","POST"])
def create():

    if request.method == "POST":

        code = request.form["code"]
        url = request.form["url"]
        password = request.form["password"]

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        cur.execute(
        "INSERT INTO links(code,target_url,password_hash) VALUES(%s,%s,%s)",
        (code,url,pw_hash)
        )

        conn.commit()

        return "created"

    return """
    <h2>Create link</h2>
    <form method="post">
    code <input name="code"><br>
    url <input name="url"><br>
    password <input name="password"><br>
    <button>Create</button>
    </form>
    """


@app.route("/<code>", methods=["GET","POST"])
def access(code):

    if request.method == "GET":
        return render_template_string(login_html, code=code)

    password = request.form["password"]

    cur.execute(
    "SELECT target_url,password_hash FROM links WHERE code=%s",
    (code,)
    )

    row = cur.fetchone()

    if not row:
        return "not found",404

    url, pw_hash = row

    if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        return "wrong password",403

    return redirect(url)


app.run(host="0.0.0.0", port=8080)
