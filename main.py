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
        user = "ldore",  
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

@app.route("/recipe/<recipe_id>", methods=["GET", "POST"])
@flask_login.login_required
def recipe_detail(recipe_id):
    database_connection = connect_db() 
    database_cursor = database_connection.cursor()     

    # Fetch recipe details
    database_cursor.execute(f"SELECT * FROM `Recipe` WHERE `id` = {recipe_id};")
    recipe_details = database_cursor.fetchone()    

    # Fetch ingredients with amounts
    database_cursor.execute(f""" 
        SELECT `Ingredients`.`name`, `RecipeIngredients`.`amount`
        FROM `RecipeIngredients` 
        JOIN `Ingredients` ON `Ingredients`.`id` = `RecipeIngredients`.`ingredient_id`
        WHERE `RecipeIngredients`.`recipe_id` = %s;
    """, (recipe_id,))
    recipe_ingredients = database_cursor.fetchall()

    # Fetch all reviews for the recipe
    database_cursor.execute(f""" 
        SELECT * 
        FROM `Review` 
        WHERE `recipe_id` = {recipe_id};
    """)  
    recipe_reviews = database_cursor.fetchall()          
    
    # Fetch detailed reviews with customer information
    database_cursor.execute(f"""
        SELECT review_table.rating, review_table.review, review_table.timestamp, customer_table.username
        FROM `Review` review_table
        JOIN `Customer` customer_table ON review_table.customer_id = customer_table.id
        WHERE review_table.recipe_id = {recipe_id}  
        ORDER BY review_table.timestamp DESC;      
    """)

    # Handle POST request for submitting a review
    if request.method == "POST":      
        customer_id = flask_login.current_user.user_id
        database_cursor.execute(f"""
            SELECT * 
            FROM `Review` 
            WHERE `recipe_id` = '{recipe_id}' AND `customer_id` = '{customer_id}';
        """)
        existing_review = database_cursor.fetchone()

        if existing_review:
            flash("You have already submitted a review for this recipe.", "error")

    database_cursor.execute("""
        SELECT rating 
        FROM `Review` 
        WHERE `recipe_id` = %s;
    """, (recipe_id,))
    ratings = database_cursor.fetchall()        

    if ratings:
        total_ratings = sum(rating['rating'] for rating in ratings)
        average_rating = total_ratings / len(ratings)
    else:
        average_rating = 0  # No ratings yet     

    database_cursor.close()
    database_connection.close()

    return render_template(
        "individual_recipe.html.jinja", 
        recipe=recipe_details, 
        ingredients=recipe_ingredients, 
        reviews=recipe_reviews,
        average_rating=average_rating
    )

@app.route("/addreview/<recipe_id>", methods =["GET", "POST"])
def addreview(recipe_id): 
    conn = connect_db() 
    cursor = conn.cursor()
    if request.method == "POST":
        rating = request.form["rating"]
        review = request.form["review"] 
        timestamp = datetime.now() 
        customer_id = flask_login.current_user.user_id 
        cursor.execute(f""" 
                    INSERT INTO `Review` (`recipe_id`, `customer_id`, `rating`, `review`, `timestamp`)
                    VALUES 
                        ('{recipe_id}', '{customer_id}', '{rating}', '{review}','{timestamp}')    
                        ON DUPLICATE KEY UPDATE `review`= '{review}', rating = '{rating}';   
                """,) 
        conn.close()      
        cursor.close()      

    return redirect(f"/recipe/{recipe_id}")             

