from flask import Flask, render_template, request,redirect,flash,abort,url_for
import pymysql
from dynaconf import Dynaconf
import flask_login


app = Flask(__name__)

conf = Dynaconf(
    settings_file = ['settings.toml']
)





login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view =('/signin')

class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True
    
    def __init__(self, user_id, username,email,first_name,last_name):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

    def get_id(self) :
        return str(self.user_id)   
    


@login_manager.user_loader    
def load_user(user_id):
    conn = connect_db()
    cursor =conn.cursor()
    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id};")
    result = cursor.fetchone()
    cursor.close
    conn.close

    if result is not None:
        return User(result['id'], result['username'], result['email'],result['first_name'],result['last_name'])

def connect_db ():
    conn =pymysql.connect(
        host= "db.steamcenter.tech",
        name= "pantryfy",
        user = "ldore",
        password = conf.password,
        autocommit= True,
        cursorclass= pymysql.cursors.DictCursor, )
    return conn




@app.route("/")
def index():
    return render_template("homepage.html.jinja")




@app.route("/search")
def search_page():
    return render_template("searchpage.html.jinja")


@app.route("/catolog")
def catolog_page():
    return render_template("catalog.html.jinja")

@app.route("/settings")
def setting_page():
    return render_template("settings.html.jinja")


