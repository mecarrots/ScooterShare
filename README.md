# IoT Major Assignment

### Contributors:
- Jed
- [Dom](https://github.com/weggith)

## Features

Full-stack Scooter Share application built to run on two Raspberry Pi's, utilizing Python, Flask and Google Cloud Platform.

### User Registration
- Implemented a registration system using Flask with encrypted password storage.
- Integrated user registration for customers, ensured secure login for all three account types (customer, admin, engineer).

### Customer Functionality
- Developed functionality enabling users to view detailed information about available scooters, including make, color, location, remaining power, and cost per time.
- Enabled customer users to book scooters, manage booking history, and top up their accounts.
- Implemented a system allowing users to unlock and lock their booked scooters.

### Admin Functionality
- Created admin tools for overseeing scooter usage, booking history, and customer top-up history.
- Implemented data visualization reports of scooter booking/usage history using Seaborn.
- Enabled admins to view the status of all scooters, report issues, and modify customer and scooter information.

### Engineer Functionality
- Allowed engineers to check reported scooter issues and view scooter locations.
- Implemented functionality for engineers to create reports and change scooter status accordingly.

### Notes
- Utilized a CI pipeline, ran using Github Actions to ensure PEP8 coding style.
- Github utilized for version control, Trello for project management.
- This assignment recieved a HD (high distinction).

## How to run:
*Database is no longer hosted, will not function as intended.*

First, install dependencies:
```
sudo pip install flask_session flask_bcrypt flask_cors flask_sqlalchemy mysqlclient seaborn
```
Configure config.ini with the correct IP of the MasterPi, for example my PI's IP on my local network is 192.168.0.3.
```
[app]
ip_address = 192.168.0.3
port = 5000
```
To start the flask app, navigate to flask_backend and run:
```
sudo flask --app app.py run --host=0.0.0.0
```
The app should now be accessible on `192.168.0.3:5000` (depending on config)

