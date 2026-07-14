import json, random, config

class DatasetGenerator:
    '''
    Class for generating a dataset that simulates schema drift events
    '''
    def __init__(self):
        self.statuses = ["active", "maintenance", "error", "standby"]
        self.regions = ["south", "east", "north", "west"]

    def generate_records(self, filename: str, count: int):
        '''
        Generates the records based on the randomized logic defined

        Parameters
        ----------
        filename: str
            Name of the file to generate
        count: int
            Number of records that the dataset consists of 
        '''
        generated_records = []
        start_timestamp = 1700000000

        for i in range(count):

            timestamp = start_timestamp + (i * 60)
            device_id = i + 1
            
            schema_state = random.randint(1, 10)

            if schema_state <= 4:
                #NORMAL BASE SCHEMA
                record = {
                    "device_id": str(device_id),
                    "time": timestamp,
                    "readings": {
                        "temp": round(random.uniform(0, 40.5), 2),
                        "humidity": random.randint(0, 100)
                    },
                    "status": random.choice(self.statuses)
                }

            elif schema_state > 4 and schema_state <= 6:
                #RENAMING AND FLATTENING OBJECTS
                record = {
                    "device_identifier": device_id, #RENAMED
                    "timestamp": timestamp,         #RENAMED
                    "temp_c": round(random.uniform(15.0, 35.0), 2), #FLATTENED OBJECT
                    "hum_pct": random.randint(30, 80),              #FLATTENED OBJECT
                    "region": random.choice(self.regions)           #NEW KEY
                }

            elif schema_state > 6 and schema_state <= 8:
                #TYPE CHANGE
                record = {
                    "device_id": str(device_id),
                    "time": str(timestamp), #NUMERIC TIMESTAMP -> TEXT
                    "readings": {
                        "temp": str(round(random.uniform(0, 40.5), 2)), #FLOATING NUMBER -> TEXT
                        "humidity": random.randint(0, 100)
                    },
                    "status": None #INSERTING NULL VALUE
                }

            else:
                #NESTED KEY
                record = {
                    "device": {"id": device_id, "group": "legacy"},     #NESTED KEY
                    "time": timestamp,
                    "metrics": {
                        "environment": {    #NESTED KEY
                            "t": round(random.uniform(0, 40.5), 2),
                            "h": random.randint(0, 100)
                        }
                    },
                    "alerts": [random.choice(["low_bat", "high_temp"])] if random.random() > 0.8 else []
                }

            generated_records.append(record)

        with open(filename, 'w') as file:
            json.dump(generated_records, file, indent = 2)
        
        print(f"Generated {count} generated_records in {filename}")

if __name__ == "__main__":
    generator = DatasetGenerator()
    generator.generate_records(config.FILE1, config.DATASET_SIZE)
    generator.generate_records(config.FILE2, config.DATASET_SIZE)