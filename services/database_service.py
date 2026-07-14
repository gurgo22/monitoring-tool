import psycopg2, config
from psycopg2.extensions import connection
from models.incident import Incident
from models.base_schema import BaseSchema
'''
Database queries that are required for the monitoring process and data visualization
'''
def connect_to_db(is_local_connection: bool) -> connection:
    '''
    Establishes a connection to the PostgreSQL database
    
    Parameters
    ----------
    is_local_connection: bool
        If True then the connection is outside the docker network, if False then it is inside the docker network
    
    Returns
    ----------
    db_connection: psycopg2.extensions.connection or None
    '''
    try:
        db_connection = psycopg2.connect(
            host = config.DB_HOST if not is_local_connection else 'localhost',
            database = config.DB_NAME,
            user = config.DB_USER,
            password = config.DB_PASS,
            connect_timeout = 3
        )
    
        print("Connected to PostgreSQL!")
    
        return db_connection
    
    except psycopg2.OperationalError as e:
        print(f"Could not connect to the database! \n {e}")
        return None


def try_connect_to_db() -> connection:
    '''
    Attempts to connect to the database in a loop until successful, 
    then initializes the tables
    
    Returns
    ----------
    db_connection: psycopg2.extensions.connection
    '''
    is_connected = False

    while not is_connected:

        db_connection = connect_to_db(is_local_connection = False)
        
        if (db_connection is not None):
            create_incidents_table(db_connection)
            create_base_schema_table(db_connection)
            is_connected = True
            
            return db_connection


def check_table_exists(db_connection: connection, table_name: str) -> bool:
    '''
    Checks if a specific table exists in the database
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        table_name: str
            Name of the table the check is for
    
    Returns
    ----------
    exists: bool
    '''
    try:
        query = """
            SELECT *
            FROM pg_tables 
            WHERE tablename = lower(%s);
        """

        cursor = db_connection.cursor()
        params = (table_name, )
        cursor.execute(query, params)
        
        if (cursor.rowcount > 0):
            print(f"The {table_name} table already exist.")
            return True
        else:
            print(f"The {table_name} table does not exist yet.")
            return False
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem while checking if the table exists! {e}")
        return False


def create_incidents_table(db_connection : connection):
    '''
    Creates the 'incidents' table in the database if it does not already exist
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
    '''
    if (not check_table_exists(db_connection, 'incidents')):

        try:
            cursor = db_connection.cursor()
            cursor.execute("""
            CREATE TABLE incidents
            (
                ID SERIAL PRIMARY KEY,
                KEY TEXT NOT NULL,
                TIMESTAMP TIMESTAMP,
                STREAM_ID TEXT NOT NULL,
                SEVERITY TEXT,
                DETAILS TEXT
            );
            """)
            
            db_connection.commit()
            print("The incidents table was succesfully created!")
            
        except psycopg2.OperationalError as e:
            print(f"There was a problem during the creation of the incidents table! {e}")


