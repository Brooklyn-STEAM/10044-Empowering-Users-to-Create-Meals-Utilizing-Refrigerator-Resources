from flask import Flask, render_template, request,redirect,flash,abort,url_for, session 
import pymysql
from dynaconf import Dynaconf
import flask_login

from datetime import datetime  
from flask_login import logout_user

from werkzeug.security import generate_password_hash, check_password_hash 
from datetime import datetime  
from flask_login import logout_user



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

        user = conf.username, 



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
            return redirect("/") 


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
                VALUES ('{username}', '{phone}', '{password}', '{first_name}','{last_name}', '{email}', );
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
    
    conn = connect_db() 
    cursor = conn.cursor()     
     


    cursor.execute(f"SELECT * FROM `Recipe` WHERE `id` = {recipe_id};")
    recipe = cursor.fetchone()    
    # is the code to get the ingredients for the recipe
    cursor.execute("""
        SELECT `Ingredients`.`name`, `RecipeIngredients`.`amount`
        FROM `RecipeIngredients`
        JOIN `Ingredients` ON `Ingredients`.`id` = `RecipeIngredients`.`ingredient_id`
        WHERE `RecipeIngredients`.`recipe_id` = %s;
    """, (recipe_id,))
    ingredients = cursor.fetchall()

    cursor.execute(f""" SELECT * FROM 	`RecipeIngredients` JOIN `Recipe` ON`Recipe`.`id`= `RecipeIngredients`.`recipe_id`
                   JOIN `Ingredients` ON `Ingredients`.`id` = `RecipeIngredients`.`ingredient_id`
                   WHERE `recipe_id` = {recipe_id}
                  ;""")
    ingredients = cursor.fetchall()

   

    cursor.execute(f""" 
        SELECT * FROM Review WHERE `recipe_id` = {recipe_id};
    """)  


    

    

    reviews = cursor.fetchall()          
    

    cursor.execute(f"""
        SELECT r.rating, r.review, r.timestamp, c.username, c.picture
        FROM Review r 
        JOIN Customer c ON r.customer_id = c.id
        WHERE r.recipe_id = {recipe_id}  
        ORDER BY r.timestamp DESC;      
    """)   
    
                      

    review_stuff = cursor.fetchall()


    if request.method == "POST":      
       
        customer_id = flask_login.current_user.user_id
        cursor.execute(f"""SELECT * FROM Review WHERE recipe_id = '{recipe_id}' AND customer_id = '{customer_id}';""")
        existing_review = cursor.fetchone()            

        if existing_review:
            flash("You have already submitted a review for this product.", "error")
        else:
            rating = request.form["rating"]
            review = request.form["review"] 
            timestamp = datetime.now() 
            
            cursor.execute(f"""       
                INSERT INTO Review (recipe_id, customer_id, rating, review, timestamp)
                VALUES ('{recipe_id}', '{customer_id}', '{rating}', '{review}', '{timestamp}');
            """)         
            conn.commit()      
            
            flash("Your review has been submitted!", "success")
            return redirect(f"/recipe/{recipe_id}")
        
    cursor.execute(f"""
        SELECT rating 
         FROM `Review` 
        WHERE `recipe_id` = {recipe_id};
     """)
    ratings = cursor.fetchall()        

    if ratings:
        total_ratings = sum(rating['rating'] for rating in ratings)
        average_rating = total_ratings / len(ratings)
    else:
        average_rating = 0  # No ratings yet     


    cursor.close()
    conn.close() 

    print(recipe) 



    return render_template("individual_recipe.html.jinja", recipe = recipe, reviews = reviews, ingredients = ingredients, average_rating = average_rating, recipe_id = recipe_id, review_stuff = review_stuff) 

    
