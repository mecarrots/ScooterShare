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


app = Flask(__name__)

HOST = ""
USER = ""
PASSWORD = ""
DATABASE = ""

def create_db_connection():
    return MySQLdb.connect(
        host=HOST, user=USER, passwd=PASSWORD, db=DATABASE
    )

engineer_page = Blueprint('engineer_page', __name__, template_folder='templates')

@engineer_page.route('/reported_scooters', methods=['GET'])
def get_reported_scooters():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all scooter details for reported scooters
        query = "SELECT * FROM scooters WHERE Status = %s"
        cursor.execute(query, ("To Be Repaired",))
        scooter_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the fetched data to a list of dictionaries
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


@engineer_page.route("/reported_scooters_page", methods=['GET'])
def repair_statuses_page():
    response = requests.get("http://" + ip_address + ":" + port + "/reported_scooters")
    data = json.loads(response.text)

    return render_template("engineer/reported_scooters.html", reported_scooters=data)


@engineer_page.route('/repair_statuses', methods=['GET'])
def repair_statuses():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all repair details from the repairs table
        query = "SELECT * FROM repairs"
        cursor.execute(query)
        repair_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the fetched data to a list of dictionaries
        repairs = []
        for repair in repair_data:
            repair_dict = {
                "RequestID": repair[0],
                "ScooterID": repair[1],
                "UserID": repair[2],
                "RepairStatus": repair[3],
                "Description": repair[4]
            }
            repairs.append(repair_dict)

        return jsonify({"repairs": repairs})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)})


@engineer_page.route("/repair_status_page", methods=['GET'])
def reported_scooters_page():
    response = requests.get("http://" + ip_address + ":" + port + "/repair_statuses")
    data = json.loads(response.text)

    return render_template("engineer/update_repair_page.html", repair_data=data)


@engineer_page.route('/engineer_page')
def engineer_page_render():
    return render_template('engineer/engineer.html')


@engineer_page.route('/update_repair_state', methods=['POST', 'GET'])
def update_repair_state():
    try:

        # FIXME: UPDATE STATUS IN SCOOTER TABLE AS WELL
        data = request.form
        requestID = data['request_id']

        connection = create_db_connection()
        cursor = connection.cursor()

        # Fetch all repair details from the repairs table
        query = "SELECT RepairStatus FROM repairs WHERE RequestID = %s"
        cursor.execute(query, (requestID,))
        repair_data = cursor.fetchone()
        repairStatus = repair_data[0]
        
        cursor.close()
        connection.close()

        # swap repair status
        if repairStatus == "Complete":
            repairStatus = "In Progress"
        else:
            repairStatus = "Complete"

        print(repairStatus)

        connection = create_db_connection()
        cursor = connection.cursor()

        # Update to opposite repair status
        query = "UPDATE repairs SET RepairStatus = %s WHERE RequestID = %s"
        cursor.execute(query, (repairStatus, requestID))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect("http://" + ip_address + ":" + port + "/repair_status_page")
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)})


@engineer_page.route('/engineer_lock_unlock')
def engineer_lock_unlock():
    user_id = session.get('user_id')
    response1 = requests.get("http://" + ip_address + ":" + port + "/engineer_active_bookings_unlocked")
    lockable = json.loads(response1.text)

    response2 = requests.get("http://" + ip_address + ":" + port + "/engineer_active_bookings_locked")
    unlockable = json.loads(response2.text)

    return render_template("engineer/lock_unlock.html", lockable=lockable, unlockable=unlockable)


@engineer_page.route("/engineer_unlock_scooter/<int:scooter_id>/<int:booking_id>")
def engineer_unlock_scooter(scooter_id, booking_id):
    # Check available money on account (needs to be enough to book the scooter)
    # Set LockStatus in booking entry to "Unlocked"
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Update the booking status in the database
        update_booking_query = "UPDATE bookings SET LockStatus = 'Unlocked' WHERE BookingID = %s"
        cursor.execute(update_booking_query, (booking_id,))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({"message": "Scooter Unlocked Successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)})

@engineer_page.route("/engineer_lock_scooter/<int:scooter_id>/<int:booking_id>", methods=['GET'])
def engineer_lock_scooter(scooter_id, booking_id):
    # Charge from available money on account
    # Set LockStatus in booking entry to "Locked"
    # Set BookingStatus in booking entry to "Completed"
    # Set ScooterStatus in scooter entry to "Available"
    # Set new location
    try:
        userID = session.get('user_id')
        new_location = request.args.get('newLocation')
        print(new_location)

        connection = create_db_connection()
        cursor = connection.cursor()

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

        return jsonify({"message": "Scooter Locked Successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)})
    

# return list of locked scooters that are actively booked by a user
@engineer_page.route('/engineer_active_bookings_unlocked', methods=['GET'])
def engineer_get_active_booking_history_unlocked():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the customer's active bookings
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus FROM bookings WHERE BookingStatus = 'Active' AND LockStatus = 'Unlocked'"
        cursor.execute(query,)
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
    

@engineer_page.route('/engineer_active_bookings_locked', methods=['GET'])
def engineer_get_active_booking_history_locked():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get the customer's active bookings
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus FROM bookings WHERE AND BookingStatus = 'Active' AND LockStatus = 'Locked'"
        cursor.execute(query,)
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