def insert_incident(db_connection : connection, incident : Incident):
    '''
    Inserts a new incident record into the 'incidents' table
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        incident: Incident
            Incident object which gets inserted into the incidents table
    '''
    try:
        query = """
            INSERT INTO incidents (KEY, TIMESTAMP, STREAM_ID, SEVERITY, DETAILS)
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor = db_connection.cursor()
        params = (incident.key, incident.timestamp, incident.stream_id, incident.severity, incident.details)
        cursor.execute(query, params)

        db_connection.commit()
        print("The incident was succesfully added to the database!")
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the insertion of the incident into the database! {e}")


def get_incident(db_connection : connection, key: str, timestamp, stream_id: str, severity: str) -> list:
    '''
    Retrieves incident records from the database based on optional filtering criteria
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        key: str
            Key of the incident that the filtering is for
        timestamp: datetime
            Timestamp of the incident that the filtering is for
        stream_id: str
            Stream ID of the incident that the filtering is for
        severity: str
            Severity of the incident that the filtering is for
    
    Returns
    ----------
    result: list
    '''
    try:
        query = """
            SELECT * FROM incidents
            WHERE (timestamp = %s OR %s IS NULL)
              AND (key = %s OR %s IS NULL)
              AND (stream_id = %s OR %s IS NULL)
              AND (severity = %s OR %s IS NULL)
        """

        cursor = db_connection.cursor()
        params = (timestamp, timestamp, key, key, stream_id, stream_id, severity, severity)
        cursor.execute(query, params)
       
        print("The incident(s) were succesfully extracted from the database!")
        result = cursor.fetchall()
        return result
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the extraction of the incident(s) from the database! {e}")
        return None

def get_latest_incident_timestamp(db_connection : connection, stream_id: str) -> int:
    '''
    Retrieves the UNIX timestamp of the most recent incident for a given stream ID
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        stream_id: str
            Stream ID of the incident that the filtering is for

    Returns
    ----------
    unix_timestamp: int
    '''
    try:
        query = """
            SELECT timestamp
            FROM incidents
            WHERE stream_id = %s OR %s IS NULL
            ORDER BY timestamp DESC
            FETCH FIRST 1 ROWS ONLY
        """

        cursor = db_connection.cursor()
        params = (stream_id, stream_id)
        cursor.execute(query, params)
       
        print("The latest incident was succesfully extracted from the database!")
        result = cursor.fetchall()

        #CONVERTING REGULAR TIMESTAMP TO UNIX TIMESTAMP
        if result:
            dt_obj = result[0][0]
            unix_timestamp = int(dt_obj.timestamp() * 1000)
            
            return unix_timestamp
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the extraction of the latest incident from the database! {e}")
        return []


def create_base_schema_table(db_connection : connection):
    '''
    Creates the 'base schema' table in the database if it does not already exist
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
    '''
    if (not check_table_exists(db_connection, 'base schema')):

        try:
            cursor = db_connection.cursor()
            cursor.execute("""
                CREATE TABLE "base schema"
                (
                    TIMESTAMP TIMESTAMP,
                    STREAM_ID TEXT, 
                    SCHEMA TEXT
                );
            """)
            
            db_connection.commit()
            print("The base schema table was succesfully created!")
            
        except psycopg2.OperationalError as e:
            print(f"There was a problem during the creation of the base schema table! {e}")


def insert_base_schema(db_connection : connection, base_schema : BaseSchema):
    '''
    Inserts a new base schema record into the 'base schema' table
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        base_schema: BaseSchema
            BaseSchema object that contains the schema of the stream
    '''
    try:
        query = """
            INSERT INTO "base schema"
            VALUES (%s, %s, %s)
        """
        
        cursor = db_connection.cursor()
        params = (base_schema.timestamp, base_schema.stream_id, base_schema.schema)
        cursor.execute(query, params)

        db_connection.commit()
        print("The new base schema was succesfully added to the database!")
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the insertion of the new base schema into the database! {e}")


def does_stream_have_base_schema(db_connection : connection, stream_id: str) -> bool: 
    '''
    Checks if a specific stream ID currently has an associated base schema
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        stream_id: str
            Stream ID of the stream that the filtering is for
    
    Returns
    ----------
    has_base_schema: bool
    '''
    try:
        query = """
            SELECT *
            FROM "base schema"
            WHERE stream_id LIKE %s;
        """

        cursor = db_connection.cursor()
        params = (stream_id, )
        cursor.execute(query, params)

        if (cursor.rowcount > 0):
            return True
        else:
            print(f"Stream: {stream_id} has no base schema yet!")
            return False
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the insertion of the new base schema into the database! {e}")


def get_latest_schema(db_connection : connection, stream_id) -> str:
    '''
    Retrieves the current base schema for a specific stream ID
    
    Parameters
    ----------
        db_connection: connection
            Connection to the database
        stream_id: str
            Stream ID of the stream that the filtering is for
    
    Returns
    ----------
    schema: str
    '''
    try:
        query = """
            SELECT schema
            FROM "base schema"
            WHERE stream_id LIKE %s
            ORDER BY "timestamp" DESC
            FETCH FIRST 1 ROWS ONLY
        """

        cursor = db_connection.cursor()
        params = (stream_id, )
        cursor.execute(query, params)

        print("The latest schema was succesfully extracted from the database!")
        return cursor.fetchone()[0]
        
    except psycopg2.OperationalError as e:
        print(f"There was a problem during the extraction of the latest base schema from the database! {e}")
        return []