@app.route('/comment/<recipe_id>', methods=['POST', 'GET'])
@flask_login.login_required
def add_comment(recipe_id):
    


    return redirect(url_for('view_recipe', recipe_id=recipe_id))

      


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
        
        cursor.execute(f"""
        SELECT r.rating, r.review, r.timestamp, c.username
        FROM Review r 
        JOIN Customer c ON r.customer_id = c.id
        WHERE r.recipe_id = {recipe_id}  
        ORDER BY r.timestamp DESC;      
    """)    
        
    

        

        return redirect(f"/recipe/{recipe_id}") 
    

   
    
    

        
@app.route('/deletereview/<recipe_id>', methods=['POST', "GET"])
def delete_review(recipe_id):
    conn = connect_db()
    cursor = conn.cursor()
    customer_id = flask_login.current_user.user_id  
    cursor.execute("""
        DELETE FROM Review
        WHERE recipe_id = %s AND customer_id = %s
    """, (recipe_id, customer_id))

    conn.commit()
    conn.close()
    cursor.close() 

    return redirect(f'/recipe/{recipe_id}')

        
      


        

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


@app.route("/settings", methods = ["GET","POST"])
@flask_login.login_required
def setting_page():
    customer_id = flask_login.current_user.user_id
    conn =connect_db()
    cursor = conn.cursor()

    cursor.execute(f"SELECT `email`,`username`, `picture` FROM `Customer` WHERE `id` = '{customer_id}';")
    customer_details = cursor.fetchall()

    if request.method == "POST":
        new_photo = request.form['new_photo']
        cursor.execute(f"UPDATE `Customer` SET `picture` = ('{new_photo}') WHERE `id` = '{customer_id}';")
        return redirect ("/settings")
        


    cursor.close()
    conn.close

    return render_template("settings.html.jinja", customer_details = customer_details)




@app.route("/update_settings", methods=["POST", "GET"])
@flask_login.login_required
def update_pass():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.user_id

    new_username = request.form.get("new_username")
    new_password = request.form.get("new_password")

    
    if new_username and new_password:
        cursor.execute(
            "UPDATE Customer SET username = %s, password = %s WHERE id = %s",
            (new_username, new_password, customer_id)
        )
    elif new_username:
        cursor.execute(
            "UPDATE Customer SET username = %s WHERE id = %s",
            (new_username, customer_id)
        )
    elif new_password:
        cursor.execute(
            "UPDATE Customer SET password = %s WHERE id = %s",
            (new_password, customer_id)
        )

    conn.commit()
    flash("Account updated successfully!", "success")

    cursor.close() 
    conn.close()

    return redirect("/signin") 


# this is  duplicate code
@app.route("/settings/delete", methods=["POST", "GET"])
@flask_login.login_required
def delete_account():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.user_id

   
    cursor.execute("DELETE FROM Review WHERE customer_id = %s;", (customer_id,))
    cursor.execute("DELETE FROM SavedRecipe WHERE customer_id = %s;", (customer_id,))
    cursor.execute("DELETE FROM CustomerIngredients WHERE customer_id = %s;", (customer_id,))

   
    cursor.execute("DELETE FROM Customer WHERE id = %s;", (customer_id,))


    conn.commit()
    cursor.close()
    conn.close()

   
    logout_user()

    return redirect("/signup")



@app.route("/profile")
def profile_page(): 
    return render_template("profile.html.jinja") 





@app.route("/update_settings", methods=["POST", "GET"])
@flask_login.login_required
def update_settings():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.user_id

    new_username = request.form.get("new_username")
    new_password = request.form.get("new_password")

    
    if new_username and new_password:
        cursor.execute(
            "UPDATE Customer SET username = %s, password = %s WHERE id = %s",
            (new_username, new_password, customer_id)
        )
    elif new_username:
        cursor.execute(
            "UPDATE Customer SET username = %s WHERE id = %s",
            (new_username, customer_id)
        )
    elif new_password:
        cursor.execute(
            "UPDATE Customer SET password = %s WHERE id = %s",
            (new_password, customer_id)
        )

    conn.commit()
    flash("Account updated successfully!", "success")

    cursor.close() 
    conn.close()

    return redirect("/signin") 





