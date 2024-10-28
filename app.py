import streamlit as st
import pandas as pd
import pydeck as pdk
import seaborn as sns

# Import functions from the other two files
from generate_sql_query import generate_sql_query
from execute_sql_and_summarize import execute_sql_query, summarize_results

st.title('Real Estate Data Explorer')

# Explanation and example prompts
st.write("""
Enter a query about real estate properties in New York City. You can ask for properties based on different criteria such as price, location, or size. 
Here are some example prompts you can try:
- Show me the top 10 most expensive properties in Manhattan
- Find residential properties within 5 miles of Queens
- List all office spaces available in Brooklyn larger than 2000 sq ft
""")

# Global property type and color mapping using Seaborn for better colors
property_types = ['Residential', 'Commercial', 'Industrial', 'Office', 'Multi-Family Residential']
colors = sns.color_palette('RdBu', len(property_types)).as_hex()
property_type_colors = dict(zip(property_types, colors))

# Load the JSON files for business context and schema information
@st.cache_data
def load_json_files():
    try:
        with open('business_context.json', 'r') as f:
            business_context = f.read()
        with open('schema_information.json', 'r') as f:
            schema_information = f.read()
        with open('prompt_query_pairs.json', 'r') as f:
            prompt_query_pairs = f.read()
        return business_context, schema_information, prompt_query_pairs
    except Exception as e:
        st.error(f'Error reading JSON files: {e}')
        st.stop()

# Function to clean and format data for rendering
def clean_dataframe(df):
    # Replace NaN with 'N/A' for display purposes
    df = df.fillna('N/A')
    
    # Format price for better readability
    if 'price' in df.columns:
        df['price'] = df['price'].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
    
    return df

# Tooltip formatter function
def format_tooltip(data):
    tooltip_parts = []
    if data.get('address') != 'N/A':
        tooltip_parts.append(f"<b>Address:</b> {data.get('address')}<br/>")
    if data.get('price') != 'N/A':
        tooltip_parts.append(f"<b>Price:</b> {data.get('price')}<br/>")
    if data.get('bedrooms') != 'N/A':
        tooltip_parts.append(f"<b>Bedrooms:</b> {data.get('bedrooms')}<br/>")
    if data.get('bathrooms') != 'N/A':
        tooltip_parts.append(f"<b>Bathrooms:</b> {data.get('bathrooms')}<br/>")
    if data.get('square_feet') != 'N/A':
        tooltip_parts.append(f"<b>Square Feet:</b> {data.get('square_feet')}<br/>")
    if data.get('property_type') != 'N/A':
        tooltip_parts.append(f"<b>Property Type:</b> {data.get('property_type')}<br/>")
    return "".join(tooltip_parts)

# Function to create a horizontal legend for the property types
def create_legend():
    legend_html = "<div style='display: flex; justify-content: space-around; margin-bottom: 20px;'>"
    for property_type, color in property_type_colors.items():
        legend_html += (
            f"<div style='display: flex; align-items: center; margin-right: 20px;'>"
            f"<div style='width: 20px; height: 20px; background-color: {color}; "
            f"border-radius: 50%; margin-right: 10px;'></div>{property_type}</div>"
        )
    legend_html += "</div>"
    return legend_html

# Cache the SQL query generation
@st.cache_data
def get_sql_query(user_prompt, business_context, schema_information, prompt_query_pairs):
    return generate_sql_query(user_prompt, business_context, schema_information, prompt_query_pairs)

# Cache the SQL query execution
@st.cache_data
def get_results(sql_query):
    results = execute_sql_query(sql_query)
    return [dict(row) for row in results]

# Cache the summary generation
@st.cache_data
def get_summary(sql_query, rows):
    return summarize_results(sql_query, rows)

# Initialize session state variables
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ''
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ''
if 'rows' not in st.session_state:
    st.session_state.rows = []
if 'summary' not in st.session_state:
    st.session_state.summary = ''
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'selected_indices' not in st.session_state:
    st.session_state.selected_indices = []

# Prompt input
user_prompt = st.text_input('Enter your query prompt:', '', key='prompt_input')