@app.route("/")
def index():
    conn = connect_db()
    cursor = conn.cursor()

    # Check if the user is logged in
    if flask_login.current_user.is_authenticated:
        customer_id = flask_login.current_user.user_id
        cursor.execute("""
            SELECT * 
            FROM `CustomerIngredients`
            JOIN `Ingredients` ON `CustomerIngredients`.`ingredient_id` = `Ingredients`.`id`
            WHERE `CustomerIngredients`.`customer_id` = %s;
        """, (customer_id,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("homepage.html.jinja", ingredients=results)
    
    if flask_login.current_user.is_authenticated == False:
        return render_template("homepage.html.jinja")
    cursor.close()
    conn.close()
    return render_template("homepage.html.jinja")
@app.route




@app.route("/search", methods=["GET"])
def search_page():
    query = request.args.get('query', '')  # Get the search query (default to an empty string)
    cuisine = request.args.get('cuisine', '')  # Get the selected cuisine (default to an empty string)

    conn = connect_db()
    cursor = conn.cursor()

    # Base SQL query
    sql_query = "SELECT * FROM `Recipe` WHERE 1=1"
    params = []

    # Add search query filter
    if query:
        sql_query += " AND (`name` LIKE %s OR `description` LIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])

    # Add cuisine filter
    if cuisine:
        sql_query += " AND `cuisine` = %s"
        params.append(cuisine)

    # Execute the query with parameters
    cursor.execute(sql_query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("searchpage.html.jinja", recipe=results, query=query, cuisine=cuisine)
    



























@app.route("/catalog")
def catolog_page():
    
    if flask_login.current_user.is_authenticated == False:
        flash("Please log in to view your ingredients.")
        return redirect("/signin")
        
    
    conn = connect_db()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.user_id
    cursor.execute(f"""
        SELECT *
        FROM `CustomerIngredients` 
        JOIN `Ingredients`  ON `Ingredients`.`id` = `CustomerIngredients`.`ingredient_id`
        WHERE `CustomerIngredients`.`customer_id` = {customer_id};
    """)
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    if flask_login.current_user.is_authenticated == False:
        return redirect("/signin")
    
    return render_template("catalog.html.jinja", ingredients = results)

@app.route("/settings")
def setting_page():
    return render_template("settings.html.jinja")


@app.route("/add_ingredient", methods = ["GET","POST"])
@flask_login.login_required
def add_ingredient_page():
    customer_id = flask_login.current_user.user_id
    conn = connect_db()
    cursor = conn.cursor()


    cursor.execute("SELECT * FROM `Ingredients`")
    ing_results = cursor.fetchall()



    if request.method == "POST":
        is_checked = request.form.getlist('ing_check')


        for ing_id in is_checked:
            cursor.execute(f"INSERT INTO `CustomerIngredients` (`customer_id`, `ingredient_id`) VALUES ('{customer_id}','{ing_id}');")
        return redirect ("/swiper")

    cursor.close()
    conn.close

    return render_template("add_ingredient.html.jinja", ing_results = ing_results)



   


@app.route("/mexican")
def mexican_recipes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `Recipe` WHERE `cuisine` = 'Mexican';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()    
    return render_template("mexican_recipes.html.jinja" , recipe = results)
@app.route("/british")
def korean_recipes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `Recipe` WHERE `cuisine` = 'British';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()    
    return render_template("korean_recipes.html.jinja" , recipe = results)

@app.route("/italian")  
def italian_recipes():
    conn = connect_db()         
    cursor = conn.cursor()  
    cursor.execute("SELECT * FROM `Recipe` WHERE `cuisine` = 'Italian';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("italian_recipes.html.jinja", recipe = results)  

@app.route("/individual_ingrediant")
def individual_ingrediant_page():
    return render_template("individual_ingredient.html.jinja")

@app.route("/swiper")
def swiper_page():
    conn = connect_db()
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM `Recipe`")

    # cursor.execute("""
    #                SELECT * 
    #                FROM `CustomerIngredients` 
    #                JOIN `RecipeIngredients` ON `recipe_id`               
    #              """)


    # cursor.execute("""
    #                
    # """)
    # 
    

    # for x in results 
        # if results_category = American, British, Canidian, Chinese, Dutch, Egyptian, Filipino, French

    #flash a message when the  the recipe is succesfully  saved
   
    results = cursor.fetchall()
    cursor.close()
    conn.close


    return render_template("swiper.html.jinja", recipe = results)

@app.route("/savedrecipes" ,methods=["POST", "GET"])
@flask_login.login_required
def savedrecipes_page():
    conn=connect_db()
    cursor= conn.cursor()

    customer_id = flask_login.current_user.user_id
    cursor.execute(f"""
                SELECT 
                    `image`,
                    `recipe_id`,
                    `name`,
                    `description`,
                   
                `SavedRecipe`.`id`
                FROM `SavedRecipe` 
                JOIN `Recipe` ON `recipe_id` = `Recipe`.`id` 
                WHERE `customer_id` =  {customer_id};""")
    

    results = cursor.fetchall()

    return render_template("savedrecipes.html.jinja" , recipe = results)


@app.route("/recipe/<recipe_id>/save", methods=['POST'])
@flask_login.login_required
def add_to_saved(recipe_id):
    customer_id = flask_login.current_user.user_id
    conn = connect_db()
    cursor = conn.cursor()

    # Check if the recipe is already saved
    cursor.execute("""
        SELECT * FROM `SavedRecipe`
        WHERE `customer_id` = %s AND `recipe_id` = %s
    """, (customer_id, recipe_id))
    existing_recipe = cursor.fetchone()

    if existing_recipe:
        message = "Recipe is already saved!"
        status = "warning"
    else:
        # Save the recipe
        cursor.execute("""
            INSERT INTO `SavedRecipe` (`customer_id`, `recipe_id`)
            VALUES (%s, %s)
        """, (customer_id, recipe_id))
        conn.commit()
        message = "Recipe saved successfully!"
        status = "success"

    cursor.close()
    conn.close()

    flash('Recipe saved successfully!')

    return redirect(url_for('swiper_page'))



@app.route("/individual/recipe/<recipe_id>/save", methods=['POST'])
@flask_login.login_required
def save_recipe(recipe_id):
    customer_id = flask_login.current_user.user_id
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        
        customer_id = flask_login.current_user.user_id

    # Check if the recipe is already saved
    cursor.execute(f"""
        SELECT * FROM `SavedRecipe`
        WHERE `customer_id` = {customer_id} AND `recipe_id` = {recipe_id}
    """)
    existing_recipe = cursor.fetchone()

    if existing_recipe:
        cursor.execute(f"""
        DELETE FROM `SavedRecipe`       
        WHERE `customer_id` = {customer_id} AND `recipe_id` = {recipe_id}
        """)
        conn.commit()
        flash("Recipe removed from saved recipes.")
    else:
        # Save the recipe
        cursor.execute(f"""
            INSERT INTO `SavedRecipe` (`customer_id`, `recipe_id`)
            VALUES ({customer_id}, {recipe_id})
        """)
        conn.commit()
        flash("Recipe saved successfully!")

    return redirect(url_for('recipe_detail', recipe_id=recipe_id))



@app.route("/recipe/<recipe_id>/delete" ,methods =['POST'])
@flask_login.login_required
def delete_saved(recipe_id):
    if request.method == "POST":
        customer_id = flask_login.current_user.user_id    

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"""
                        DELETE FROM `SavedRecipe`
                        WHERE `customer_id` = {customer_id} AND `recipe_id` = {recipe_id}
                  ;""" )  
        cursor.close()
        conn.close()
        flash("Recipe deleted successfully!")
        if request.method == "POST":
            return redirect(url_for('savedrecipes_page'))
        else:
            # Redirect to the recipe detail page
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))
        

@app.route("/ingredient/<ingredient_id>/delete", methods=['POST'])
@flask_login.login_required
def delete_ingredient(ingredient_id):
    if request.method == "POST":
        customer_id = flask_login.current_user.user_id

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"""
            DELETE FROM `CustomerIngredients`
            WHERE `customer_id` = {customer_id} AND `ingredient_id` = {ingredient_id}
        """)
        cursor.close()
        conn.close()

        flash("Ingredient deleted successfully!")

    return redirect(url_for('catolog_page'))



@app.route("/profile")
@flask_login.login_required
def profile():
    return render_template("profile.html.jinja")