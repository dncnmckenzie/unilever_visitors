import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sender_email = os.getenv('SENDER_EMAIL')
receiver_email = os.getenv('RECEIVER_EMAIL')
password = os.getenv('EMAIL_PASSWORD')

subject = "Test Email"
body = "This is a test email to check the email configuration."

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
    print("Test email sent successfully!")
except Exception as e:
    print(f"Failed to send test email: {e}")
