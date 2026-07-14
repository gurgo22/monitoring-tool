import uvicorn
from services import database_service
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API service is running."}

@app.get("/api/BaseSchema/{streamId}")
async def get_base_schema(stream_id : str) -> dict[str, str]:
    '''
    Endpoint for getting the base schema of a stream
    
    Parameters
    ----------
    stream_id: str
        ID of the stream
    '''
    try:
        db_connection = database_service.connect_to_db(is_local_connection = True)
        schema = database_service.get_latest_schema(db_connection, stream_id)
    
        return {"schema": schema}
    
    except Exception as exc:
        raise HTTPException(status_code = 500, detail = str(exc))
    

@app.get("/api/Incident")
async def get_incident(timestamp: str = None, key: str = None, stream_id: str = None,
                       severity: str = None) -> dict[str, list]:
    '''
    Endpoint for querying incidents
    
    Parameters
    ----------
    timestamp: str
        timestamp of the incident(s)
    key: str
        name of the key to which the incident is related to
    stream_id: str
        ID of the stream where the incident occured
    severity: str
        severity of the incident
    '''
    try:
        db_connection = database_service.connect_to_db(is_local_connection = True)
        incidents = database_service.get_incident(db_connection, key, timestamp, stream_id, severity)
    
        return {"incidents": incidents}
    
    except Exception as exc:
        raise HTTPException(status_code = 500, detail = str(exc))

if __name__ == "__main__":
    uvicorn.run(app, host = "127.0.0.1", port = 8000)

#COMMAND FOR RUNNING THE APP: uvicorn notification.api.monitoring_api:app --reload