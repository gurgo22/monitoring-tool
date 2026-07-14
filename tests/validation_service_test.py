import services.validation_service as validation_service
from models.severity import Severity

def test_build_schema_valid_data():
    '''
    Test that build_schema correctly generates a schema for valid JSON data
    '''
    sample_data = {
        "name": "Some Person",
        "age": 100,
        "address": {
            "street": "123 Some St",
            "city": "Budapest"
        }
    }

    schema = validation_service.build_schema(sample_data)

    expected_schema = {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"}
            }
        }
    }
    assert schema == expected_schema, f"Expected {expected_schema}, but got {schema}"
    print("\n[SUCCESS] build_schema correctly generated the schema for valid JSON data.")

def test_build_schema_valid_data():
    '''
    Test that a valid dictionary correctly returns a properties schema
    '''
    data = {
        "device_id": "1",
        "time": 1700000000,
        "readings": {"temp": 25.5}
    }
    
    schema = validation_service.build_schema(data)
    
    assert "device_id" in schema
    assert schema["device_id"]["type"] == "string"
    assert schema["time"]["type"] == "integer"
    assert schema["readings"]["type"] == "object"
    assert schema["readings"]["properties"]["temp"]["type"] == "number"


def test_no_schema_change():
    '''
    Test comparing two identical schemas yields no changes
    '''
    old_schema = validation_service.build_schema({"id": 1, "status": "active"})
    new_schema = validation_service.build_schema({"id": 2, "status": "standby"}) 
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    assert len(changes) == 0

def test_disappeared_keys():
    '''
    Test that a missing key yields a HIGH severity alert
    '''
    old_schema = validation_service.build_schema({"id": 1, "status": "active", "region": "north"})
    new_schema = validation_service.build_schema({"id": 1, "status": "active"})
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    assert len(changes) == 1
    key, severity, details = changes[0]
    
    assert key == "region"
    assert severity == Severity.HIGH.value
    assert "Key disappeared: region" in details

def test_appeared_keys():
    '''
    Test that a new flat key yields a LOW severity alert
    '''
    old_schema = validation_service.build_schema({"id": 1})
    new_schema = validation_service.build_schema({"id": 1, "region": "north"})
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    assert len(changes) == 1
    key, severity, details = changes[0]
    
    assert key == "region"
    assert severity == Severity.LOW.value
    assert "New key appeared: region" in details
    assert "Type: string" in details

def test_type_change():
    '''
    Test that changing a data type yields a MEDIUM severity alert
    '''
    old_schema = validation_service.build_schema({"time": 1700000000}) 
    new_schema = validation_service.build_schema({"time": "1700000000"})
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    assert len(changes) == 1
    key, severity, details = changes[0]
    
    assert key == "time"
    assert severity == Severity.MEDIUM.value
    assert "integer -> string" in details

def test_nested_type_change():
    '''
    Test that type changes inside nested objects are detected recursively
    '''
    old_schema = validation_service.build_schema({"readings": {"temp": 25.5}}) 
    new_schema = validation_service.build_schema({"readings": {"temp": "25.5"}})
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    assert len(changes) == 1
    key, severity, details = changes[0]
    
    assert key == "readings.temp"
    assert severity == Severity.MEDIUM.value
    assert "number -> string" in details

def test_appeared_nested_object():
    '''
    Test that a completely new nested object recursively yields all its internal keys
    '''
    old_schema = validation_service.build_schema({"time": 1700000000})
    new_schema = validation_service.build_schema({
        "time": 1700000000,
        "metrics": {
            "environment": {
                "temp": 25.5
            }
        }
    })
    
    changes = list(validation_service.get_schema_changes(old_schema, new_schema))
    
    changed_keys = []
    
    for change in changes:
        changed_keys.append(change[0])
        assert change[1]  == Severity.LOW.value
    
    assert "metrics.environment.temp" in changed_keys
    assert "metrics.environment" in changed_keys
