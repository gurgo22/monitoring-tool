import time, json, config, datetime, redis_utilities
import services.validation_service as validation_service
import services.database_service as database_service
import notification.email_notification as email_notification
import notification.webhook_notification as webhook_notification
from models.incident import Incident
from models.base_schema import BaseSchema
'''
Controls the monitoring process and consumes data from the Redis stream
'''
last_check_time = time.time()

incident_count = 0

is_monitoring_stopped = True

redis_stream = redis_utilities.connect_to_redis()

db_connection = database_service.try_connect_to_db()

redis_utilities.create_consumer_group(redis_stream)

def send_notifications(incident: Incident):
    '''
    Initializes the notifications system about the current incident

    Parameters
    ----------
    incident: Incident  
        The incident object containing details about the incident
    '''
    global incident_count
    webhook_notification.send_notification(incident)
    
    if (incident_count == config.INCIDENT_EMAIL_RATE):
        email_notification.send_email_notification(incident)
        incident_count = 0

def handle_changes(changes: list, stream_id: str, new_data_schema: dict):
    '''
    Inserts all of the incidents into the database
    and sends notifications about incidents related to a schema drift
    
    Parameters
    ----------
    changes: list
        List of changes in the schema of a record
    stream_id: str  
        Identifier of a stream
    new_data_schema: dictionary
        Schema of the record that will the base schema from now on 
    '''
    global incident_count

    for change in changes:
                
        incident = Incident(change[0], datetime.datetime.now(), stream_id, change[1], change[2])
        database_service.insert_incident(db_connection, incident)

        incident_count += 1
        print("Incident count", incident_count, flush=True)

        send_notifications(incident)

    base_schema = BaseSchema(datetime.datetime.now(), stream_id, json.dumps(new_data_schema))
    database_service.insert_base_schema(db_connection, base_schema)

    print("Finished checking for changes!\n", flush=True)

def deserialize_received_data(stream_id: str, msg_id: str, received_data: dict) -> dict:
    '''
    Deserializes the received json data into a python object

    Parameters
    ----------
    stream_id: str  
        Identifier of a stream
    msg_id: str
        Identifier of a message in the redis stream
    received_data: dictionary 
        Data from the redis stream
    
    Returns
    ----------
    new_data: dictionary
    '''
    try:
        json_string = received_data["payload"]
        new_data = json.loads(json_string)

    except KeyError:
        print(f"Stream: {stream_id} | Msg: {msg_id} - Missing 'payload' key. Data: {received_data}")
    except TypeError as e:
        #IF received_data IS None, OR IF json_string IS NOT str TYPE
        print(f"Stream: {stream_id} | Msg: {msg_id} - Type error: {e}. Data: {received_data}")
    except json.JSONDecodeError as e:
        print(f"Stream: {stream_id} | Msg: {msg_id} - Unable to decode JSON. Error: {e}")
    except Exception as e:
        #ALL OTHER JSON RELATED ISSUES
        print(f"Stream: {stream_id} | Msg: {msg_id} - JSON object error: {e}")

    return new_data

def validate_schema(stream_id: str, msg_id: str, received_data: dict):
    '''
    Initiates the validation process

    Parameters
    ----------
    stream_id: str  
        Identifier of a stream
    msg_id: str
        Identifier of a message in the redis stream
    received_data: dictionary 
        Data from the redis stream
    '''
    new_data = deserialize_received_data(stream_id, msg_id, received_data)

    print(f"Validating and processing {msg_id} from {stream_id}: {new_data}", flush=True)

    new_data_schema = validation_service.build_schema(new_data)

    if (database_service.does_stream_have_base_schema(db_connection, stream_id)):
        
        schema_str = database_service.get_latest_schema(db_connection, stream_id)
        latest_schema_dict = json.loads(schema_str)
        
        changes = list(validation_service.get_schema_changes(latest_schema_dict, new_data_schema))

        if (len(changes)) > 0:
            handle_changes(changes, stream_id, new_data_schema)
        else:
            print("There was no change in the schema!", flush=True)
    else:
        base_schema = BaseSchema(datetime.datetime.now(), stream_id, json.dumps(new_data_schema))
        database_service.insert_base_schema(db_connection, base_schema)

    redis_stream.xack(stream_id, config.CONSUMER_GROUP_NAME, msg_id)
    print("---------------------------------------------------")

def handle_message(stream_id: str, msg_id: str, received_data: dict):
    '''
    Handles a message that does not get validated

    Parameters
    ----------
    stream_id: str  
        Identifier of a stream
    msg_id: str
        Identifier of a message in the redis stream
    received_data: dictionary 
        Data from the redis stream
    '''
    new_data = deserialize_received_data(stream_id, msg_id, received_data)

    print(f"Processing {msg_id} from {stream_id}: {new_data}", flush=True)

    redis_stream.xack(stream_id, config.CONSUMER_GROUP_NAME, msg_id)
    print("---------------------------------------------------", flush=True)    


def start_monitoring():
    '''
    Initializes the monitoring process
    ''' 
    global last_check_time

    redis_utilities.set_stream_offset(redis_stream)

    while not is_monitoring_stopped:
        
        if redis_stream.get("stream_status") == "stopped":
            break

        result = redis_stream.xreadgroup(config.CONSUMER_GROUP_NAME,
                                        config.CONSUMER_NAME,
                                        {stream_id: '>' for stream_id in config.STREAM_IDS},
                                        block=config.READ_BLOCK_MS)

        if not result:
            print("No new message!")
            is_new_message = False

        else:
            #RESULT IS A LIST OF TUPLES: [(stream_id, [(id, {field: value}), ...]), ...]
            for stream_id, messages in result:
                for msg_id, received_data in messages:

                    try:
                        #CHECK IF THE MESSAGE NEEDS TO BE VALIDATED
                        validation_time = time.time() - last_check_time >= config.VALIDATION_CHECK_INTERVAL
                        
                        if (validation_time):
                            validate_schema(stream_id, msg_id, received_data)
                            last_check_time = time.time()
                        else:
                            handle_message(stream_id, msg_id, received_data)
                    except Exception as ex:
                        print(f"Failed to process {msg_id}: {ex}", flush=True)
                        time.sleep(0.1)


def check_stream_status():
    '''
    Keeps checking if the monitoring of the stream is disabled.
    Once the status is set to enabled, it initalizes the monitoring
    '''    
    global is_monitoring_stopped

    while True:

        if (redis_stream.get("stream_status") == "running"):
            
            is_monitoring_stopped = False
            print("Monitoring started!", flush=True)
            start_monitoring()
        else:
            is_monitoring_stopped = True
            print("Monitoring is stopped!", flush=True)

        time.sleep(5)

#CHECKING STATUS IMMEDIATELY WHEN THE CONSUMER STARTS UP
check_stream_status()