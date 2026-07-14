import requests
from config import EXTERNAL_SYSTEM_URL, WEBHOOK_TIMEOUT
from models.incident import Incident
'''
Module for the sending of webhook notifications
'''
def send_notification(incident : Incident):
    '''
    Sends a webhook with a POST HTTP request with the details of an incident

    Parameters
    ----------
    incident: Incident  
        The incident object containing details about the incident
    '''
    try:
        response = requests.post(EXTERNAL_SYSTEM_URL, json = incident.to_dict(), timeout = WEBHOOK_TIMEOUT)

        response.raise_for_status() 
        print(f"Webhook notification sent successfully! Status Code: {response.status_code}")
    
    except Exception as exc:
        print(f"Failed to send webhook: {exc}")
