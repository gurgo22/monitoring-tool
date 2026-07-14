def get_secret(secret_name):
    '''
    Reads Docker/local secrets values
    '''
    secret_path = f"/run/secrets/{secret_name}"
    local_path = f"secrets/{secret_name}.txt"
    
    try:
        with open(secret_path, "r") as secret_file:
            return secret_file.read().strip()
    
    except FileNotFoundError:

        try:
            with open(local_path, "r") as secret_file:
                return secret_file.read().strip()
                    
        except FileNotFoundError:
            print(f"Could not find '{secret_name}' in Docker or locally!")
            return None

#DATASET GENERATOR
FILE1 = "generated_file_1.json"
FILE2 = "generated_file_2.json"
DATASET_SIZE = 100000

#FILENAME FOR THE DOCKER COMPOSE BIND VOLUME TARGET
FILE_TARGET_NAME = "generated_file.json"

#POSTGRE DATABASE
DB_NAME = get_secret('postgres_db_name')
DB_USER = get_secret('postgres_user')
DB_PASS = get_secret('postgres_password')
DB_HOST = 'postgres'
DB_PORT = '5432'

#REDIS
REDIS_HOSTNAME = 'redis'
REDIS_PORT = '6379'
STREAM_IDS = ["stream1", "stream2"]

#PRODUCER
MAX_STREAM_SIZE = 100000
BATCH_SIZE = 10
PRODUCE_DELAY = 0.1

#CONSUMER
VALIDATION_CHECK_INTERVAL = 1
INCIDENT_EMAIL_RATE = 100
CONSUMER_GROUP_NAME = 'monitoring_group'
CONSUMER_NAME = 'consumer'
READ_BLOCK_MS = 100

#EMAIL NOTIFCATION
EMAIL_SENDERNAME = 'Monitoring Tool'
OCI_HOST = "smtp.email.eu-frankfurt-1.oci.oraclecloud.com"
OCI_PORT = 587
EMAIL_NOTIFICATION_RECIPIENTS = "gurgo22@gmail.com"
EMAIL_NOTIFICATION_SENDERS = "gurgo22@gmail.com"

#WEBHOOK NOTIFICATION
#SENDING FROM DOCKER NETWORK TO LOCAL NETWORK
EXTERNAL_SYSTEM_URL = "http://host.docker.internal:5000/webhookcallback"
EXTERNAL_SYSTEM_PORT = 5000
WEBHOOK_TIMEOUT = 3

#DASHBOARD
#THE MAXIMUM AMOUNT OF RECORDS TO CREATE THE DATA CLEANING ADVICE ON
DATA_CLEANING_MAX_DATESET_SIZE = 100
NUMBER_OF_STREAMS = 2
 