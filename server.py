import pandas as pd
from flask import Flask, render_template, request, jsonify
import plotly.express as px
from datetime import datetime
from pandas.tseries.offsets import MonthEnd

app = Flask(__name__)

# Load and preprocess data
df = pd.read_csv('car_summary.csv')
df['Month and Year'] = pd.to_datetime(df['Month and Year'], format='%B %Y')
df.sort_values('Month and Year', inplace=True)

# Combine Vehicle Make and Model
df['Make and Model'] = df['Vehicle Make'] + ' ' + df['Vehicle Model']

# Vehicle types for selection
vehicle_types = df['Battery-Electric Vehicle (BEV), Plug-in Hybrid Electric Vehicle (PHEV) or Fuel Cell Electric Vehicle (FCEV)'].unique().tolist()
vehicle_types.insert(0, 'All')

# Available models for selection
vehicle_models = sorted(df['Make and Model'].unique())

# Available provinces/territories for selection
available_provinces = df['Recipient Province/Territory'].unique().tolist()
available_provinces.insert(0, 'All')

@app.route('/', methods=['GET'])
def index():
    selected_vehicle_type = 'All'
    selected_province = 'All'

    # Default selected models: top 5 from latest month and selected vehicle type
    latest_month = df['Month and Year'].max()
    if selected_vehicle_type == 'All':
        latest_data = df[df['Month and Year'] == latest_month]
    else:
        latest_data = df[(df['Month and Year'] == latest_month) &
                         (df['Battery-Electric Vehicle (BEV), Plug-in Hybrid Electric Vehicle (PHEV) or Fuel Cell Electric Vehicle (FCEV)'] == selected_vehicle_type)]

    default_models = latest_data.groupby('Make and Model')['Number of Cars'].sum().nlargest(5).index.tolist()

    return render_template('index.html',
                           vehicle_types=vehicle_types,
                           selected_vehicle_type=selected_vehicle_type,
                           vehicle_models=vehicle_models,
                           selected_models=default_models,
                           available_provinces=available_provinces,
                           selected_province=selected_province)

@app.route('/update_graphs', methods=['POST'])
def update_graphs():
    selected_vehicle_type = request.json.get('vehicle_type', 'All')
    selected_models = request.json.get('vehicle_models', [])
    selected_province = request.json.get('province', 'All')

    # Filter data based on vehicle type
    if selected_vehicle_type == 'All':
        df_filtered = df.copy()
    else:
        df_filtered = df[df['Battery-Electric Vehicle (BEV), Plug-in Hybrid Electric Vehicle (PHEV) or Fuel Cell Electric Vehicle (FCEV)'] == selected_vehicle_type]

    # Filter data based on selected province
    if selected_province != 'All':
        df_filtered = df_filtered[df_filtered['Recipient Province/Territory'] == selected_province]

    # Apply date filter for past year
    one_year_ago = df['Month and Year'].max() - pd.DateOffset(years=1)
    df_filtered_year = df_filtered[df_filtered['Month and Year'] >= one_year_ago]

    # Graph 1: Total sales by month
    sales_by_month = df_filtered.groupby(df_filtered['Month and Year'].dt.to_period('M'))['Number of Cars'].sum().reset_index()
    sales_by_month['Month and Year'] = sales_by_month['Month and Year'].dt.to_timestamp()
    fig1 = px.line(sales_by_month, x='Month and Year', y='Number of Cars', title='Total Sales by Month', height=600,
                   template='simple_white', markers=True)
    fig1.update_traces(line=dict(width=4))
    fig1.update_layout(xaxis_title='', yaxis_title='Number of Cars')
    fig1.update_xaxes(range=[one_year_ago, df['Month and Year'].max()], rangeslider_visible=True)
    graph1 = fig1.to_html(full_html=False)

    # Graph 2: Top selling cars in last three months, ordered latest first
    unique_months = df_filtered['Month and Year'].drop_duplicates().sort_values(ascending=False)
    last_three_months = unique_months[:3]

    graphs2 = []
    for month in last_three_months:
        month_data = df_filtered[df_filtered['Month and Year'] == month]
        top_cars = month_data.groupby('Make and Model')['Number of Cars'].sum().nlargest(10).reset_index()
        fig = px.bar(top_cars, x='Make and Model', y='Number of Cars', title=f'Top Selling Cars in {month.strftime("%B %Y")}',
                     height=600, template='simple_white')
        fig.update_traces(marker_color='indianred')
        fig.update_layout(xaxis_tickangle=-45, xaxis_title='', yaxis_title='Number of Cars')
        graph = fig.to_html(full_html=False)
        graphs2.append({'month': month.strftime("%B %Y"), 'graph': graph})

    # If no models selected, default to top 5 models from latest month
    if not selected_models:
        latest_month = df_filtered['Month and Year'].max()
        latest_data = df_filtered[df_filtered['Month and Year'] == latest_month]
        selected_models = latest_data.groupby('Make and Model')['Number of Cars'].sum().nlargest(5).index.tolist()

    # Graph 3: Sales of selected cars by month
    specific_cars_data = df_filtered[df_filtered['Make and Model'].isin(selected_models)]
    specific_cars_sales = specific_cars_data.groupby(['Month and Year', 'Make and Model'])['Number of Cars'].sum().reset_index()
    fig3 = px.line(specific_cars_sales, x='Month and Year', y='Number of Cars', color='Make and Model',
                   title='Sales of Selected Cars by Month', height=600, template='simple_white', markers=True)
    fig3.update_traces(line=dict(width=4))
    fig3.update_layout(xaxis_title='', yaxis_title='Number of Cars')
    fig3.update_xaxes(range=[one_year_ago, df['Month and Year'].max()], rangeslider_visible=True)
    graph3 = fig3.to_html(full_html=False)

    # Graph 4: Sales by province over time (No filters applied)
    sales_by_province = df.groupby(['Month and Year', 'Recipient Province/Territory'])['Number of Cars'].sum().reset_index()
    fig4 = px.line(sales_by_province, x='Month and Year', y='Number of Cars', color='Recipient Province/Territory',
                   title='Sales by Province Over Time', height=600, template='simple_white', markers=True)
    fig4.update_traces(line=dict(width=3))
    fig4.update_layout(xaxis_title='', yaxis_title='Number of Cars')
    fig4.update_xaxes(range=[one_year_ago, df['Month and Year'].max()], rangeslider_visible=True)
    graph4 = fig4.to_html(full_html=False)

    return jsonify({
        'graph1': graph1,
        'graphs2': graphs2,
        'graph3': graph3,
        'graph4': graph4
    })

