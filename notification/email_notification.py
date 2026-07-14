import smtplib , config, os, email.utils
from email.message import EmailMessage
from models.incident import Incident
from dotenv import load_dotenv
'''
Module for sending email notifications
'''
load_dotenv()

def send_email_notification(incident : Incident):
    '''
    Sends an email notification using the OCI Email Service with the details of an Incident object.
    
    Parameters
    ----------
    incident: Incident
        Incident object which the email is about
    '''
    USERNAME_SMTP = os.getenv('OCI_EMAIL_USER')
    PASSWORD_SMTP = os.getenv('OCI_EMAIL_PASSW')
    
    SUBJECT = f"[{incident._severity.upper()}] Pipeline Incident: Stream {incident._stream_id}"

    BODY_TEXT = (
        f"Data Pipeline Incident Alert\r\n"
        f"----------------------------\r\n"
        f"Severity:  {incident._severity}\r\n"
        f"Stream ID: {incident._stream_id}\r\n"
        f"Timestamp: {incident._timestamp}\r\n"
        f"Key:       {incident._key}\r\n\r\n"
        f"Details:\r\n{incident._details}\r\n"
    )

    header_color = "orange"

    if (incident._severity == 'HIGH'):
        header_color = "red"
    
    BODY_HTML = f"""\
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif;">
      <h2 style="color: {header_color};">Data Pipeline Incident Alert</h2>
      <ul>
        <li><strong>Severity:</strong> {incident._severity}</li>
        <li><strong>Stream ID:</strong> {incident._stream_id}</li>
        <li><strong>Timestamp:</strong> {incident._timestamp}</li>
        <li><strong>Incident Key:</strong> {incident._key}</li>
      </ul>
      <h3>Details:</h3>
      <p style="background-color: #f4f4f4; padding: 10px; border-left: 4px solid {header_color};">
        {incident._details}
      </p>
    </body>
    </html>
    """

    msg = EmailMessage()
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((config.EMAIL_SENDERNAME, config.EMAIL_NOTIFICATION_SENDERS))
    msg['To'] = config.EMAIL_NOTIFICATION_RECIPIENTS

    msg.set_content(BODY_TEXT)
    msg.add_alternative(BODY_HTML, subtype='html')

    try: 
        server = smtplib.SMTP(config.OCI_HOST, config.OCI_PORT)
        server.ehlo()

        server.starttls()
        server.ehlo()
        
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        
        server.sendmail(
            config.EMAIL_NOTIFICATION_SENDERS, 
            config.EMAIL_NOTIFICATION_RECIPIENTS, 
            msg.as_string()
        )
        server.close()
        print("Email notification sent!")
    except Exception as e:
        print(f"Error sending email for incident {incident._key}: {e}")
    else:
        print(f"Alert successfully sent for incident: {incident._key}")