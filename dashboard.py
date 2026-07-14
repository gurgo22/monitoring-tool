import streamlit as st, redis, pandas as pd, time, config, datetime, redis_utilities, json
import services.database_service as database_service, plotly.express as px, services.data_cleaning_service as data_cleaning_service
from models.severity import Severity
#!!! A modul több részének fejlesztéséhez GenAI eszköz eszköz segítsége volt használva !!!

st.set_page_config(page_title="Stream Monitoring Dashboard", layout="wide")

st.title("Monitoring Tool")

control_panel_tab, visualization_tab, data_cleaning_tab = st.tabs(["Control Panel", "Data Visualization", "Data Cleaning"])

st.set_page_config(layout="wide")

db_connection = database_service.connect_to_db(is_local_connection = False)

def render_control_panel():
    '''
    Shows a control panel for interacting with the Redis stream
    '''
    st.header("Redis Stream Control")
    st.divider()

    redis_stream = redis_utilities.connect_to_redis()
    redis_is_connected = False
    current_state = "unknown"

    #CHECKING THE REDIS SERVICE STATUS
    if redis_stream is not None:
        try:
            redis_stream.ping()
            redis_is_connected = True
            
            status = redis_stream.get("stream_status")
            current_state = status if status else "stopped"
            
        except redis.exceptions.ConnectionError:
            st.error("Could not connect to Redis.")

    #COLUMNS FOR ALIGNMENT
    status_column, button_column = st.columns(2)
            
    with status_column:
        st.metric("Current Monitoring Status", current_state.upper())

    with button_column:

        if redis_is_connected:
        
            if current_state == "stopped":
        
                if st.button("▶ Start Monitoring", width='stretch', type="primary"):
        
                    redis_stream.set("stream_status", "running")
                    st.rerun()
            else:
                if st.button("⏸ Stop Monitoring", width='stretch', type="secondary"):
        
                    redis_stream.set("stream_status", "stopped")
                    st.rerun()
        else:
            st.button("Start Monitoring", width='stretch', disabled=True)

    #STREAM STATUS
    st.divider()
    st.subheader("Stream Information")
    
    if redis_is_connected:

        cols = st.columns(config.NUMBER_OF_STREAMS)
        
        for i, stream_id in enumerate(config.STREAM_IDS):
            
            length = redis_utilities.get_redis_length(redis_stream, stream_id)
            
            heartbeat = redis_utilities.get_stream_heartbeat(redis_stream, stream_id)
            
            with cols[i]:
                
                st.metric(
                    label=f"{stream_id}", 
                    value=length, 
                    delta=f"Last event happened: {heartbeat}",
                    delta_color="normal"
                )
                
    else:
        st.info("Redis is disconnected. Stream lengths unavailable.")

    #ADVANCED OPERATIONS
    if redis_is_connected:

        st.divider()
        with st.expander("Advanced Operations"):
            
            st.caption("Use these commands carefully, as they modify the stream permanently.")
            
            selected_stream = st.selectbox(
                "Select Stream for Operations:", 
                config.STREAM_IDS,
                key="advanced_ops_stream_select"
            )

            trim_column, delete_column = st.columns(2)
            
            with trim_column:

                st.markdown("**Trim Stream**")
                count_to_trim = st.number_input("Records to delete:", min_value=100, max_value=100000, value=1000, step=100)
                
                if st.button("Trim Records", width='stretch'):

                    redis_utilities.trim_stream(redis_stream, selected_stream, count_to_trim)
                    st.toast(f"Stream successfully trimmed by {count_to_trim} records.")
                    
            with delete_column:
                st.markdown("**Delete Records From Stream**")
                
                if st.button("Delete All Stream Data", width='stretch', type="primary"):

                    redis_utilities.empty_stream(redis_stream, selected_stream)
                    st.toast("Stream emptied.")
    else:
        st.info("Redis is disconnected. Advanced operations are unavailable.")

