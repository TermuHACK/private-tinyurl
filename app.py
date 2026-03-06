import os
import shortuuid
import psutil

from flask import Flask,request,redirect,session
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash,check_password_hash

# CONFIG

DB_URL=os.getenv("DB_URL","sqlite:///tiny.db")
ENC_KEY=os.getenv("ENC_KEY")

if not ENC_KEY:
    ENC_KEY=Fernet.generate_key()
else:
    ENC_KEY=ENC_KEY.encode()

fernet=Fernet(ENC_KEY)

app=Flask(__name__)
app.secret_key="secret"

app.config["SQLALCHEMY_DATABASE_URI"]=DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

db=SQLAlchemy(app)

# MODELS

class Link(db.Model):

    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(50),unique=True)
    url=db.Column(db.Text)
    clicks=db.Column(db.Integer,default=0)


class Config(db.Model):

    id=db.Column(db.Integer,primary_key=True)
    password=db.Column(db.Text)


# INIT

with app.app_context():

    db.create_all()

    if not Config.query.first():

        p=os.getenv("ADMIN_PASS","admin")

        c=Config(password=generate_password_hash(p))

        db.session.add(c)
        db.session.commit()

# LOGIN

@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":

        password=request.form.get("password")

        c=Config.query.first()

        if check_password_hash(c.password,password):

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
        code=request.form.get("code")

        if not code:
            code=shortuuid.ShortUUID().random(length=6)

        enc=fernet.encrypt(url.encode()).decode()

        link=Link(code=code,url=enc)

        db.session.add(link)
        db.session.commit()

    links=Link.query.all()

    html="""

    <h2>TinyURL admin</h2>

    <h3>Create link</h3>

    <form method=post>
    <input name=url placeholder="url">
    <input name=code placeholder="custom endpoint (optional)">
    <button>create</button>
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

    <h3>Change password</h3>

    <form method=post action="/password">

    <input type=password name=new placeholder="new password">

    <button>change</button>

    </form>

    <h3>Container stats</h3>

    <div style="width:300px;height:300px">
    <canvas id="chart"></canvas>
    </div>

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
            },

            options:{
                responsive:false
            }

        })

    })

    </script>

    """

    return html


# PASSWORD CHANGE

@app.route("/password",methods=["POST"])
def password():

    if not session.get("auth"):
        return redirect("/")

    new=request.form.get("new")

    c=Config.query.first()

    c.password=generate_password_hash(new)

    db.session.commit()

    return redirect("/admin")


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
