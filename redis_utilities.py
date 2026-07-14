import redis, config, time
'''
Utilities file for the redis operations
'''
def connect_to_redis() -> redis.Redis:
    '''
    Creates a connection to redis
    
    Returns
    ----------
    redis_stream: Redis
    '''
    try:
        redis_stream = redis.Redis(host = config.REDIS_HOSTNAME,
                                port = config.REDIS_PORT,
                                decode_responses=True)
        
        return redis_stream
    except Exception as exc:
        print(f"There was an error during the establishment of the Redis protocol! {exc}")
        return None
      
def create_consumer_group(redis_stream : redis.Redis):
    '''
    Creates a consumer group for the consumer

    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    '''
    for stream_id in config.STREAM_IDS: 

        try:
            redis_stream.xgroup_create(stream_id, config.CONSUMER_GROUP_NAME, id=0, mkstream=True)
            print(f"Consumer group: {config.CONSUMER_GROUP_NAME} created for stream_id: {stream_id}!")

        except:
            #CONSUMER GROUP ALREADY EXISTS
            print(f"A consumer group for stream: {stream_id} with the same name as {config.CONSUMER_GROUP_NAME} already exists")

def set_stream_offset(redis_stream : redis.Redis):
    '''
    Sets the offset to the beginning of the log file for all streams

    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    '''
    for stream_id in config.STREAM_IDS:
        try:
            redis_stream.xgroup_setid(stream_id, config.CONSUMER_GROUP_NAME, '$')
        except Exception as exc:
            print(f"Error resetting offset for {stream_id}: {exc}")

def get_redis_length(redis_stream: redis.Redis, stream_id: str):
    '''
    Returns the number of records in a stream.
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    '''
    try:
        return redis_stream.xlen(stream_id)
    except Exception as exc:
        print(f"Error getting the length of the stream {stream_id}: {exc}")
    
def trim_stream(redis_stream: redis.Redis, stream_id: str, count_to_trim: int):
    '''
    Trims the stream in order to shrink its size.
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    count_to_keep: int
        Amount of records to trim from the stream
    '''
    try:
        redis_stream.xtrim(stream_id, maxlen = count_to_trim)
    except Exception as exc:
        print(f"Error while trimming {stream_id}: {exc}")

def empty_stream(redis_stream: redis.Redis, stream_id: str):
    '''
    Removes all of the records from a stream
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    '''
    try:
        redis_stream.xtrim(stream_id, maxlen=0, approximate=False)
    except Exception as exc:
        print(f"Error while emptying {stream_id}: {exc}")

def get_stream_heartbeat(redis_stream: redis.Redis, stream_id: str):
    '''
    Gets the time of the last record that arrived in the stream to calculate a heartbeat
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    '''
    try:

        latest_record = redis_stream.xrevrange(stream_id, count=1)
        
        if not latest_record:
            return "Never (Empty stream)"
        
        record_id = latest_record[0][0]
            
        #GETTING THE TIMESTAMP FROM THE RECORD
        timestamp_ms = int(record_id.split('-')[0])
        timestamp_sec = timestamp_ms / 1000.0
        
        elapsed_time = int(time.time() - timestamp_sec)
        
        if elapsed_time < 60:
            return f"{elapsed_time} seconds ago"
        elif elapsed_time < 3600:
            mins = elapsed_time // 60
            return f"{mins} minutes ago"
        else:
            hours = elapsed_time // 3600
            return f"{hours} hours ago"
            
    except Exception as exc:
        print(f"Error while calculating the heartbeat {stream_id}: {exc}")

def check_stream_exists(redis_stream: redis.Redis, stream_id) -> bool:
    '''
    Checks if a stream with the given stream ID exists
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    '''
    if redis_stream.exists(stream_id):

        print(f"Stream with id: {stream_id} does exist")
        return True
    print(f"Stream with id: {stream_id} does not exist")
    return False

def check_stream_empty(redis_stream: redis.Redis, stream_id) -> bool:
    '''
    Checks if the stream with the given stream ID is empty
    
    Parameters
    ----------
    redis_stream: Redis
        Connection to redis
    stream_id: str
        ID of the stream
    '''
    if redis_stream.xlen(stream_id) > 0:
        
        print(f"Stream: {stream_id} is not empty")
        return True
    print(f"Stream: {stream_id} is empty")
    return False