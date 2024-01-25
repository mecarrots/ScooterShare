from flask import (
    Flask,
    session,
    request,
    jsonify,
    redirect,
    url_for,
    render_template,
    send_from_directory
)

# from flask_login import LoginManager
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import MySQLdb
import json
import requests
from datetime import datetime
from flask_cors import CORS
import secrets

import configparser
config = configparser.ConfigParser()
config.read('config.ini')
ip_address = config.get('app', 'ip_address')
port = config.get('app', 'port')


from engineer import engineer_page
from customer import customer_page
from admin import admin_page

app = Flask(__name__, static_url_path='/static')

bcrypt = Bcrypt(app)
# Configure Flask-Session to use server-side sessions.
# secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = "JEFF"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SESSION_TYPE'] = 'sqlalchemy'
# app.config['SESSION_COOKIE_SECURE'] = True

db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db

sess = Session(app)
CORS(app)

# register blueprints
app.register_blueprint(engineer_page)
app.register_blueprint(customer_page)
app.register_blueprint(admin_page)

# with app.app_context():
#     db.create_all()


HOST = ""
USER = ""
PASSWORD = ""
DATABASE = ""

# initialise database in app config
app.config['MYSQL_HOST'] = HOST
app.config['MYSQL_USER'] = USER
app.config['MYSQL_PASSWORD'] = PASSWORD
app.config['MYSQL_DB'] = DATABASE

# # initialise session variables
# with app.app_context():
#     session['loggedin'] = None
#     session['user_id'] = None
#     session['username'] = None


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


def create_db_connection():
    return MySQLdb.connect(
        host=HOST, user=USER, passwd=PASSWORD, db=DATABASE
    )

@app.route('/register/<int:page_id>', methods=['POST'])
def register_user(page_id):
    try:
        # Extract data from the POST request
        data = request.form
        userType = data['userType']
        userName = data['userName']

        # TODO: SHOULD THIS BE HASHED BEFORE BEING POSTED?
        hashed_password = bcrypt.generate_password_hash(
            data["password"]).decode('utf-8')

        password = hashed_password
        firstName = data['firstName']
        lastName = data['lastName']
        phoneNumber = data['phoneNumber']
        email = data['email']
        availableMoney = 0

        # Create a database connection
        connection = create_db_connection()
        cursor = connection.cursor()

        # Insert data into the database
        insert_query = """INSERT INTO users (UserType, Username,
            Password, FirstName, LastName,
            PhoneNumber, Email, AvailableMoney)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            insert_query,
            (userType,
            userName,
            password,
            firstName,
            lastName,
            phoneNumber,
            email,
            availableMoney))
        connection.commit()

        # Close the database connection
        cursor.close()
        connection.close()

        # return jsonify({"message": "User inserted successfully"}), 201
        if page_id == 1:
            return render_template("register.html", message = "User registered successfully"), 201
        if page_id == 2:
            return render_template('admin/admin.html')
    except:
        if page_id == 1:
            return render_template("register.html", message = "User not inserted. User may already exist"), 500
        if page_id == 2:
            return render_template('admin/admin.html')
        


@app.route('/login', methods=['POST'])
def login_user():
    # Extract data from the POST request
    data = request.form
    password = data['password']
    email = data['email']

    # Create a database connection
    connection = create_db_connection()
    cursor = connection.cursor()

    # Select user from the database
    select_query = """SELECT Password, UserID, UserType, Username FROM users WHERE Email= %s"""
    cursor.execute(
        select_query,
        (email,))

    user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user[0], password):
        # Close the database connection
        cursor.close()
        connection.close()
        # session variables
        if user:
            # create session data
            session['loggedin'] = True
            session['user_id'] = user[1]
            session['username'] = user[3]
        # set user ID as a session variable
        userType = user[2]
        if userType == "Engineer":
            return render_template("engineer/engineer.html")
        elif userType == "System Admin":
            return render_template("admin/admin.html")
        elif userType == "Customer":
            return render_template("customer/customer.html")
        else:
            return jsonify({"message": "User logged in"}), 201

    else:
        # Close the database connection
        cursor.close()
        connection.close()
        return render_template("login.html", message = "Email Address or Password Incorrect")


@app.route('/logout')
def logout_user():
    try:    
        if session['user_id'] is None:
            return render_template('home.html', message="No user was logged in")
        
        else:
            session['loggedin'] = None
            session['user_id'] = None
            session['username'] = None
            return render_template('home.html', message="Successfully logged out!")
    except:
            return render_template('home.html', message="No current user session. It is likely that no user is logged in!"), 201


# Home page
@app.route('/')
def home_page():
    return render_template('home.html')


@app.route('/register_form', methods=['GET'])
def register_form():
    return render_template('register.html')


@app.route('/login_form', methods=['GET'])
def login_form():
    return render_template('login.html')


@app.route('/scooter_location/<int:scooter_id>', methods=['GET'])
def get_scooter_location(scooter_id):
    try:
        # Create a database connection
        connection = create_db_connection()
        cursor = connection.cursor()

        # Fetch the location of the scooter with the specified ID from the
        # database
        query = "SELECT Location FROM scooters WHERE ScooterID = %s"
        cursor.execute(query, (scooter_id,))
        location_data = cursor.fetchone()

        # Close the database connection
        cursor.close()
        connection.close()

        if location_data:
            location = location_data[0]
            return jsonify({"location": location})
        else:
            return jsonify(
                {"error": f"Scooter with ID {scooter_id} not found"})

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
