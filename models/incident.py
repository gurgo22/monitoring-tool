class Incident:
    '''
    Class for storing data about an incident
    '''
    def __init__(self, key, timestamp, stream_id, severity, details):
        
        self._key = key
        self._timestamp = timestamp
        self._stream_id = stream_id
        self._severity = severity
        self._details = details

    @property
    def key(self):
        return self._key

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def stream_id(self):
        return self._stream_id

    @property
    def severity(self):
        return self._severity

    @property
    def details(self):
        return self._details
    
    def to_dict(self) -> dict:
        '''
        Converts an Incident object into a python dictionary
        '''

        if hasattr(self.timestamp, 'isoformat'):
            formatted_time = self.timestamp.isoformat()
        else:
            formatted_time = str(self.timestamp)

        return {
            "key": self.key,
            "timestamp": formatted_time,
            "stream_id": self.stream_id,
            "severity": self.severity,
            "details": self.details
        }
