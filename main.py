from flask import Flask, render_template, request,redirect,flash,abort,url_for
import pymysql
from dynaconf import Dynaconf
import flask_login
from werkzeug.security import generate_password_hash
from datetime import datetime  



app = Flask(__name__)

conf = Dynaconf(
    settings_file = ['settings.toml']
)




app.secret_key = conf.secret_key 
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view =('/signin')


class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True
    
    def __init__(self, user_id, username,email,first_name,last_name, phone):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone 

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
        return User(result['id'], result['username'], result['email'],result['first_name'],result['last_name'], result['phone']) 

def connect_db ():
    conn = pymysql.connect(            
        host= "db.steamcenter.tech",
        database= "pantryfy",
        user = "rbarry", 
        password = conf.password, 
        autocommit= True,   
        cursorclass= pymysql.cursors.DictCursor, 
        )       

    return conn       


@app.route("/signin", methods=["POST", "GET"])
def signin():
    if flask_login.current_user.is_authenticated:
        return redirect("/") 

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = connect_db() 
        cursor = conn.cursor() 
        cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}';")
        result = cursor.fetchone()          
     
        if result is None:
            flash("Your username/password is incorrect")
        elif password != result["password"]:                 
            flash("Your username/password is incorrect")   
        else:
            user = User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"], result["phone"])  
            flask_login.login_user(user) 

        
        
        conn.close() 
        cursor.close()
           
        
    return render_template("signin.html.jinja")
           

@app.route('/logout') 
def logout():
    flask_login.logout_user()  
    return redirect('/')      


@app.route("/signup", methods=["POST", "GET"])
def signup(): 
    if flask_login.current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST": 
        first_name = request.form["first_name"]
        last_name = request.form["last_name"] 
        email = request.form["email"]
        password = request.form["password"]
        username = request.form["username"]
        phone = request.form["phone"]   
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Password does not match the confirmation.")
            return render_template("signup.html.jinja")

        conn = connect_db() 
        cursor = conn.cursor() 

        try:
            cursor.execute(f"""
                INSERT INTO `Customer` (`username`, `phone`, `password`, `first_name`, `last_name`, `email`)
                VALUES ('{username}', '{phone}', '{password}', '{first_name}','{last_name}', '{email}');
            """) 
            conn.commit()
        except pymysql.err.IntegrityError:
            flash("Sorry, that username/email is already in use.")
            return render_template("signup.html.jinja")
        finally:
            cursor.close()
            conn.close()

        return redirect("/signin")

    return render_template("signup.html.jinja") 


@app.route("/recipe/<recipe_id>/", methods=["GET", "POST"])
@flask_login.login_required
def product_detail(recipe_id):
    conn = connect_db() 
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT * FROM `Review` WHERE `id` = {recipe_id};
    """) 
    product = cursor.fetchone() 

    cursor.execute(f"""
        SELECT r.rating, r.review, r.timestamp, c.username
        FROM `Review` r 
        JOIN `Customer` c ON r.customer_id = c.id
        WHERE r.recipe_id = {recipe_id}  
        ORDER BY r.timestamp DESC;    
    """)                         

    product = cursor.fetchall()     

    if request.method == "POST":      
       
        customer_id = flask_login.current_user.id
        cursor.execute(f"SELECT * FROM `Review` WHERE `recipe_id` = '{recipe_id}' AND `customer_id` = '{customer_id}';")
        existing_review = cursor.fetchone()           

        if existing_review:
            flash("You have already submitted a review for this product.", "error")
        else:
            rating = request.form["rating"]
            review = request.form["review"] 
            timestamp = datetime.now() 
            
            cursor.execute(f"""       
                INSERT INTO `Review` (`recipe_id`, `customer_id`, `rating`, `review`, `timestamp`)
                VALUES ('{recipe_id}', '{customer_id}', '{rating}', '{review}', '{timestamp}');
            """)         
            conn.commit()      
            
            flash("Your review has been submitted!", "success")
            return redirect(f"/product/{recipe_id}") 

    cursor.close()
    conn.close()

    return render_template(".html.jinja", product = product,) 


@app.route("/addreview/<recipe_id>/", methods =["GET", "POST"])
def addreview(recipe_id): 
    conn = connect_db()
    cursor = conn.cursor() 
    rating = request.form["rating"]
    review = request.form["review"] 
    timestamp = datetime.now() 
    customer_id = flask_login.current_user.id 
    cursor.execute(f"""
                INSERT INTO `Review` (`recipe_id`, `customer_id`, `rating`, `review`, `timestamp`)
                VALUES
                    ('{recipe_id}', '{customer_id}', '{rating}', '{review}','{timestamp}')    
                    ON DUPLICATE KEY UPDATE `review`= '{review}', rating = '{rating}';   
            """,) 
    conn.close()      
    cursor.close() 

    return render_template("homepage.html.jinja")    



    


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


@app.route("/addingredient")
def addingredient_page():
    return render_template("addingredient.html.jinja")

@app.route("/mexican")
def mexican_recipes():
    return render_template("mexican_recipes.html.jinja")

@app.route("/individual_ingrediant")
def individual_ingrediant_page():
    return render_template("individual_ingredient.html.jinja")