#!!! GenAI eszköz segítségével készült kód !!!
def create_incident_count_chart():
    '''
    Creates a pie chart that shows the distribution of the count of incidents among the streams
    
    Returns
    ----------
    fig: Figure
    '''
    incident_count_by_stream = []

    for stream_id in config.STREAM_IDS:
        count = len(database_service.get_incident(db_connection=db_connection,
                                                key=None, timestamp=None,
                                                stream_id=stream_id,
                                                severity=None))
        incident_count_by_stream.append({"Stream": stream_id, "Incidents": count})

    df = pd.DataFrame(incident_count_by_stream)

    if not df.empty and df["Incidents"].sum() > 0:

        fig = px.pie(
            df, 
            values='Incidents', 
            names='Stream', 
            title='Total Incident Count by Stream',
            hole=0.33,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        return fig
    else:
        return None

#!!! GenAI eszköz segítségével készült kód !!!
def create_stacked_severity_chart():
    '''
    Creates a stacked bar chart that shows the distribution of the count of incidents
    among the streams grouped by severity

    Returns
    ----------
    fig: Figure
    '''
    chart_data = []

    for stream_id in config.STREAM_IDS:

        for sev in Severity:

            incidents = database_service.get_incident(
                db_connection=db_connection,
                key=None,
                timestamp=None,
                stream_id=stream_id,
                severity=sev.value
            )
                
            count = len(incidents)

            chart_data.append({
                "Stream": stream_id,
                "Severity": sev.name,
                "Incident Count": count
            })

    df = pd.DataFrame(chart_data)

    if not df.empty and df["Incident Count"].sum() > 0:

        fig = px.bar(
            df, 
            x="Stream", 
            y="Incident Count", 
            color="Severity", 
            title="Incident Distribution by Severity",

            color_discrete_map={
                "LOW": "#00CC96", 
                "MEDIUM": "#FFA15A", 
                "HIGH": "#EF553B"
            },
            barmode="stack"
        )

        return fig
    return None


def fetch_stream_data():
    
    all_stream_dfs = []
        
    raw_data = database_service.get_incident(
        db_connection=db_connection,
        key=None,
        timestamp=None,
        stream_id=None,
        severity=None
    )
            
    if raw_data:
        cols = ['id', 'key', 'timestamp', 'stream_id', 'severity', 'details']
        df_stream = pd.DataFrame(raw_data, columns=cols)
        all_stream_dfs.append(df_stream)
                
    if not all_stream_dfs:
        return pd.DataFrame()
            
    #COMBINING ALL INDIVIDUAL STREAM DATAFRAMES INTO ONE
    df_combined = pd.concat(all_stream_dfs, ignore_index=True)
        
    #CONVERTING TIMESTAMP COLUMN TO PANDAS DATETIME OBJECT
    df_combined['timestamp'] = pd.to_datetime(df_combined['timestamp'])
        
    return df_combined

#!!! GenAI eszköz segítségével készült kód !!!
def plot_trend_chart(df, timeframe_label, freq_code):
    '''
    Creates a line chart that shows the count of incidents that happened in the selected timeframe
    in each stream aggregated by the selected amount of time
    '''
    #Group by exact time buckets and stream_id
    df_resampled = (
        df.groupby([
            pd.Grouper(key='timestamp', freq=freq_code), 
            'stream_id'
        ])
        .size()
        .reset_index(name='incident_count')
    )

    # Pivot to put timestamps on the index and streams as columns
    df_pivot = df_resampled.pivot(index='timestamp', columns='stream_id', values='incident_count')

    #Resample the pivot table to fill missing buckets with 0
    # .asfreq() enforces the frequency, and .fillna(0) drops the missing spots to zero
    df_pivot = df_pivot.resample(freq_code).asfreq().fillna(0)

    #Melt it back to the format Plotly expects
    df_filled = df_pivot.reset_index().melt(
        id_vars='timestamp', 
        var_name='stream_id', 
        value_name='incident_count'
    )

    fig = px.line(
        df_filled,
        x='timestamp',
        y='incident_count',
        color='stream_id',
        title=f"Incident Trend ({timeframe_label})",
        markers=True
    )
        
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Incident Count")
        
    st.plotly_chart(fig, width='stretch')

#!!! GenAI eszköz segítségével készült kód !!!
def plot_severity_trend_chart(df, timeframe_label, freq_code):
    '''
    Creates a line chart that shows the count of incidents that happened in the selected timeframe
    in each stream aggregated by the selected amount of time
    '''
    #Group by exact time buckets and severity
    df_resampled = (
        df.groupby([
            pd.Grouper(key='timestamp', freq=freq_code), 
            'severity'
        ])
        .size()
        .reset_index(name='incident_count')
    )

    #Pivot to put timestamps on the index and severities as columns
    df_pivot = df_resampled.pivot(index='timestamp', columns='severity', values='incident_count')

    #Resample the pivot table to fill missing time buckets with 0
    df_pivot = df_pivot.resample(freq_code).asfreq().fillna(0)

    #Melt it back to the "long" format Plotly expects
    df_filled = df_pivot.reset_index().melt(
        id_vars='timestamp', 
        var_name='severity', 
        value_name='incident_count'
    )

    fig = px.line(
        df_filled,
        x='timestamp',
        y='incident_count',
        color='severity',
        title=f"Incident Trend by Severity ({timeframe_label})",
        markers=True,

        color_discrete_map={
            "LOW": "#00CC96",
            "MEDIUM": "#FFA15A",
            "HIGH": "#EF553B"  
        }
    )
    
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Incident Count")
    
    st.plotly_chart(fig, width='stretch')

#!!! GenAI eszköz segítségével készült kód !!!
def render_key_incident_analysis(df_incidents):
    '''
    Creates a bar chart showing incident counts per key for the selected stream
    '''
    #Find all unique streams that exist in the current dataset
    available_streams = df_incidents['stream_id'].unique()

    if len(available_streams) == 0:
        st.info("No stream data available for Key Analysis.")
        return

    selected_stream = st.selectbox(
        "Select Stream to Analyze:", 
        options=available_streams,
        key="key_incident_stream_select" 
    )

    #Filter the dataframe for only the chosen stream
    df_filtered = df_incidents[df_incidents['stream_id'] == selected_stream].copy()

    #Count the appearances of each unique key
    df_key_counts = df_filtered['key'].value_counts().reset_index()
    df_key_counts.columns = ['key', 'incident_count']

    fig = px.bar(
        df_key_counts,
        x='key',
        y='incident_count',
        title="Incident Distribution by Key",
        labels={
            'key': 'Incident Key', 
            'incident_count': 'Total Incidents'
        },
        text_auto=True,
        color='incident_count',
        color_continuous_scale='Bluered'
    )

    # Clean up the layout
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        margin=dict(t=50, b=50)
    )

    st.plotly_chart(fig, width='stretch')


