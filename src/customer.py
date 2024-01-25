from flask import (
    Flask,
    session,
    request,
    jsonify,
    redirect,
    url_for,
    render_template,
    Blueprint,
    current_app
)

import flask
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

# Session(app)

HOST = ""
USER = ""
PASSWORD = ""
DATABASE = ""

def create_db_connection():
    return MySQLdb.connect(
        host=HOST, user=USER, passwd=PASSWORD, db=DATABASE
    )


customer_page = Blueprint('customer_page', __name__,
                          template_folder='templates')


@customer_page.route('/customer_page_render')
def customer_page_render():
    return render_template('customer/customer.html')


@customer_page.route('/add_scooter_usage', methods=['POST'])
def add_scooter_usage():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        scooter_id = data.get('ScooterID')
        user_id = data.get('UserID')
        time_used = data.get('TimeUsed')
        distance_covered = data.get('DistanceCovered')

        if scooter_id is None or user_id is None or time_used is None or distance_covered is None:
            return jsonify({"error": "Incomplete data"}), 400

        connection = create_db_connection()
        cursor = connection.cursor()

        try:
            # Insert scooter usage data into the database
            insert_query = """INSERT INTO scooter_usage (ScooterID, UserID, 
            TimeUsed, DistanceCovered) VALUES (%s, %s, %s, %s)"""
            cursor.execute(insert_query, (scooter_id, user_id,
                           time_used, distance_covered))
            connection.commit()

            return jsonify({"message": "Scooter usage data added successfully"}), 201
        except Exception as e:
            connection.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@customer_page.route('/book_scooter/<int:scooter_id>/<int:user_id>', methods=['POST'])
def book_scooter(scooter_id, user_id):
    # Set the booking status to 'Active' if a booking is made
    booking_status = 'Active'
    
    connection = create_db_connection()
    cursor = connection.cursor()

    try:
        connection.begin()

        # Update the attempting to be booked scooter's status to 'Occupying'
        update_scooter_status_query = """UPDATE scooters SET Status = 'Occupying' WHERE ScooterID = %s"""
        cursor.execute(update_scooter_status_query, (scooter_id,))

        # Insert booking data into the bookings table
        insert_query = """INSERT INTO bookings (ScooterID, UserID, BookingTime, BookingStatus, LockStatus)
        VALUES (%s, %s, NOW(), %s, 'Locked')"""
        cursor.execute(
            insert_query,
            (scooter_id,
             user_id,
             booking_status))

        connection.commit()

        points_to_increment = 100

        select_query = "SELECT points FROM ranking WHERE UserID = %s"
        cursor.execute(select_query, (user_id,))
        current_points = cursor.fetchone()

        if current_points is not None:
            print("Current Points:", current_points)
            current_points = current_points[0]

            # Increment the points
            new_points = current_points + points_to_increment
            print("New Points:", new_points)

            # Update the user's points in the database
            update_query = "UPDATE ranking SET points = %s WHERE UserID = %s"
            cursor.execute(update_query, (new_points, user_id))
            connection.commit()
        else:
            print(points_to_increment)
            # Insert points data into the database
            insert_query = """INSERT INTO ranking (UserID, points)
            VALUES (%s, %s)"""
            cursor.execute(
                insert_query,
                (user_id,
                 points_to_increment))
            connection.commit()

        return jsonify({"message": "Booking successful"}), 201

    except Exception as e:
        # Rollback the transaction in case of an error
        connection.rollback()
        return jsonify({"message": "Booking failed. Error: " + str(e)}), 500

    finally:
        cursor.close()
        connection.close()


@customer_page.route("/book_scooter_page/<int:scooter_id>", methods=['GET', 'POST'])
def book_scooter_page(scooter_id):
    response = requests.post(
        "http://" + ip_address + ":" + port + "/book_scooter/" + str(scooter_id) + "/" + str(session['user_id']))
    data = json.loads(response.text)

    return render_template("customer/customer_booking.html", message=data)

