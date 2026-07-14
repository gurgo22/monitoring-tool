import os, json, redis, time, config
'''
Module for producing records from the generated dataset into the Redis stream
'''

with open("generated_file.json") as f:
    data = json.load(f)

stream_name = os.getenv("REDIS_STREAM", "default_stream")

redis_stream = redis.Redis(host = config.REDIS_HOSTNAME, port = config.REDIS_PORT, decode_responses=True)

pipe = redis_stream.pipeline()

count = 0

for record in data:
    #WRAPS THE RECORD INTO A JSON STRING
    wrapped_data = {"payload": json.dumps(record)}
    
    pipe.xadd(stream_name, wrapped_data, maxlen = config.MAX_STREAM_SIZE, approximate = True)
    count = count + 1
    print(f"{stream_name} Produced: {record}")
    time.sleep(config.PRODUCE_DELAY)

    if count % config.BATCH_SIZE == 0:
        pipe.execute()

#LOADING THE REMAINING DATA
if (count % config.BATCH_SIZE != 0):
    pipe.execute()