def render_incident_filters():
    '''
    Renders the filter UI and returns the selected parameters
    '''
    st.subheader("Filter for Incidents")
    streamid_column, severity_column, count_column = st.columns(3)
    
    with streamid_column:
        selected_stream = st.selectbox("Stream ID", ["ALL"] + config.STREAM_IDS)
    with severity_column:
        selected_severity = st.selectbox("Severity", ["ALL", "LOW", "MEDIUM", "HIGH"])
    with count_column:
        limit = st.number_input("Max Results", min_value=1, max_value=10000, value=100)

    db_stream = None if selected_stream == "ALL" else selected_stream
    db_severity = None if selected_severity == "ALL" else selected_severity

    return db_stream, db_severity, limit


def render_incident_table(db_stream, db_severity, limit):
    '''
    Gets the data about the filtered incidents, converts it into a dataframe
    and renders tha table containing the values
    '''
    incidents = database_service.get_incident(
        db_connection=db_connection,
        key=None,
        timestamp=None, 
        stream_id=db_stream,
        severity=db_severity
    )
    
    if not incidents:
        st.info("No incidents match these filters.")
        return None, None

    cols = ['id', 'key', 'timestamp', 'stream_id', 'severity', 'message']
    df = pd.DataFrame(incidents, columns=cols)
    df = df.sort_values(by="timestamp", ascending=False).head(limit)

    st.caption("Click the checkbox next to any row to focus on the details of an incident.")
    
    event = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    #RETURNS THE DATAFRAME AND THE INDEX OF THE SELECTED ROW
    if len(event.selection.rows) > 0:
        return df, event.selection.rows[0]
    
    return df, None


def render_incident_payload(df, selected_idx):
    '''
    Renders the detailed view for a selected incident

    Parameters
    ----------
    df: DataFrame
        Stream records from the selected time interval
    selected_idx: int
        Index of the selected row in the Dataframe
    '''
    st.divider()
    st.subheader("3. Raw Incident Payload")
    
    #EXTRACTING THE SELECTED ROWS DATA FROM THE DATAFRAME
    selected_row = df.iloc[selected_idx]

    st.write(f"**Incident ID:** `{selected_row['id']}` | **Time:** `{selected_row['timestamp']}`")
    
    #PARSE AND RENDER JSON OR SHOW RAW CONTENT
    try:
        parsed_message = json.loads(selected_row['message'])
        st.json(parsed_message)
    except json.JSONDecodeError:
        st.code(selected_row['message'], language="text")