if user_prompt:
    # Load the JSON files
    business_context, schema_information, prompt_query_pairs = load_json_files()
    
    if user_prompt != st.session_state.user_prompt:
        # New prompt entered, regenerate everything
        st.session_state.user_prompt = user_prompt
        
        # Stage 1: Generate SQL query
        st.info('Generating SQL query...')
        with st.spinner('Generating SQL query...'):
            try:
                sql_query = get_sql_query(user_prompt, business_context, schema_information, prompt_query_pairs)
                st.session_state.sql_query = sql_query
            except Exception as e:
                st.error(f'Error generating SQL query: {e}')
                st.stop()
        st.success('SQL query generated.')
        st.subheader('Generated SQL Query')
        st.code(st.session_state.sql_query, language='sql')
        
        # Stage 2: Execute SQL query
        st.info('Executing SQL query...')
        with st.spinner('Executing SQL query...'):
            try:
                rows = get_results(sql_query)
                st.session_state.rows = rows
            except Exception as e:
                st.error(f'Error executing SQL query: {e}')
                st.stop()
        st.success('Results received.')
        
        # Stage 3: Summarize results
        with st.spinner('Summarizing results...'):
            try:
                summary = get_summary(sql_query, rows)
                st.session_state.summary = summary
            except Exception as e:
                st.error(f'Error summarizing results: {e}')
                st.stop()
        
        # Stage 4: Prepare DataFrame
        if st.session_state.rows:
            df = pd.DataFrame(st.session_state.rows)
            # Data processing steps...
            # Ensure 'price' is numeric
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df.dropna(subset=['price', 'latitude', 'longitude'])
    
            # Normalize 'price' for visualization
            max_price = df['price'].max()
            df['elevation'] = df['price'] / max_price * 1000  # Adjust scaling as needed
    
            # Assign colors based on property type
            def assign_color(row):
                property_type = row.get('property_type', 'Unknown')
                base_color = property_type_colors.get(property_type, '#CCCCCC')  # Default to grey if not found
                red, green, blue = [int(base_color[i:i+2], 16) for i in (1, 3, 5)]
                transparency = 150  # Set transparency to make them more visually pleasing
                return [red, green, blue, transparency]
    
            df['color'] = df.apply(assign_color, axis=1)
    
            # Format price before displaying it
            df = clean_dataframe(df)
    
            # Convert data types to ensure they are serializable
            df['bedrooms'] = df['bedrooms'].astype(str)
            df['bathrooms'] = df['bathrooms'].astype(str)
            df['date_listed'] = df['date_listed'].astype(str)
            df['square_feet'] = df['square_feet'].astype(str)
    
            # Ensure 'color' is a list of integers
            df['color'] = df['color'].apply(lambda x: [int(i) for i in x])
    
            # Ensure critical numeric columns have no NaN values
            numeric_columns = ['latitude', 'longitude', 'elevation']
            df = df.dropna(subset=numeric_columns)
    
            df = df.astype({
                'latitude': float,
                'longitude': float,
                'elevation': float,
                'price': str,
                'bedrooms': str,
                'bathrooms': str,
                'square_feet': str,
                'property_type': str,
                'address': str,
                # Add other columns as needed
            })
            st.session_state.df = df
    else:
        # Use cached data
        sql_query = st.session_state.sql_query
        summary = st.session_state.summary
        df = st.session_state.df
else:
    st.stop()

# Display SQL query and summary
st.subheader('Summary')
summary_fixed = summary.replace('$', '\\$')
st.markdown(summary_fixed)

if not st.session_state.df.empty:
    df = st.session_state.df
    # Multi-select for filtering property types
    selected_property_types = st.multiselect(
        'Select Property Types to Display',
        options=property_types,
        default=property_types,
        key='property_types_select'
    )

    df_filtered = df[df['property_type'].isin(selected_property_types)]

    if df_filtered.empty:
        st.warning('No data available for the selected property types.')
    else:
        # Display legend
        st.markdown(create_legend(), unsafe_allow_html=True)

        # Calculate view state
        if len(df_filtered) > 1:
            lat_range = df_filtered['latitude'].max() - df_filtered['latitude'].min()
            lon_range = df_filtered['longitude'].max() - df_filtered['longitude'].min()
            if max(lat_range, lon_range) < 0.05:
                zoom = 13
            elif max(lat_range, lon_range) < 0.2:
                zoom = 11
            else:
                zoom = 9
        else:
            zoom = 12

        view_state = pdk.ViewState(
            latitude=df_filtered['latitude'].mean(),
            longitude=df_filtered['longitude'].mean(),
            zoom=zoom,
            pitch=50,
            bearing=0,
            controller=True
        )

        # Create the PyDeck layer
        layer = pdk.Layer(
            'ColumnLayer',
            data=df_filtered,
            get_position='[longitude, latitude]',
            get_elevation='elevation',
            elevation_scale=1,
            radius=100,
            get_fill_color='color',
            pickable=True,
            auto_highlight=True,
            id='property-layer'
        )

        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=view_state,
            layers=[layer],
            tooltip={
                "html": format_tooltip({
                    "address": "{address}",
                    "price": "{price}",
                    "bedrooms": "{bedrooms}",
                    "bathrooms": "{bathrooms}",
                    "square_feet": "{square_feet}",
                    "property_type": "{property_type}"
                })
            }
        )

        # Display the PyDeck chart with selection enabled
        event = st.pydeck_chart(
            deck,
            use_container_width=True,
            key="deck",
            on_select="rerun",
            selection_mode="single-object"
        )

        # Handle selection
        if event and hasattr(event, 'selection') and event.selection:
            selection_data = event.selection

            # Access indices
            indices = selection_data.indices.get('property-layer', [])
            if indices:
                selected_property = df_filtered.iloc[indices]
                # Clean up the selected property data to avoid NaN issues
                cleaned_property = clean_dataframe(selected_property)
                st.subheader('Selected Property Details')
                st.write(cleaned_property)
            else:
                st.info('No property selected.')
        else:
            st.info('Click on a property on the map to see details here.')
else:
    st.warning('No results returned from the query.')
