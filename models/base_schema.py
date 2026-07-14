class BaseSchema:
    def __init__(self, timestamp, stream_id, schema):
        
        self._timestamp = timestamp
        self._stream_id = stream_id
        self._schema = schema

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def stream_id(self):
        return self._stream_id

    @property
    def schema(self):
        return self._schema
