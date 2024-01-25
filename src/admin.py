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
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
# import numpy
from datetime import date, timedelta, datetime
import os
import glob

import configparser
config = configparser.ConfigParser()
config.read('config.ini')
ip_address = config.get('app', 'ip_address')
port = config.get('app', 'port')


matplotlib.use('Agg')

app = Flask(__name__)

HOST = ""
USER = ""
PASSWORD = ""
DATABASE = ""


def create_db_connection():
    return MySQLdb.connect(
        host=HOST, user=USER, passwd=PASSWORD, db=DATABASE
    )


def clear_existing_images(visualisations_dir):
    # Remove existing image files in the 'visualisations' directory
    existing_images = glob.glob(os.path.join(visualisations_dir, '*.png'))
    for image in existing_images:
        os.remove(image)


admin_page = Blueprint('admin_page', __name__, template_folder='templates')


@admin_page.route('/customer_list', methods=['GET'])
def getCustomers():
    try:
        if request.method == 'GET':
            connection = create_db_connection()
            cur = connection.cursor()

            # Get list of customers only for admin page
            select_customers = """
                SELECT * FROM users WHERE UserType = 'Customer'
            """
            cur.execute(select_customers)
            data = cur.fetchall()

            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})


@admin_page.route('/visualisation/<int:scooter_id>', methods=['GET'])
def generate_usage_report(scooter_id):
    try:
        # Use flask static directory to save charts
        visualisations_dir = 'static'
        # Create it if it doesn't exist
        os.makedirs(visualisations_dir, exist_ok=True)
        # Clear existing images in the 'visualisations' directory
        clear_existing_images(visualisations_dir)

        connection = create_db_connection()
        cursor = connection.cursor()

        today = date.today()
        one_week_ago = today - timedelta(days=7)

        # Get daily distance covered data from db
        query_distance = """
        SELECT DATE(UsageDate) AS UsageDate, SUM(DistanceCovered) AS TotalDistance
        FROM scooter_usage
        WHERE ScooterID = %s AND UsageDate >= %s
        GROUP BY DATE(UsageDate)
        ORDER BY DATE(UsageDate)
        """
        cursor.execute(query_distance, (scooter_id, one_week_ago))
        distance_data = cursor.fetchall()

        # Get weekly time used data from db
        query_time = """
        SELECT YEARWEEK(UsageDate) AS Week, SUM(TimeUsed) AS TotalTime
        FROM scooter_usage
        WHERE ScooterID = %s
        GROUP BY YEARWEEK(UsageDate)
        ORDER BY YEARWEEK(UsageDate)
        LIMIT 10
        """
        cursor.execute(query_time, (scooter_id,))
        time_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Process the daily distance data for the last 7 days
        dates_distance = [entry[0] for entry in distance_data]
        distances = [entry[1] for entry in distance_data]

        # Process the weekly time data for the last 10 weeks
        weeks_data = [entry[0] for entry in time_data]
        years = [int(str(week)[:4]) for week in weeks_data]
        weeks_in_year = [int(str(week)[4:]) for week in weeks_data]
        time_used = [entry[1] for entry in time_data]

        # Create a Seaborn bar chart for daily distance
        distance_chart_path = os.path.join(
            visualisations_dir, 'daily_distance_chart.png')
        plt.figure(figsize=(10, 6))
        sns.barplot(x=dates_distance, y=distances, color='b')
        plt.xlabel('Date')
        plt.ylabel('Distance Covered (km)')
        plt.title('Daily Distance Covered for Scooter ID {}'.format(scooter_id))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(distance_chart_path)
        plt.close()

        # Create a Seaborn bar chart for weekly time used
        weekly_time_chart_path = os.path.join(
            visualisations_dir, 'weekly_time_chart.png')
        plt.figure(figsize=(10, 6))
        sns.barplot(x=weeks_in_year, y=time_used, color='g')
        plt.xlabel('Week in Year')
        plt.ylabel('Time Used (minutes)')
        plt.title('Weekly Time Used for Scooter ID {}'.format(scooter_id))
        plt.tight_layout()
        plt.savefig(weekly_time_chart_path)
        plt.close()

        return jsonify({
            "scooter_id": scooter_id
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@admin_page.route('/scooter_by_id/<int:scooter_id>', methods=['GET'])
def get_scooter_by_id(scooter_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get scooter details by ID
        query = "SELECT * FROM scooters WHERE ScooterID = %s"
        cursor.execute(query, (scooter_id,))
        scooter_data = cursor.fetchone()

        cursor.close()
        connection.close()

        if scooter_data:
            # Convert the fetched data to a dictionary
            scooter_details = {
                "ScooterID": scooter_data[0],
                "Make": scooter_data[1],
                "Colour": scooter_data[2],
                "Location": scooter_data[3],
                "RemainingPower": scooter_data[4],
                "CostPerTime": scooter_data[5],
                "Status": scooter_data[6]
            }

            return jsonify({"scooter_id": scooter_id,
                            "scooter_details": scooter_details})
        else:
            return jsonify({"message": "Scooter not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_page.route('/customer_by_id/<int:customer_id>', methods=['GET'])
def get_customer_by_id(customer_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get customer details by ID
        query = "SELECT * FROM users WHERE UserID = %s"
        cursor.execute(query, (customer_id,))
        customer_data = cursor.fetchone()

        cursor.close()
        connection.close()

        if customer_data:
            # Convert the fetched data to a dictionary
            customer_details = {
                "UserID": customer_data[0],
                "UserType": customer_data[1],
                "Username": customer_data[2],
                "Password": customer_data[3],
                "FirstName": customer_data[4],
                "LastName": customer_data[5],
                "PhoneNumber": customer_data[6],
                "Email": customer_data[7],
                "AvailableMoney": customer_data[8]
            }

            return jsonify({"customer_id": customer_id,
                            "customer_details": customer_details})
        else:
            return jsonify({"message": "Customer not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_page.route('/add_scooter', methods=['POST'])
def add_scooter():
    # Get data from the form
    make = request.form.get('make')
    colour = request.form.get('colour')
    location = request.form.get('location')
    remaining_power = request.form.get('remaining_power')
    cost_per_time = request.form.get('cost_per_time')
    status = request.form.get('status')

    connection = create_db_connection()
    cursor = connection.cursor()

    # Insert into the scooters table
    insert_query = """INSERT INTO scooters (Make, Colour, Location,
    RemainingPower, CostPerTime, Status) VALUES (%s, %s, %s, %s, %s, %s)"""
    cursor.execute(
        insert_query,
        (make,
         colour,
         location,
         remaining_power,
         cost_per_time,
         status))
    connection.commit()

    cursor.close()
    connection.close()

    return render_template('admin/admin.html')

@admin_page.route('/edit_scooter', methods=['POST'])
def update_scooter():
    if request.method == 'POST':
        # Get data from the form
        scooter_id = request.form['scooter_id']
        make = request.form['make']
        colour = request.form['colour']
        location = request.form['location']
        remaining_power = request.form['remaining_power']
        cost_per_time = request.form['cost_per_time']
        status = request.form['status']

        connection = create_db_connection()
        cursor = connection.cursor()

        try:
            # Update data in the scooters table
            update_query = """UPDATE scooters SET Make = %s,
            Colour = %s, Location = %s,
            RemainingPower = %s, CostPerTime = %s,
            Status = %s WHERE ScooterID = %s"""
            cursor.execute(
                update_query,
                (make,
                 colour,
                 location,
                 remaining_power,
                 cost_per_time,
                 status,
                 scooter_id))
            connection.commit()
            message = "Scooter updated successfully"

        except Exception as e:
            message = f"Error: {e}"
            connection.rollback()

        finally:
            cursor.close()
            connection.close()

        return render_template('admin/admin.html')

@admin_page.route('/edit_user', methods=['POST'])
def update_user():
    if request.method == 'POST':
        # Get data from the form
        user_id = request.form['user_id']
        usertype = request.form['usertype']
        username = request.form['username']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        phonenumber = request.form['phonenumber']
        email = request.form['email']
        availablemoney = request.form['availablemoney']

        connection = create_db_connection()
        cursor = connection.cursor()

        try:
            # Update data in the users table
            update_query = """
            UPDATE users
            SET UserType = %s,
                Username = %s,
                FirstName = %s,
                LastName = %s,
                PhoneNumber = %s,
                Email = %s,
                AvailableMoney = %s
            WHERE UserID = %s
            """
            print(usertype, username, firstname, lastname,
                  phonenumber, email, availablemoney, user_id)
            cursor.execute(
                update_query,
                (usertype, username, firstname, lastname,
                 phonenumber, email, availablemoney, user_id)
            )
            connection.commit()
            message = "User updated successfully"

        except Exception as e:
            message = f"Error: {e}"
            connection.rollback()

        finally:
            cursor.close()
            connection.close()

        return render_template('admin/admin.html')


@admin_page.route('/delete_scooter/<int:scooter_id>', methods=['DELETE'])
def delete_scooter(scooter_id):
    connection = create_db_connection()
    cursor = connection.cursor()

    try:
        # Delete scooter by ID
        delete_query = "DELETE FROM scooters WHERE ScooterID = %s"
        cursor.execute(delete_query, (scooter_id,))
        connection.commit()
        message = "Scooter deleted successfully"

    except Exception as e:
        message = f"Error: {e}"
        connection.rollback()

    finally:
        cursor.close()
        connection.close()

    return jsonify({"message": message})


@admin_page.route('/scooter_usage_history/<int:scooter_id>', methods=['GET'])
def get_scooter_usage_history(scooter_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get scooter usage history by
        query = "SELECT UsageID, ScooterID, TimeUsed, DistanceCovered, UsageDate FROM scooter_usage WHERE ScooterID = %s"
        cursor.execute(query, (scooter_id,))
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
                "UsageDate": entry[4].strftime('%d-%m-%Y')  # dd-mm-yyyy
            }
            scooter_usage_history.append(entry_dict)

        return jsonify({"scooter_id": scooter_id, "scooter_usage_history": scooter_usage_history})

    except Exception as e:
        return jsonify({"error": str(e)})

@admin_page.route('/add_repair/<int:page_id>', methods=['POST'])
def add_repair(page_id):
    # Get data from the form
    scooter_id = request.form.get('scooter_id')
    user_id = request.form.get('user_id')
    repair_status = 'In Progress'
    description = request.form.get('description')

    connection = create_db_connection()
    cursor = connection.cursor()

    try:
        # Change scooter status to under repair when a repair is added
        update_query = "UPDATE scooters SET Status = 'To Be Repaired' WHERE ScooterID = %s"
        cursor.execute(update_query, (scooter_id,))

        # Insert repair entry into the repairs table
        insert_query = """INSERT INTO repairs
         (ScooterID, UserID, RepairStatus, Description)
        VALUES (%s, %s, %s, %s)"""
        cursor.execute(
            insert_query,
            (scooter_id, user_id, repair_status, description))

        connection.commit()
        message = "Repair entry added successfully"

        # Send email with scooter details
        email_message = f"Scooter ID: {scooter_id}\nUser ID: {user_id}\nRepair Description: {description}"

        # Send the email to all engineers
        connection = create_db_connection()
        cursor = connection.cursor()
        select_query = "SELECT Email FROM users WHERE UserType = 'Engineer'"
        cursor.execute(select_query)
        engineers = cursor.fetchall()

        for engineer in engineers:
            engineer_email = engineer[0]

            response = requests.post(
                "MAILGUN API",
                auth=("api", "API KEY"),
                data={
                    "from": "MAILGUN EMAIL",
                    "to": [engineer_email],
                    "subject": "New Scooter Repair Request",
                    "text": email_message
                })
            print(f"Email sent to {engineer_email}. Response:", response.text)

    except Exception as e:
        message = f"Error: {e}"
        connection.rollback()

    finally:
        cursor.close()
        connection.close()

    if page_id == 1:
        return render_template("customer/customer.html")
    if page_id == 2:
        return render_template('admin/admin.html')


@admin_page.route('/booking_history/<int:scooter_id>', methods=['GET'])
def get_booking_history(scooter_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get booking history by UserID
        query = "SELECT BookingID, ScooterID, BookingTime, \
        BookingStatus FROM bookings WHERE ScooterID = %s"
        cursor.execute(query, (scooter_id,))
        booking_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the fetched data to a list of dictionaries
        booking_history = []
        for booking in booking_data:
            booking_history.append({
                "BookingID": booking[0],
                "ScooterID": booking[1],
                # Format the date and time
                "BookingTime": booking[2].strftime("%Y-%m-%d %H:%M:%S"),
                "BookingStatus": booking[3]
            })

        return jsonify({"booking_history": booking_history})

    except Exception as e:
        return jsonify({"error": str(e)})


@admin_page.route('/topup_history/<int:user_id>', methods=['GET'])
def get_topup_history(user_id):
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get topup history by UserID
        query = "SELECT PaymentID, Amount FROM payments WHERE UserID = %s"
        cursor.execute(query, (user_id,))
        topup_data = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert the data into a list of dictionaries
        topup_history = []
        for topup in topup_data:
            topup_history.append({
                "PaymentID": topup[0],
                "Amount": topup[1]
            })

        return jsonify({"user_id": user_id, "topup_history": topup_history})

    except Exception as e:
        return jsonify({"error": str(e)})


@admin_page.route('/all_scooters', methods=['GET'])
def get_all_scooters():
    try:
        connection = create_db_connection()
        cursor = connection.cursor()

        # Get all scooters
        query = "SELECT * FROM scooters"
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


@admin_page.route('/admin_page')
def admin_page_render():
    return render_template('admin/admin.html')


@admin_page.route("/scooter_edit/<int:scooter_id>", methods=['GET'])
def scooter_edit_page(scooter_id):
    response = requests.get(
        "http://" + ip_address + ":" + port + "/scooter_by_id/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("admin/scooter_edit.html", scooter_edit=data)


@admin_page.route("/scooter_delete/<int:scooter_id>", methods=['GET', 'DELETE'])
def scooter_delete_page(scooter_id):
    response = requests.delete(
        "http://" + ip_address + ":" + port + "/delete_scooter/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("admin/scooter_delete.html", message=data)


@admin_page.route("/scooter_status", methods=['GET'])
def scooter_status_page():
    response = requests.get("http://" + ip_address + ":" + port + "/all_scooter_status")
    data = json.loads(response.text)

    return render_template("scooter_status.html", scooter_status=data)


@admin_page.route("/customer_detail", methods=['GET'])
def customer_detail_page():
    response = requests.get("http://" + ip_address + ":" + port + "/customer_list")
    data = json.loads(response.text)

    return render_template("admin/customer.html", user=data)


@admin_page.route("/scooter_visualisation/<int:scooter_id>", methods=['GET'])
def scooter_visualisation_page(scooter_id):
    response = requests.get(
        "http://" + ip_address + ":" + port + "/visualisation/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("admin/scooter_visualisation.html", visualisation=data)


@admin_page.route("/customer_edit/<int:user_id>", methods=['GET', 'PUT'])
def customer_edit_page(user_id):
    response = requests.get(
        "http://" + ip_address + ":" + port + "/customer_by_id/" + str(user_id))
    data = json.loads(response.text)

    return render_template("admin/customer_edit.html", customer_edit=data)


@admin_page.route('/add_scooter', methods=['GET'])
def add_scooter_page():
    return render_template('admin/scooter_add.html')


@admin_page.route("/report_scooter/<int:scooter_id>", methods=['GET'])
def scooter_report_page(scooter_id):
    user_id = session.get('user_id')
    response = requests.get(
        "http://" + ip_address + ":" + port + "/scooter_by_id/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("admin/scooter_report.html", scooter=data, user_id_=user_id)


@admin_page.route("/view_all_scooters", methods=['GET'])
def view_all_scooters_page():
    response = requests.get("http://" + ip_address + ":" + port + "/all_scooters")
    data = json.loads(response.text)

    return render_template("admin/view_all_scooters.html", scooters=data)


@admin_page.route("/create_user_page", methods=['GET'])
def create_user_page():
    return render_template("admin/customer_add.html")


@admin_page.route('/scooter_usage_admin/<int:scooter_id>', methods=['GET'])
def view_scooter_usage_history(scooter_id):
    response = requests.get(
        f"http://" + ip_address + ":" + port + "/scooter_usage_history/" + str(scooter_id))
    data = json.loads(response.text)
    print(data)
    return render_template('admin/scooter_usage.html', scooter_data=data)


@admin_page.route("/scooter_booking/<int:scooter_id>", methods=['GET'])
def scooter_booking_page(scooter_id):
    response = requests.get(
        "http://" + ip_address + ":" + port + "/booking_history/" + str(scooter_id))
    data = json.loads(response.text)

    return render_template("admin/scooter_booking.html", booking_history=data)
