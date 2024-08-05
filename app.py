from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
from threading import Thread
from dotenv import load_dotenv

app = Flask(__name__)
VISITOR_FILE = 'visitors.json'

# Load environment variables from .env file
load_dotenv()


def load_visitor_details():
    if os.path.exists(VISITOR_FILE):
        with open(VISITOR_FILE, 'r') as file:
            return json.load(file)
    return {}


def save_visitor_details(visitor_details):
    with open(VISITOR_FILE, 'w') as file:
        json.dump(visitor_details, file)


visitor_details = load_visitor_details()


@app.route('/')
def serve_home():
    return send_from_directory(os.path.join(app.root_path, ''), 'index.html')


@app.route('/sign_in')
def serve_sign_in():
    return send_from_directory(os.path.join(app.root_path, ''), 'sign_in.html')


@app.route('/sign_out')
def serve_sign_out():
    return send_from_directory(os.path.join(app.root_path, ''), 'sign_out.html')


@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)


@app.route('/visitor_names', methods=['GET'])
def get_visitor_names():
    names = [name for name, details in visitor_details.items() if not details.get('signed_out', False)]
    return jsonify(names)


@app.route('/submit_sign_in', methods=['POST'])
def submit_sign_in():
    try:
        full_name = request.form['fullName']
        company = request.form['company']
        mobile_number = request.form['mobileNumber']
        site_contact = request.form['siteContact']
        submission_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Print form data for debugging
        print(f"Sign In: {full_name}, {company}, {mobile_number}, {site_contact}, {submission_time}")

        # Store visitor details
        visitor_details[full_name] = {
            'company': company,
            'mobile_number': mobile_number,
            'site_contact': site_contact,
            'sign_in_time': submission_time,
            'signed_out': False
        }
        save_visitor_details(visitor_details)

        # Send sign-in confirmation email
        email_body = f"""
        Visitor Sign-In Confirmation:

        Full Name: {full_name}
        Company: {company}
        Mobile Number: {mobile_number}
        Site Contact: {site_contact}
        Sign In Time: {submission_time}
        """
        send_email(full_name, "Sign In Confirmation", email_body)

        return jsonify({"message": "Sign in successful"}), 200
    except Exception as e:
        print(f"Error during sign in: {e}")
        return jsonify({"message": str(e)}), 500


@app.route('/submit_sign_out', methods=['POST'])
def submit_sign_out():
    try:
        full_name = request.form['fullName']
        sign_out_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Print form data for debugging
        print(f"Sign Out: {full_name}, {sign_out_time}")

        if full_name in visitor_details:
            visitor_details[full_name]['signed_out'] = True
            visitor_details[full_name]['sign_out_time'] = sign_out_time
            save_visitor_details(visitor_details)

            # Retrieve the stored details for the visitor
            company = visitor_details[full_name]['company']
            mobile_number = visitor_details[full_name]['mobile_number']
            site_contact = visitor_details[full_name]['site_contact']

            # Send sign-out confirmation email
            email_body = f"""
            Visitor Sign-Out Confirmation:

            Full Name: {full_name}
            Company: {company}
            Mobile Number: {mobile_number}
            Site Contact: {site_contact}
            Sign Out Time: {sign_out_time}
            """
            send_email(full_name, "Sign Out Confirmation", email_body)

            return jsonify({"message": "Sign out successful"}), 200
        else:
            return jsonify({"message": "Visitor not found"}), 404
    except Exception as e:
        print(f"Error during sign out: {e}")
        return jsonify({"message": str(e)}), 500


def send_email(visitor_name, subject, body):
    sender_email = os.getenv('SENDER_EMAIL')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    password = os.getenv('EMAIL_PASSWORD')

    if not sender_email or not receiver_email or not password:
        print("Email configuration is missing")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print("Connecting to the SMTP server...")
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(sender_email, password)
        print("Sending the email...")
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_daily_summary():
    unsigned_out_visitors = {name: details for name, details in visitor_details.items() if not details['signed_out']}
    if unsigned_out_visitors:
        # Email details
        sender_email = os.getenv('SENDER_EMAIL')
        receiver_email = os.getenv('RECEIVER_EMAIL')
        password = os.getenv('EMAIL_PASSWORD')

        if not sender_email or not receiver_email or not password:
            print("Email configuration is missing for daily summary")
            return

        subject = "Daily Visitor Sign Out Summary"
        body = "The following visitors have not signed out:\n\n"
        for name, details in unsigned_out_visitors.items():
            body += (f"Full Name: {name}\nCompany: {details['company']}\nMobile Number: {details['mobile_number']}\n"
                     f"Site Contact: {details['site_contact']}\nSign In Time: {details['sign_in_time']}\n\n")

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            print("Connecting to the SMTP server...")
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(sender_email, password)
            print("Sending the email...")
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send daily summary email: {e}")


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Schedule the daily summary email at 4:30 PM
schedule.every().day.at("16:30").do(send_daily_summary)

# Start the scheduling in a separate thread
t = Thread(target=run_schedule)
t.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
