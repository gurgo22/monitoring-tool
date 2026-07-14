import pytest
from models.incident import Incident
from models.severity import Severity

def test_incident_initialization():
    '''
    Test that an Incident object is initialized correctly with all attributes.
    '''
    data = {
        "key": "some_key",
        "timestamp": 1700000000,
        "stream_id": "redis_stream_n",
        "severity": Severity.HIGH,
        "details": "Key disappeared: some_key"
    }

    incident = Incident(**data)

    assert incident.key == data["key"]
    assert incident.timestamp == data["timestamp"]
    assert incident.stream_id == data["stream_id"]
    assert incident.severity == data["severity"]
    assert incident.details == data["details"]

    print("\n[SUCCESS] Initialization was successful")

def test_properties_read_only():
    '''
    Tests if attributes can be overwritten.
    '''
    incident = Incident("some_key",  1700000050, "redis_stream_1", Severity.MEDIUM, "Key disappeared: some_key")

    with pytest.raises(AttributeError):
        incident.key = "other_key"
    
    with pytest.raises(AttributeError):
        incident.severity = Severity.LOW

    print("[SUCCESS] All properties are protected from being overwritten")