@app.route("/settings/preferences", methods =["POST"])
@flask_login.login_required
def settings_preference(): 
    selected_preferences = request.form.get("theme") 
    return redirect("/", selected_preferences = selected_preferences)









@app.route("/addingredient")
def addingredient_page():
    return render_template("addingredient.html.jinja")


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
@app.route("/japanese")
def japanese_recipes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `Recipe` WHERE `cuisine` = 'Japanese';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("japanese_recipes.html.jinja", recipe = results)
@app.route("/indian")
def indian_recipes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `Recipe` WHERE `cuisine` = 'Indian';")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("indian_recipes.html.jinja", recipe = results)

@app.route("/individual_ingrediant")
def individual_ingrediant_page():
    return render_template("individual_ingredient.html.jinja")

@app.route("/swiper", methods=["POST", "GET"])
def swiper_page():
    conn=connect_db()
    cursor= conn.cursor()



    #flash a message when the  the recipe is succesfully  saved
   

    customer_id = flask_login.current_user.user_id
    cursor.execute(f"""
                SELECT * FROM `Recipe`
                JOIN `RecipeIngredients` ON `Recipe`.`id` = `RecipeIngredients`.`recipe_id`
                JOIN `Ingredients` ON `Ingredients`.`id` = `RecipeIngredients`.`ingredient_id`
                JOIN `CustomerIngredients` ON `CustomerIngredients`.`ingredient_id` = `RecipeIngredients`.`ingredient_id`
                WHERE `Ingredients`.`id` = `CustomerIngredients`.`ingredient_id`
                AND `CustomerIngredients`.`customer_id` = {customer_id};
        """)
    

    results = cursor.fetchall()
    """if not results:
        flash("No recipes found for the selected ingredients.")
        return redirect(url_for('catolog_page'))"""
    
    cursor.close()
    conn.close()

    return render_template("swiper.html.jinja", recipe=results, )
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
 

@app.route("/add_ingredient", methods=["POST", "GET"])
def add_ingredient():
    customer_id = flask_login.current_user.user_id
    conn = connect_db()
    cursor = conn.cursor()


    cursor.execute("SELECT * FROM `Ingredients`")
    ingredients = cursor.fetchall()

    cursor.execute(f"SELECT * FROM `CustomerIngredients` WHERE `customer_id` = '{customer_id}'")
    past_checked  = cursor.fetchall()

    if request.method == "POST":
        
        cursor.execute(f"DELETE FROM `CustomerIngredients` WHERE `customer_id` = '{customer_id}'")

        is_checked = request.form.getlist('ing_check')
        print(is_checked)

        for ing_id in is_checked:
            cursor.execute(f"INSERT INTO `CustomerIngredients` (`customer_id`, `ingredient_id`) VALUES ('{customer_id}','{ing_id}');")

            
        return redirect ("/swiper")
            

    cursor.close()
    conn.close

    return render_template("add_ingredient.html.jinja", ingredients = ingredients, past_checked = past_checked)
    




@app.route("/ingredient/delete_all", methods=['POST'])
@flask_login.login_required
def delete_all_ingredients():
    if request.method == "POST":
        customer_id = flask_login.current_user.user_id

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"""
            DELETE FROM `CustomerIngredients`
            WHERE `customer_id` = {customer_id}
        """)
        cursor.close()
        conn.close()

        flash("All ingredients deleted successfully!")

    return redirect(url_for('catolog_page'))


@app.route("/recipe/delete_all", methods=['POST'])
@flask_login.login_required
def delete_all_recipes():
    if request.method == "POST":
        customer_id = flask_login.current_user.user_id

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"""
            DELETE FROM `SavedRecipe`
            WHERE `customer_id` = {customer_id}
        """)
        cursor.close()
        conn.close()

        flash("All recipes removed successfully!")

    return redirect(url_for('savedrecipes_page'))

@app.route("/credits")
def credits_page():
    return render_template("credits.html.jinja")
