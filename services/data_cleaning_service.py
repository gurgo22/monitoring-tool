import config, json, pandas as pd, redis_utilities
'''
Module that contains methods that the data cleaning feature uses
'''
def get_data_from_interval(stream_id: str, current_time: int, last_change_time: int) -> list:
    '''
    Gets records that are between two timestamps from redis
    
    Parameters
    ----------
    stream_id: str
        Stream ID of the stream from which records are retrieved
    current_time: int
        Unix timestamp of the current time
    last_change_time: int
        Unix timestamp of the last schema change in the stream 
    
    Returns
    ----------
    payloads: list
        Content of the records from the selected time interval
    '''
    redis_stream = redis_utilities.connect_to_redis()
    
    interval_data = redis_stream.xrange(stream_id,
                                        min = f"{last_change_time}-0",
                                        max = f"{current_time}-0",
                                        count = config.DATA_CLEANING_MAX_DATESET_SIZE)
    print(interval_data)
    payloads = []

    for entry_id, fields in interval_data:

        raw_json_str = fields.get('payload')

        if raw_json_str:
            try:
                data = json.loads(raw_json_str)
                payloads.append(data)
                print(f"ID: {entry_id} | Data: {data}")
            except json.JSONDecodeError:
                print(f"Error: Could not parse JSON for entry {entry_id}")
    
    return payloads


def process_flattened_data(dataset) -> pd.DataFrame:
    '''
    Processes and cleans the dataset

    Parameters
    ----------
    dataset: list
        Stream records from the selected time interval
    
    Returns
    ----------
    df_cleaned: DataFrame
    '''
    if not dataset:
        return None

    df_cleaned = flatten_dataset(dataset)

    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    #FIXING PyArrow SERIALIZATION (IT DOES NOT HANDLE object TYPES)
    for col in df_cleaned.select_dtypes(include=['object']).columns:
        df_cleaned[col] = df_cleaned[col].astype(str)

    return df_cleaned

#!!! GenAI eszköz segítségével készült kód !!!
def rename_duplicates(df) -> pd.DataFrame:
    '''
    Renames the duplicate columns by adding an index that distinguishes them (duplicate based on column name) 
    
    Parameters
    ----------
    df: DataFrame
        Stream records from the selected time interval

    Returns
    ----------
    df: DataFrame
    '''
    cols = pd.Series(df.columns)
        
    for duplicate in cols[cols.duplicated()].unique():
        # Find all instances of the duplicate name and append an index
        dup_indices = cols[cols == duplicate].index
        
        for i, idx in enumerate(dup_indices):
        
            if i > 0: # Leave the first one as is, rename the rest
                cols[idx] = f"{duplicate}_{i}"
        
    df.columns = cols

    return df

#!!! GenAI eszköz segítségével készült kód !!!
def get_nested_columns(df) -> list:
    '''
    Returns the nested columns from a dataset

    Parameters
    ----------
    df: DataFrame
        Stream records from the selected time interval

    Returns
    ----------
    cols: list
    '''
    cols = []
        
    for col in df.columns:
        
        if df[col].empty: continue
        # Check the first non-null value to see if it's a list or dict
        first_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
        
        if isinstance(first_val, (dict, list)):
            cols.append((col, type(first_val)))
        
    return cols

def flatten_dataset(data) -> pd.DataFrame:
    '''
    Logic for flattening a dataset, by normalizing dictionaries and exploding lists
    
    Parameters
    ----------
    data: list
        Stream records from the selected time interval

    Returns
    ----------
    df: DataFrame
    '''
    df = pd.DataFrame(data)

    while True:
        
        df = rename_duplicates(df)
        
        nested_cols = get_nested_columns(df)
        
        if not nested_cols:
            break 
        
        for col_name, col_type in nested_cols:
        
            if col_type is dict:
                
                flattened = pd.json_normalize(df[col_name]).add_prefix(f"{col_name}_")
                flattened.index = df.index

                df = pd.concat([df.drop(columns=[col_name]), flattened], axis=1)

                df = rename_duplicates(df)
            
            elif col_type is list:
                df = df.explode(col_name)
                
    #STREAMLIT USES PYARROW AND CANNOT HANDLE object TYPES
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str)
                
    return df

def analyze_data_quality(df):
    '''
    Analyzes the DataFrame for statistical details about numeric values,
    missing values and data types

    Parameters
    ----------
    df: DataFrame
        Stream records from the selected time interval

    Returns
    ----------
    statistics_df, missing_df, data_types_df: Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    '''
    #CASTING ALL VALUES TO STRING AND THEN TRIES TO CONVERT IT INTO A NUMERIC TYPE
    numeric_df = df.astype(str).apply(pd.to_numeric, errors='coerce')
    
    #DROPPING ALL NaN VALUES SO ONLY THE NUMERIC VALUES REMAIN
    numeric_df = numeric_df.dropna(axis=1, how='all')
    
    statistics_df = numeric_df.describe() if not numeric_df.empty else None

    missing_counts = df.isnull().sum()  
    missing_counts = missing_counts[missing_counts > 0].sort_values(ascending=False)
    
    if not missing_counts.empty:

        missing_df = pd.DataFrame({
            "Missing Row Count": missing_counts,
            "Missing Percentage (%)": (missing_counts / len(df) * 100).round(2)
        })
    else:
        missing_df = None

    data_types_df = pd.DataFrame(df.dtypes, columns=["Data Type"]).astype(str)

    return statistics_df, missing_df, data_types_df