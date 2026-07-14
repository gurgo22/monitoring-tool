from flask import Flask, request, render_template
from config import EXTERNAL_SYSTEM_PORT
'''
Flask app for receiving the webhooks containing the details of an incident
'''
app = Flask(__name__)

current_incident = None

@app.route('/')
def main_page():
    '''
    Displays the main page
    '''
    return render_template('index.html', incident = current_incident)

@app.route("/webhookcallback", methods=["POST"])
def hook():
    '''
    Displays the details of an incident
    '''
    global current_incident 
    
    if request.is_json:

        current_incident = request.get_json()
        
        print(f"Webhook triggered! Latest incident is now: {current_incident.get('key')}")
        return {"status": "success", "message": "Webhook received"}, 200
    else:
        return {"status": "error", "message": "Request must be JSON"}, 400

if __name__ == "__main__":
    app.run(debug=True, port=EXTERNAL_SYSTEM_PORT)