def incident_details_view():

    st.header("Incident Details")
    st.divider()
    
    #Get the filter parameters from the user
    db_stream, db_severity, limit = render_incident_filters()

    #Fetch the data and render the interactive table
    df, selected_idx = render_incident_table(db_stream, db_severity, limit)

    #If the user clicked a row, render the deep dive
    if selected_idx is not None:
        render_incident_payload(df, selected_idx)

#!!! GenAI eszköz segítségével készült kód !!!
def plot_heatmap_chart(df, timeframe_label, freq_code):
    '''
    Creates a heatmap visualizing incident counts during a timeline
    '''
    #Group by exact time buckets and stream_id
    df_resampled = (
        df.groupby([
            pd.Grouper(key='timestamp', freq=freq_code), 
            'stream_id'
        ])
        .size()
        .reset_index(name='incident_count')
    )

    #Pivot: Put Streams on the Y-axis (index) and Time on the X-axis (columns)
    df_pivot = df_resampled.pivot(
        index='stream_id', 
        columns='timestamp', 
        values='incident_count'
    )

    #Fill the time gaps with 0
    #Transpose (.T) so time is on the index, resample to fill gaps, then transpose back
    if not df_pivot.empty:
        df_pivot = df_pivot.T.resample(freq_code).asfreq().fillna(0).T
    else:
        df_pivot = df_pivot.fillna(0)

    fig = px.imshow(
        df_pivot,
        labels=dict(x="Time", y="Stream ID", color="Incident Count"),
        x=df_pivot.columns,
        y=df_pivot.index,
        color_continuous_scale='Reds',
        aspect="auto",
        title=f"Stream Activity Heatmap ({timeframe_label})"
    )
        
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Monitored Streams")
        
    st.plotly_chart(fig, width='stretch')


def add_cleaned_df_to_session_state(dataset):
    '''
    Adds the processed dataset to the streamlit session storage
    '''
    df_cleaned = data_cleaning_service.process_flattened_data(dataset)

    st.session_state.cleaned_dataset = df_cleaned


def rendering_flattening_assistant(df_cleaned):
    '''
    Handles the UI for the nested JSON flattening tool
    '''
    st.header("Data Normalizer")

    # --- 3. UI Outputs ---
    st.dataframe(df_cleaned, width='stretch')

    csv = df_cleaned.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Cleaned CSV",
        data=csv,
        file_name="cleaned_stream_data.csv",
        mime="text/csv",
    )

#!!! GenAI eszköz segítségével készült kód !!!
def render_data_quality_report(df_cleaned):
    '''
    Handles the Streamlit UI rendering for the data quality report
    '''
    st.divider()
    st.subheader("Data Quality Report")
    
    # --- Fetch the pre-calculated data from the service layer ---
    stats_df, missing_df, dtypes_df = data_cleaning_service.analyze_data_quality(df_cleaned)
    
    # --- Render the UI ---
    summary_tab, missing_tab, types_tab = st.tabs(["Statistical Summary", "Missing Values", "Data Types"])
    
    with summary_tab:
        if stats_df is not None:
            st.dataframe(stats_df, width='stretch')
        else:
            st.info("No numerical columns found to analyze.")

    with missing_tab:
        st.caption("Tracks the number of Null/NaN values per column.")
        if missing_df is not None:
            st.dataframe(missing_df, width='stretch')
        else:
            st.success("No missing values detected in any column!")

    with types_tab:
        st.dataframe(dtypes_df, width='stretch')


def render_summary_charts():
    '''
    Renders the Pie and Stacked Bar charts
    '''
    # INCIDENT COUNT PIE
    incident_count_fig = create_incident_count_chart()
    if incident_count_fig:
        st.plotly_chart(incident_count_fig, width='stretch')
    else:
        st.info("No incidents found yet. The chart will appear once data is processed.")

    # SEVERITY DISTRIBUTION STACKED BAR
    stacked_fig = create_stacked_severity_chart()
    if stacked_fig:
        st.plotly_chart(stacked_fig, width='stretch')
    else:
        st.info("No incident data available to display.")

