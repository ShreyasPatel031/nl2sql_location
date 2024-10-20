import streamlit as st
import requests
import json
import pandas as pd
import pydeck as pdk
import numpy as np
import seaborn as sns  # Use Seaborn for better color palettes

# Set your Mapbox API key
pdk.settings.mapbox_api_key = 'YOUR_MAPBOX_ACCESS_TOKEN'  # Replace with your Mapbox token

st.title('Real Estate Data Explorer')

# Explanation and example prompts
st.write("""
Enter a query about real estate properties in New York City. You can ask for properties based on different criteria such as price, location, or size. 
Here are some example prompts you can try:
- "Show me the top 10 most expensive properties in Manhattan."
- "Find residential properties in Queens larger than 2000 sq ft."
- "List all office spaces available in Brooklyn."
""")

# Global property type and color mapping using Seaborn for better colors
property_types = ['Residential', 'Commercial', 'Industrial', 'Office', 'Multi-Family Residential']
colors = sns.color_palette('RdBu', len(property_types)).as_hex()  # Using Seaborn 'RdBu' color palette
property_type_colors = dict(zip(property_types, colors))

# Cache the SQL query result
@st.cache_data
def fetch_results_from_api(user_prompt):
    cloud_function_url = 'https://us-central1-ai-demos-439118.cloudfunctions.net/gemini_location_query'
    payload = {'prompt': user_prompt}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(cloud_function_url, headers=headers, json=payload)
    return response

# Tooltip formatter function to avoid NaN issues and conditionally add data
def format_tooltip(data):
    tooltip_parts = []

    if pd.notna(data.get('address')):
        tooltip_parts.append(f"<b>Address:</b> {data.get('address')}<br/>")
    
    if pd.notna(data.get('price')):
        price = data.get('price')
        if isinstance(price, (int, float)):
            price = f"${price:,.0f}"
        tooltip_parts.append(f"<b>Price:</b> {price}<br/>")

    if pd.notna(data.get('bedrooms')):
        tooltip_parts.append(f"<b>Bedrooms:</b> {data.get('bedrooms')}<br/>")

    if pd.notna(data.get('bathrooms')):
        tooltip_parts.append(f"<b>Bathrooms:</b> {data.get('bathrooms')}<br/>")

    if pd.notna(data.get('square_feet')):
        tooltip_parts.append(f"<b>Square Feet:</b> {data.get('square_feet')}<br/>")

    if pd.notna(data.get('property_type')):
        tooltip_parts.append(f"<b>Property Type:</b> {data.get('property_type')}<br/>")

    return "".join(tooltip_parts)

# Function to create a horizontal legend for the property types
def create_legend():
    legend_html = "<div style='display: flex; justify-content: space-around; margin-bottom: 20px;'>"  # Add margin-bottom for spacing
    for property_type, color in property_type_colors.items():
        legend_html += (
            f"<div style='display: flex; align-items: center; margin-right: 20px;'>"
            f"<div style='width: 20px; height: 20px; background-color: {color}; "
            f"border-radius: 50%; margin-right: 10px;'></div>{property_type}</div>"
        )
    legend_html += "</div>"
    return legend_html

# Function to clean and format data for rendering
def clean_dataframe(df):
    # Replace NaN with 'N/A' for display purposes
    df = df.fillna('N/A')
    
    # Format price for better readability
    if 'price' in df.columns:
        df['price'] = df['price'].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
    
    return df

# Prompt input
user_prompt = st.text_input('Enter your query prompt:', '', key='prompt_input')

if user_prompt:
    with st.spinner('Generating SQL query and fetching results...'):
        response = fetch_results_from_api(user_prompt)

    if response.status_code == 200:
        data = response.json()
        sql_query = data.get('sql_query', '')
        summary = data.get('summary', '')
        results = data.get('results', [])

        st.subheader('Generated SQL Query')
        st.code(sql_query, language='sql')

        # Fix dollar sign issue by escaping the dollar sign
        st.subheader('Summary')
        summary_fixed = summary.replace('$', '\\$')
        st.markdown(summary_fixed)

        if results:
            # Convert results to a pandas DataFrame
            df = pd.DataFrame(results)

            # Ensure price is a numeric value for calculations
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df.dropna(subset=['price', 'latitude', 'longitude'])

            # Normalize price for better visualization (optional)
            max_price = df['price'].max()
            min_price = df['price'].min()  # Get min price for the color gradient
            df['elevation'] = df['price'] / max_price * 1000  # Adjust scaling factor as needed

            # Assign colors based on property type from the global property_type_colors
            def assign_color(row):
                property_type = row['property_type']
                base_color = property_type_colors.get(property_type, '#CCCCCC')  # Default to grey if not found
                red, green, blue = [int(base_color[i:i+2], 16) for i in (1, 3, 5)]
                transparency = 150  # Set transparency to make them more visually pleasing
                return [red, green, blue, transparency]

            df['color'] = df.apply(assign_color, axis=1)

            # Format price before displaying it
            df = clean_dataframe(df)

            # Multi-select for filtering property types on the main page
            selected_property_types = st.multiselect(
                'Select Property Types to Display',
                options=property_types,
                default=property_types
            )

            # Filter the dataframe based on selected property types
            df_filtered = df[df['property_type'].isin(selected_property_types)]

            if df_filtered.empty:
                st.warning('No data available for the selected property types.')
            else:
                # Display the horizontal circular legend above the map
                st.markdown(create_legend(), unsafe_allow_html=True)

                # Define the initial view state of the map (reduce map height)
                view_state = pdk.ViewState(
                    latitude=df_filtered['latitude'].mean(),
                    longitude=df_filtered['longitude'].mean(),
                    zoom=11,
                    pitch=50,
                    bearing=0,
                    controller=True  # Enable map controls
                )

                # Create a layer for the properties using ColumnLayer
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

                # Create the deck.gl map
                deck = pdk.Deck(
                    map_style='mapbox://styles/mapbox/light-v9',
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip={
                        "html": format_tooltip({"address": "{address}", "price": "{price}", "bedrooms": "{bedrooms}",
                                                "bathrooms": "{bathrooms}", "square_feet": "{square_feet}",
                                                "property_type": "{property_type}"})
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
    else:
        st.error(f"Error calling Cloud Function: {response.text}")
