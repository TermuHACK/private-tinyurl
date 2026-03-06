import os
import shortuuid
import psutil

from flask import Flask,request,redirect,session
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet

# CONFIG

DB_URL = os.getenv("DB_URL","postgresql://tiny:tiny@localhost/tinydb")
ADMIN_PASS = os.getenv("ADMIN_PASS","admin")
ENC_KEY = os.getenv("ENC_KEY")

if not ENC_KEY:
    ENC_KEY = Fernet.generate_key()
else:
    ENC_KEY = ENC_KEY.encode()

fernet = Fernet(ENC_KEY)

# APP

app = Flask(__name__)
app.secret_key="secret"

app.config["SQLALCHEMY_DATABASE_URI"]=DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

db = SQLAlchemy(app)

# MODEL

class Link(db.Model):

    id = db.Column(db.Integer,primary_key=True)
    code = db.Column(db.String(10),unique=True)
    url = db.Column(db.Text)
    clicks = db.Column(db.Integer,default=0)

# INIT DB

with app.app_context():
    db.create_all()

# LOGIN

@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":
        if request.form.get("password")==ADMIN_PASS:
            session["auth"]=True
            return redirect("/admin")

    return """
    <h2>TinyURL login</h2>
    <form method=post>
    <input type=password name=password placeholder=password>
    <button>login</button>
    </form>
    """

# ADMIN

@app.route("/admin",methods=["GET","POST"])
def admin():

    if not session.get("auth"):
        return redirect("/")

    if request.method=="POST":

        url=request.form.get("url")

        code=shortuuid.ShortUUID().random(length=6)

        enc=fernet.encrypt(url.encode()).decode()

        link=Link(code=code,url=enc)

        db.session.add(link)
        db.session.commit()

    links=Link.query.all()

    html="""

    <h2>TinyURL admin</h2>

    <form method=post>
    <input name=url placeholder="url">
    <button>shorten</button>
    </form>

    <h3>Links</h3>
    """

    for l in links:

        url=fernet.decrypt(l.url.encode()).decode()

        html+=f"""
        <div>
        <b>/{l.code}</b>
        → {url}
        | clicks: {l.clicks}
        </div>
        """

    html+="""

    <h3>Container stats</h3>

    <canvas id=chart width=300 height=300></canvas>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>

    fetch('/stats')
    .then(r=>r.json())
    .then(d=>{

        new Chart(document.getElementById('chart'),{

            type:'doughnut',

            data:{
                labels:['CPU','RAM'],
                datasets:[{
                    data:[d.cpu,d.ram]
                }]
            }

        })

    })

    </script>

    """

    return html

# REDIRECT

@app.route("/<code>")
def go(code):

    l=Link.query.filter_by(code=code).first()

    if not l:
        return "404"

    l.clicks+=1
    db.session.commit()

    url=fernet.decrypt(l.url.encode()).decode()

    return redirect(url)

# STATS

@app.route("/stats")
def stats():

    cpu=psutil.cpu_percent()
    ram=psutil.virtual_memory().percent

    return {"cpu":cpu,"ram":ram}

# RUN

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080)