#!!! GenAI eszköz segítségével készült kód !!!
def initialize_timeframe_defaults():
    '''
    Initializes default dates for the UI components if they do not exist
    '''
    if "init_defaults" not in st.session_state:
        now = datetime.datetime.now()
        st.session_state.trend_start = now - datetime.timedelta(hours=0.5)
        st.session_state.heat_start = now - datetime.timedelta(days=1)
        st.session_state.default_end = now
        st.session_state.init_defaults = True

#!!! GenAI eszköz segítségével készült kód !!!
def render_trend_analysis(df_incidents):
    '''
    Renders the Trend Analysis UI, filters data, and draws the charts

    Parameters
    ----------
    df_incidents: DataFrame
        Incidents from the selected time interval 
    '''
    st.subheader("Incident Trend")
    
    trend_start_date_column, trend_start_time_column, trend_end_date_column, trend_end_time_column = st.columns(4)
    with trend_start_date_column:
        t_start_d = st.date_input("Trend Start Date", value=st.session_state.trend_start.date(), key="t_sd")
    with trend_start_time_column:
        t_start_t = st.time_input("Trend Start Time", value=st.session_state.trend_start.time(), key="t_st")
    with trend_end_date_column:
        t_end_d = st.date_input("Trend End Date", value=st.session_state.default_end.date(), key="t_ed")
    with trend_end_time_column:
        t_end_t = st.time_input("Trend End Time", value=st.session_state.default_end.time(), key="t_et")

    timeframe = st.radio(
        "Data point aggregation:",
        ["Per 5 Seconds", "Per Minute", "Per 5 Minute"],
        horizontal=True,
        key="trend_radio"
    )
    
    freq_map = {"Per 5 Seconds": "5s", "Per Minute": "1min", "Per 5 Minute": "5min"}
    t_start_dt = pd.to_datetime(f"{t_start_d} {t_start_t}")
    t_end_dt = pd.to_datetime(f"{t_end_d} {t_end_t}")

    # Data Filtering
    mask_trend = (df_incidents['timestamp'] >= t_start_dt) & (df_incidents['timestamp'] <= t_end_dt)
    df_trend_filtered = df_incidents.loc[mask_trend].copy()
    
    # Plotting
    if not df_trend_filtered.empty:
        selected_freq = freq_map[timeframe]
        plot_trend_chart(df_trend_filtered, timeframe, selected_freq)
        plot_severity_trend_chart(df_trend_filtered, timeframe, selected_freq)
    else:
        st.warning("No incidents found in this time range for the Trend Chart.")

#!!! GenAI eszköz segítségével készült kód !!!
def render_heatmap_analysis(df_incidents):
    '''
    Renders the Heatmap UI, filters data, and draws the chart

    Parameters
    ----------
    df_incidents: DataFrame
        Incidents from the selected time interval 
    '''
    st.subheader("Heatmap of Incidents")
    
    start_date_column, start_time_column, end_date_column, end_time_column = st.columns(4)
    with start_date_column:
        h_start_d = st.date_input("Heatmap Start Date", value=st.session_state.heat_start.date(), key="h_sd")
    with start_time_column:
        h_start_t = st.time_input("Heatmap Start Time", value=st.session_state.heat_start.time(), key="h_st")
    with end_date_column:
        h_end_d = st.date_input("Heatmap End Date", value=st.session_state.default_end.date(), key="h_ed")
    with end_time_column:
        h_end_t = st.time_input("Heatmap End Time", value=st.session_state.default_end.time(), key="h_et")

    h_timeframe = st.radio(
        "Data point aggregation:",
        ["Per 5 Seconds", "Per Minute", "Per 5 Minute"],
        horizontal=True,
        key="heat_radio"
    )
    
    freq_map = {"Per 5 Seconds": "5s", "Per Minute": "1min", "Per 5 Minute": "5min"}
    h_start_dt = pd.to_datetime(f"{h_start_d} {h_start_t}")
    h_end_dt = pd.to_datetime(f"{h_end_d} {h_end_t}")

    #FILTERING FOR THE SELECTED TIME INTERVAL
    mask_heat = (df_incidents['timestamp'] >= h_start_dt) & (df_incidents['timestamp'] <= h_end_dt)
    df_heat_filtered = df_incidents.loc[mask_heat].copy()

    if not df_heat_filtered.empty:
        h_selected_freq = freq_map[h_timeframe]
        plot_heatmap_chart(df_heat_filtered, h_timeframe, h_selected_freq)
    else:
        st.warning("No incidents found in this time range for the Heatmap.")


