from genson import SchemaBuilder
from models.severity import Severity
'''
Functionalities that are required to validate a record in the stream
'''
def build_schema(data) -> dict:
    '''
    Generates the schema of a JSON object and returns it as a dictionary
    
    Parameters
    ----------
        data: any object or scalar that can be serialized in JSON
    
    Returns
    ----------
    data_dict: dictionary
    '''
    try:
        builder = SchemaBuilder()
        builder.add_object(data)
        data_dict = builder.to_schema()['properties']
        
        return data_dict
    except:
        print("Failed to build the schema for the data!")
    
def get_all_new_keys(schema_dict: dict, path: str=""):
    '''
    Recursive generator function that gets every key inside a newly appeared object
    
    Parameters
    ----------
    schema_dict: dictionary
        Contains the record that is getting
    path: str
        Path to the key (important in case of nested JSON objects)
    '''
    #BASE CASE
    if (schema_dict.get('type') != 'object'):
        return

    properties = schema_dict.get('properties', {})

    for key, value in properties.items():

        full_key = f"{path}.{key}" if path else key

        #IF THE NEW KEY IS AN object TYPE, THEN FIND THE EXACT TYPE RECURSIVELY
        if (value['type'] == 'object'):

            yield from get_all_new_keys(value, path = full_key)

        print(f"New key appeared: {full_key} | Type: {value['type']}")
        yield (full_key, Severity.LOW.value, f"New key appeared: {full_key} | Type: {value['type']}")

def get_schema_changes(old_dict: dict, new_dict: dict, path: str=""):
    '''
    Recursive generator function that checks for keys that disappeared, appeared or changed data types
    
    Parameters
    ----------
    old_dict: dictionary
        Contains the current base schema
    new_dict: dictionary
        Contains the schema of the record that is validated
    path: str
        Path to the key (important in case of nested JSON objects)
    '''
    old_keys = set(old_dict.keys())
    new_keys = set(new_dict.keys())
    
    appeared_keys = new_keys.difference(old_keys)
    
    disappeared_keys = old_keys.difference(new_keys)

    #CHECKING IF ANY NEW KEYS APPEARED
    for key in appeared_keys:
        
        full_key = f"{path}.{key}" if path else key
        
        # If the newly added key is an object, log its internal properties too
        if new_dict[key]['type'] == 'object':
            yield from get_all_new_keys(new_dict[key], path=full_key)
        else:
            print(f"New key appeared: {full_key} | Type: {new_dict[key]['type']}")
            yield (full_key, Severity.LOW.value, f"New key appeared: {full_key} | Type: {new_dict[key]['type']}")

    #CHECKING IF ANY KEYS DISAPPEARED
    for key in disappeared_keys:

        full_key = f"{path}.{key}" if path else key
        print("Key disappeared:", key)
        yield (full_key, Severity.HIGH.value, f"Key disappeared: {full_key}")

    #CHECKING IF THE TYPE OF THE OTHER KEYS HAS CHANGED
    for key in (old_keys.intersection(new_keys)):
        #TODO null -> type or type -> null is not a change 
        full_key = f"{path}.{key}" if path else key

        old_val = old_dict[key]
        new_val = new_dict[key]
        
        #IF NOT A LEAF KEY, THEN INITIATE RECURSION
        if (old_val['type'] == 'object' and new_val['type'] == 'object'):
            
            yield from get_schema_changes(old_val['properties'], new_val['properties'], path=full_key)
        
        #IF LEAF KEY, CHECK TYPE CHANGE
        elif (old_val['type'] != new_val['type']):

            print(f"Key data type changed: {full_key} | Details: {old_val['type']} -> {new_val['type']}")
            yield (full_key, Severity.MEDIUM.value, f"Key data type changed: {full_key} | Details: {old_val['type']} -> {new_val['type']}")
            