# server.py

@app.route('/brand_sales', methods=['GET', 'POST'])
def brand_sales():
    # Determine the last available month in the data
    last_available_month = df['Month and Year'].max()
    
    if request.method == 'POST':
        # Retrieve selected dates from the form
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        try:
            # Convert to datetime objects; assume 'YYYY-MM' format
            start_date = pd.to_datetime(start_date_str)
            end_date = pd.to_datetime(end_date_str) + MonthEnd(0)  # Set to end of the month
        except Exception as e:
            # Handle parsing errors
            print(f"Date parsing error: {e}")
            # Fallback to default YTD
            start_date = pd.to_datetime(f"{last_available_month.year}-01")
            end_date = last_available_month
    else:
        # Set default to YTD
        start_date = pd.to_datetime(f"{last_available_month.year}-01")
        end_date = last_available_month
    
    # Filter data based on date range
    df_filtered = df[(df['Month and Year'] >= start_date) & (df['Month and Year'] <= end_date)]
    
    # Total sales per brand
    df_brand_sales = df_filtered.groupby('Vehicle Make')['Number of Cars'].sum().reset_index()
    
    # Sales per model per brand
    df_model_sales = df_filtered.groupby(['Vehicle Make', 'Vehicle Model'])['Number of Cars'].sum().reset_index()
    
    # Prepare data for rendering
    brand_sales_data = df_brand_sales.to_dict('records')
    model_sales_data = {}
    for brand in df_brand_sales['Vehicle Make']:
        models = df_model_sales[df_model_sales['Vehicle Make'] == brand][['Vehicle Model', 'Number of Cars']]
        model_sales_data[brand] = models.to_dict('records')
    
    # Format dates as 'YYYY-MM' for 'month' input fields
    start_date_formatted = start_date.strftime('%Y-%m')
    end_date_formatted = end_date.strftime('%Y-%m')
    
    return render_template('brand_sales.html',
                           brand_sales=brand_sales_data,
                           model_sales=model_sales_data,
                           start_date=start_date_formatted,
                           end_date=end_date_formatted,
                           last_available_month=last_available_month.strftime('%Y-%m'))

if __name__ == '__main__':
    app.run(debug=True)