def render_fetch_cleaning_data_section(selected_stream):
    '''
    Renders and handles the Redis data fetching button
    
    Parameters
    ----------
    selected_stream: str
        Name of the selected stream 
    '''
    if st.button("Fetch Data for Cleaning"):

        with st.spinner("Fetching data from Redis..."):
            current_unix_timestamp = int(time.time() * 1000)
            
            latest_incident_time = database_service.get_latest_incident_timestamp(db_connection, selected_stream) - 1000
            
            #DATASET GETS STORED IN THE STREAMLIT SESSION
            st.session_state.cleaning_dataset = data_cleaning_service.get_data_from_interval(
                selected_stream, 
                current_unix_timestamp, 
                latest_incident_time
            )
            
            #ACTIVATE THE VIEW OF THE ANALYSIS AND CLEAR THE OLD ONE
            st.session_state.show_cleaning = True
            st.session_state.cleaned_dataset = None 


#!!! GenAI eszköz segítségével készült kód !!!
def render_cleaned_data_preview():
    '''
    Renders the cleaned dataframe and the download button
    '''
    df = st.session_state.cleaned_dataset
    
    st.dataframe(df, width='stretch')

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Cleaned CSV",
        data=csv,
        file_name="cleaned_stream_data.csv",
        mime="text/csv",
    )


def render_cleaning_analysis_view():

    st.subheader("Data Normalizer")
    
    add_cleaned_df_to_session_state(st.session_state.cleaning_dataset)
    
    if st.session_state.get("cleaned_dataset") is not None:

        render_cleaned_data_preview()
        
        render_data_quality_report(st.session_state.cleaned_dataset)

    #CLEAR BUTTON
    st.divider()
    if st.button("Clear Analysis", type="secondary"):
        st.session_state.show_cleaning = False
        st.session_state.cleaning_dataset = None 
        st.session_state.cleaned_dataset = None 
        st.rerun()


#WHEN THERE IS NO DATABASE CONNECTION
if db_connection is None:

    st.error("The Postgres Database is currently unreachable. Visualizations are disabled.")
    
    with control_panel_tab:

        render_control_panel()
        
    with visualization_tab:
        st.warning("Cannot load Live Insights without a database connection.")

    with data_cleaning_tab:

        st.warning("Cannot provide data cleaning advice without a database connection.")
else:

    with control_panel_tab:

        render_control_panel()

    with visualization_tab:
        st.header("Live Insights")
        
        render_summary_charts()

        df_incidents = fetch_stream_data()

        if not df_incidents.empty:

            initialize_timeframe_defaults()
            
            render_trend_analysis(df_incidents)
            st.divider()
            render_key_incident_analysis(df_incidents)
            st.divider()
            render_heatmap_analysis(df_incidents)
            
            incident_details_view()
        else:
            st.info("Waiting for data to arrive in the stream")

    with data_cleaning_tab:
        st.header("Data Cleaning Assistance")
        
        #REDIS CONNECTION CHECK
        redis_stream = redis_utilities.connect_to_redis()
        redis_is_ready = False
        
        if redis_stream is not None:
            try:
                redis_stream.ping()
                redis_is_ready = True
            except redis.exceptions.ConnectionError:
                redis_is_ready = False

        if not redis_is_ready:
            
            st.warning("Data Cleaning tools are currently disabled because Redis is unavailable.")
        
        else:
            selected_stream = st.selectbox("Select stream to get data cleaning advice on:", config.STREAM_IDS)

            if (redis_utilities.check_stream_exists(redis_stream, selected_stream)
                and redis_utilities.check_stream_empty(redis_stream, selected_stream)):
                
                render_fetch_cleaning_data_section(selected_stream)

                if (st.session_state.get("show_cleaning")
                    and st.session_state.get("cleaning_dataset") is not None):
                    
                    render_cleaning_analysis_view()
            else:
                st.info("The selected stream does not exist or it is empty")