@customer_page.route('/customer_bookings/<int:user_id>', methods=['GET'])
def get_booking_history(user_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the customer's active bookings
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus, LockStatus FROM bookings WHERE UserID = %s"
        cursor.execute(query, (user_id,))
        booking_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the data to a list of dictionaries
        booking_history = []
        for booking in booking_data:
            booking_history.append({
                "BookingID": booking[0],
                "ScooterID": booking[1],
                "BookingTime": booking[2].strftime("%Y-%m-%d %H:%M:%S"),
                "BookingStatus": booking[3],
                "LockStatus": booking[4]
            })

        return jsonify({"user_id": user_id,
                        "booking_history": booking_history})

    except Exception as e:
        return jsonify({"error": str(e)})
    

@customer_page.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    connection = create_db_connection()
    cursor = connection.cursor()

    # Get the scooter ID associated with the booking
    scooter_query = "SELECT ScooterID FROM bookings WHERE BookingID = %s"
    cursor.execute(scooter_query, (booking_id,))
    scooter_id = cursor.fetchone()[0]

    # Update the booking status in the database
    update_booking_query = "UPDATE bookings SET BookingStatus = 'Cancelled' WHERE BookingID = %s"
    cursor.execute(update_booking_query, (booking_id,))

    # Update the scooter status to 'Available'
    update_scooter_query = "UPDATE scooters SET Status = 'Available' WHERE ScooterID = %s"
    cursor.execute(update_scooter_query, (scooter_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Booking cancelled successfully"}), 200

@customer_page.route("/customer_cancel_booking/<int:booking_id>", methods=['GET'])
def scooter_cancel_booking_page(booking_id):
    response = requests.post(
        "http://" + ip_address + ":" + port + "/cancel_booking/" + str(booking_id))
    data = json.loads(response.text)

    return render_template("customer/customer_cancel_booking.html", message=data)

@customer_page.route("/customer_view_bookings", methods=['GET'])
def scooter_booking_page():
    response = requests.get(
        "http://" + ip_address + ":" + port + "/customer_bookings/" + str(session['user_id']))
    data = json.loads(response.text)

    return render_template("customer/customer_view_bookings.html", booking_history=data)


@customer_page.route('/available_scooters', methods=['GET'])
def get_all_scooters():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all available scooters
        query = "SELECT * FROM scooters WHERE status = 'Available'"
        cursor.execute(query)
        scooter_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the data into a list of dictionaries
        scooters = []
        for scooter in scooter_data:
            scooter_dict = {
                "ScooterID": scooter[0],
                "Make": scooter[1],
                "Colour": scooter[2],
                "Location": scooter[3],
                "RemainingPower": scooter[4],
                "CostPerTime": scooter[5],
                "Status": scooter[6]
            }
            scooters.append(scooter_dict)

        return jsonify({"scooters": scooters})
    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route("/view_available_scooters", methods=['GET'])
def view_all_scooters_page():
    response = requests.get("http://" + ip_address + ":" + port + "/available_scooters")
    data = json.loads(response.text)

    return render_template("customer/available_scooters.html", scooters=data)

@customer_page.route('/customer_usage_history/<int:user_id>', methods=['GET'])
def get_customer_usage_history(user_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all usage history for the specified scooter ID, including UsageDate
        query = "SELECT UsageID, ScooterID, TimeUsed, DistanceCovered FROM scooter_usage WHERE UserID = %s"
        cursor.execute(query, (user_id,))
        usage_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the data into a list of dictionaries and format UsageDate
        scooter_usage_history = []
        for entry in usage_data:
            entry_dict = {
                "UsageID": entry[0],
                "ScooterID": entry[1],
                "TimeUsed": entry[2],
                "DistanceCovered": entry[3],
                "UsageDate": entry[4].strftime('%d-%m-%Y')
            }
            scooter_usage_history.append(entry_dict)

        return jsonify({"user_id": user_id, "scooter_usage_history": scooter_usage_history})

    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route("/customer_usage_history_render", methods=['GET'])
def customer_usage_history():
    userID = session.get('user_id')
    response = requests.get(
        "http://" + ip_address + ":" + port + "/customer_usage_history/" + str(userID))
    data = json.loads(response.text)

    return render_template("customer/usage_history.html", usage_history=data)

@customer_page.route('/customer_balance_data/<int:userID>', methods=['GET'])
def customer_balance_data(userID):
    # user_id = session.get('user_id')
    # userID = session.get('user_id')
    print("User ID is " + str(userID))
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all usage history for the specified scooter ID
        query = "SELECT AvailableMoney FROM users WHERE UserID = %s"
        cursor.execute(query, (userID,))
        customer_data = cursor.fetchone()

        cursor.close()
        connection.close()

        return jsonify({"balance": customer_data[0]})

    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route('/update_user_money', methods=['POST'])
def update_user_money():
    # user_id = session.get('user_id')
    # topup_amount = data['topup_amount']
    try:
        userID = session.get('user_id')
        topup_amount = float(request.form.get('topup_amount'))

        connection = create_db_connection()
        cursor = connection.cursor()

        # get current available money from the database
        select_query = """SELECT AvailableMoney FROM users WHERE UserID = %s"""
        cursor.execute(
            select_query,
            (userID,))

        user = cursor.fetchone()
        currentMoney = float(user[0])
        newBalance = currentMoney + topup_amount

        # Get all usage history for the specified scooter ID
        update_query = "UPDATE users SET AvailableMoney = %s WHERE UserID = %s"
        cursor.execute(update_query, (newBalance, userID,))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('customer_page.customer_view_balance'))

    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route('/add_review', methods=['POST'])
def add_review():
    # Get the review data from the form
    user_id = request.form.get('user_id')
    scooter_id = request.form.get('scooter_id')
    review = request.form.get('review')
    rating = request.form.get('rating')

    connection = create_db_connection()
    cursor = connection.cursor()

    # Insert review data into the database
    insert_query = """INSERT INTO reviews (UserID, ScooterID, Review, Rating)
    VALUES (%s, %s, %s, %s)"""
    cursor.execute(
        insert_query,
        (user_id,
         scooter_id,
         review,
         rating))
    connection.commit()

    cursor.close()
    connection.close()

    return render_template('customer/customer.html', message = "Review added successfully")

@customer_page.route('/get_review', methods=['GET'])
def get_review():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Select user from the database
        query = """SELECT * FROM reviews"""
        cursor.execute(query)
        review_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # convert the fetched data to a dictionary
        review = []
        for row in review_data:
            review.append({
                "review_id": row[0],
                "user_id": row[1],
                "scooter_id": row[2],
                "review": row[3],
                "rating": row[4]
            })

        return jsonify({"review": review})

    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route('/get_ranking', methods=['GET'])
def get_ranking():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Select user from the database
        query = """SELECT * FROM ranking"""
        cursor.execute(query)
        ranking_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # convert the fetched data to a dictionary
        ranking = []
        for row in ranking_data:
            ranking.append({
                "ranking": row[0],
                "user_id": row[1],
                "points": row[2],
            })

        return jsonify({"ranking": ranking})

    except Exception as e:
        return jsonify({"error": str(e)})


@customer_page.route('/get_customer', methods=['GET'])
def get_customer():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Select user from the database
        query = """SELECT * FROM users WHERE UserType = 'Customer'"""
        cursor.execute(query)
        customer_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # convert the fetched data to a dictionary
        customer = []
        for row in customer_data:
            customer.append({
                "user_id": row[0],
                "usertype": row[1],
                "username": row[2],
                "password": row[3],
                "firstname": row[4],
                "lastname": row[5],
                "phonenumber": row[6],
                "email": row[7],
                "available_money": row[8]
            })
        return jsonify({"customer": customer})
    except Exception as e:
        return jsonify({"error": str(e)})


@customer_page.route("/customer_view_balance", methods=['GET'])
def customer_view_balance():
    if session['loggedin'] is True:
        response = requests.get(
            "http://" + ip_address + ":" + port + "/customer_balance_data/" + str(session['user_id']))
        data = json.loads(response.text)

        return render_template("customer/customer_balance.html", balance=data)
    else:
        return redirect("/login_form")


@customer_page.route("/customer_report_scooter/<int:scooter_id>", methods=['GET'])
def customer_scooter_report_page(scooter_id):
    user_id = session.get('user_id')
    response = requests.get(
        "http://" + ip_address + ":" + port + "/scooter_by_id/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("customer/customer_report.html", scooter=data, user_id_=user_id)

@customer_page.route("/add_reviews/<int:scooter_id>", methods=['GET'])
def add_review_page(scooter_id):
    user_id = session.get('user_id')
    if user_id is None:
        return render_template("/login.html")

    response = requests.get(
        "http://" + ip_address + ":" + port + "/scooter_by_id/" + str(scooter_id))
    scooter = json.loads(response.text)

    response = requests.get("http://" + ip_address + ":" + port + "/get_customer")
    customer = json.loads(response.text)

    return render_template("customer/customer_add_review.html", user_id=user_id, scooter_id=scooter, customers=customer)

@customer_page.route("/customer_review", methods=['GET'])
def customer_review_page():
    response = requests.get("http://" + ip_address + ":" + port + "/get_review")
    data = json.loads(response.text)

    response = requests.get("http://" + ip_address + ":" + port + "/get_customer")
    customer = json.loads(response.text)

    response = requests.get("http://" + ip_address + ":" + port + "/available_scooters")
    scooter = json.loads(response.text)

    return render_template("customer/customer_review.html", review_id=data, customers=customer, scooters=scooter)


@customer_page.route("/customer_ranking", methods=['GET'])
def customer_ranking_page():
    response = requests.get("http://" + ip_address + ":" + port + "/get_ranking")
    ranking = json.loads(response.text)

    response = requests.get("http://" + ip_address + ":" + port + "/get_customer")
    customer = json.loads(response.text)

    return render_template("customer/customer_ranking.html", ranking=ranking, customers=customer)


@customer_page.route('/test_session')
def test_session():
    user_id = session.get('user_id')
    return f'Test User ID: {user_id}'


@customer_page.route('/customer_lock_unlock')
def customer_lock_unlock():
    user_id = session.get('user_id')
    response1 = requests.get("http://" + ip_address + ":" + port + "/customer_active_bookings_unlocked/" + str(user_id))
    lockable = json.loads(response1.text)

    response2 = requests.get("http://" + ip_address + ":" + port + "/customer_active_bookings_locked/" + str(user_id))
    unlockable = json.loads(response2.text)

    return render_template("customer/lock_unlock.html", lockable=lockable, unlockable=unlockable)

# TODO: Complete
@customer_page.route("/customer_unlock_scooter/<int:scooter_id>/<int:booking_id>")
def customer_unlock_scooter(scooter_id, booking_id):
    # Check available money on account (needs to be enough to book the scooter)
    # Set LockStatus in booking entry to "Unlocked"
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the scooter ID associated with the booking
        scooter_query = "SELECT AvailableMoney FROM users WHERE UserID = %s"
        cursor.execute(scooter_query, (session.get('user_id'),))
        available_money = cursor.fetchone()[0]

        scooter_query = "SELECT CostPerTime FROM scooters WHERE ScooterID = %s"
        cursor.execute(scooter_query, (scooter_id,))
        cost_per_time = cursor.fetchone()[0]

        if available_money < cost_per_time:
            return render_template("customer/customer.html", message="Not enough funds to unlock scooter. Please topup account :)"), 200

        # Update the booking status in the database
        update_booking_query = "UPDATE bookings SET LockStatus = 'Unlocked' WHERE BookingID = %s"
        cursor.execute(update_booking_query, (booking_id,))

        connection.commit()

        cursor.close()
        connection.close()

        return render_template("customer/customer.html", message = "Scooter Unlocked Successfully"), 200
    except Exception as e:
        return jsonify({"error": str(e)})

@customer_page.route("/customer_lock_scooter/<int:scooter_id>/<int:booking_id>", methods=['GET'])
def customer_lock_scooter(scooter_id, booking_id):
    # Charge from available money on account
    # Set LockStatus in booking entry to "Locked"
    # Set BookingStatus in booking entry to "Completed"
    # Set ScooterStatus in scooter entry to "Available"
    # Set new location
    # TODO: USAGE ENTRY
    try:
        userID = session.get('user_id')
        new_location = request.args.get('newLocation')
        print(new_location)

        connection = create_db_connection()
        cursor = connection.cursor()

        # get cost per time
        scooter_query = "SELECT CostPerTime FROM scooters WHERE ScooterID = %s"
        cursor.execute(scooter_query, (scooter_id,))
        cost_per_time = cursor.fetchone()[0]

        # get current available money from the database
        select_query = """SELECT AvailableMoney FROM users WHERE UserID = %s"""
        cursor.execute(
            select_query,
            (userID,))

        user = cursor.fetchone()
        currentMoney = float(user[0])
        newBalance = currentMoney - cost_per_time

        # update balance to current_money - cost_per_time
        update_query = "UPDATE users SET AvailableMoney = %s WHERE UserID = %s"
        cursor.execute(update_query, (newBalance, userID,))

        connection.commit()

        # Update the lock status in the database
        update_booking_query = "UPDATE bookings SET LockStatus = 'Locked' WHERE BookingID = %s"
        cursor.execute(update_booking_query, (booking_id,))

        # Update the booking status in the database
        update_booking_query = "UPDATE bookings SET BookingStatus = 'Completed' WHERE BookingID = %s"
        cursor.execute(update_booking_query, (booking_id,))

        update_booking_query = "UPDATE scooters SET Status = 'Available' WHERE ScooterID = %s"
        cursor.execute(update_booking_query, (scooter_id,))

        update_booking_query = "UPDATE scooters SET Location = %s WHERE ScooterID = %s"
        cursor.execute(update_booking_query, (new_location, scooter_id,))
        # commit updates to bookings and scooters
        connection.commit()

        insert_usage_query = "INSERT INTO scooter_usage (ScooterID, UserID, TimeUsed,\
              UsageDate, DistanceCovered) VALUES (%s,%s,%s,DATE(NOW()),%s)"
        cursor.execute(insert_usage_query, (scooter_id, userID, 10, 10))
        # commit updates to usage table
        connection.commit()

        cursor.close()
        connection.close()

        return render_template("customer/customer.html", message = "Scooter Locked Successfully"), 200
    except Exception as e:
        return jsonify({"error": str(e)})
    

# return list of locked scooters that are actively booked by a user
@customer_page.route('/customer_active_bookings_unlocked/<int:user_id>', methods=['GET'])
def get_active_booking_history_unlocked(user_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the customer's active bookings
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus FROM bookings WHERE UserID = %s AND BookingStatus = 'Active' AND LockStatus = 'Unlocked'"
        cursor.execute(query, (user_id,))
        booking_data = cursor.fetchall()
        # print("Booking data:" + booking_data)

        cursor.close()
        connection.close()

        # Convert the data to a list of dictionaries
        booking_history = []
        for booking in booking_data:
            booking_history.append({
                "BookingID": booking[0],
                "ScooterID": booking[1],
                "BookingTime": booking[2].strftime("%Y-%m-%d %H:%M:%S"),
                "BookingStatus": booking[3]
            })

        return jsonify({"booking_history": booking_history})

    except Exception as e:
        return jsonify({"error": str(e)})
    

@customer_page.route('/customer_active_bookings_locked/<int:user_id>', methods=['GET'])
def get_active_booking_history_locked(user_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the customer's active bookings
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus FROM bookings WHERE UserID = %s AND BookingStatus = 'Active' AND LockStatus = 'Locked'"
        cursor.execute(query, (user_id,))
        booking_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the data to a list of dictionaries
        booking_history = []
        for booking in booking_data:
            booking_history.append({
                "BookingID": booking[0],
                "ScooterID": booking[1],
                "BookingTime": booking[2].strftime("%Y-%m-%d %H:%M:%S"),
                "BookingStatus": booking[3]
            })

        return jsonify({"booking_history": booking_history})

    except Exception as e:
        return jsonify({"error": str(e)})
