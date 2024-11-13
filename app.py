# app.py

from flask import Flask, render_template, request, jsonify
from data_loader import load_data, get_unique_values
from brand_sales import brand_sales_bp  # Import the Blueprint
import plotly.express as px
import plotly
import json
import pandas as pd

app = Flask(__name__)

# Step 2: Load and preprocess data using data_loader.py
df = load_data()

# Combine Vehicle Make and Model
df['Make and Model'] = df['Vehicle Make'] + ' ' + df['Vehicle Model']

# Step 3: Extract unique vehicle types and provinces/territories
vehicle_types, available_provinces, _ = get_unique_values(df)

# Extract unique Make and Model for vehicle models selection
vehicle_models = sorted(df['Make and Model'].unique())

# Register the Blueprint
app.register_blueprint(brand_sales_bp)

@app.route('/')
def index():
    # Load and preprocess data
    df = load_data()
    if df.empty:
        return "Data not loaded correctly."
    df['Month and Year'] = pd.to_datetime(df['Month and Year'], format='%b %Y')  # Adjust format as needed

    # Generate Total Sales Over Time graph
    sales_over_time = df.groupby('Month and Year')['Number of Cars'].sum().reset_index()
    fig = px.line(
        sales_over_time,
        x='Month and Year',
        y='Number of Cars',
        title='Total Sales Over Time',
        labels={'Number of Cars': 'Sales'},
        template='plotly_white'
    )
    fig.update_traces(line=dict(width=2))
    fig.update_layout(
        xaxis_title='Month and Year',
        yaxis_title='Number of Cars',
        title_x=0.5
    )

    # Convert the Plotly figure to HTML
    graph_html = fig.to_html(full_html=False)

    # -------------------------- Table Data Calculation -------------------------- #
    # Identify the latest month in the dataset
    latest_month = df['Month and Year'].max()

    # Determine the last 6 months
    all_months_sorted = df['Month and Year'].sort_values().drop_duplicates()
    last_6_months = all_months_sorted[all_months_sorted <= latest_month].iloc[-6:]
    last_6_months = last_6_months[::-1]  # Reverse to have latest first

    # Labels for the last 6 months
    last_6_months_labels = [month.strftime('%b %Y') for month in last_6_months]

    # Define date ranges
    ytd_start = pd.Timestamp(year=latest_month.year, month=1, day=1)
    one_year_ago = latest_month - pd.DateOffset(years=1) + pd.DateOffset(days=1)

    # Calculate Total Sales
    total_last_6_months = df[df['Month and Year'].isin(last_6_months)]['Number of Cars'].sum()
    ytd_sales = df[(df['Month and Year'] >= ytd_start) & (df['Month and Year'] <= latest_month)]['Number of Cars'].sum()
    one_year_sales = df[(df['Month and Year'] >= one_year_ago) & (df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

    # Canada sales per month for last 6 months
    canada_sales = df[df['Month and Year'].isin(last_6_months)].groupby('Month and Year')['Number of Cars'].sum().reindex(last_6_months).fillna(0)

    # Total Canada sales
    total_canada_last_6 = canada_sales.sum()
    canada_ytd = df[(df['Month and Year'] >= ytd_start) & (df['Month and Year'] <= latest_month)]['Number of Cars'].sum()
    canada_one_year = df[(df['Month and Year'] >= one_year_ago) & (df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

    # Prepare a list of provinces/territories sorted descending by latest month sales
    latest_month_sales_per_province = df[df['Month and Year'] == latest_month].groupby('Province/Territory')['Number of Cars'].sum()
    sorted_provinces = latest_month_sales_per_province.sort_values(ascending=False).index.tolist()

    # Initialize table data
    table_data = []

    # First row: Canada with Priority 0
    canada_row = {
        'Priority': 0,
        'Province': 'Canada',
        'Last 6 Months': [int(canada_sales[month]) for month in last_6_months],
        'Total Last 6 Months': int(total_canada_last_6),
        'YTD': int(canada_ytd),
        '1 Year': int(canada_one_year)
    }
    table_data.append(canada_row)

    # Next rows: per province/territory with Priority 1
    for province in sorted_provinces:
        province_df = df[df['Province/Territory'] == province]

        # Sales for last 6 months
        province_sales_last_6 = province_df[province_df['Month and Year'].isin(last_6_months)].groupby('Month and Year')['Number of Cars'].sum().reindex(last_6_months).fillna(0)

        # Total last 6 months
        total_province_last_6 = province_sales_last_6.sum()

        # YTD sales
        province_ytd = province_df[(province_df['Month and Year'] >= ytd_start) & (province_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

        # 1-year sales
        province_one_year = province_df[(province_df['Month and Year'] >= one_year_ago) & (province_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

        province_row = {
            'Priority': 1,
            'Province': province,
            'Last 6 Months': [int(sales) for sales in province_sales_last_6],
            'Total Last 6 Months': int(total_province_last_6),
            'YTD': int(province_ytd),
            '1 Year': int(province_one_year)
        }

        table_data.append(province_row)

    # -------------------------- Date Range Calculations for Tooltips -------------------------- #
    # Total Last 6 Months Range
    total_last_6_months_range = f"{last_6_months.iloc[-1].strftime('%b %Y')} - {last_6_months.iloc[0].strftime('%b %Y')}"

    # YTD Range
    ytd_range = f"{ytd_start.strftime('%b %Y')} - {latest_month.strftime('%b %Y')}"

    # 1 Year Range
    one_year_range = f"{(latest_month - pd.DateOffset(years=1)).strftime('%b %Y')} - {latest_month.strftime('%b %Y')}"

    # -------------------------- Pass All Necessary Data to Template -------------------------- #
    return render_template(
        'index.html',
        graph=graph_html,
        table_data=table_data,
        last_6_months_labels=last_6_months_labels,
        total_last_6_months_range=total_last_6_months_range,
        ytd_range=ytd_range,
        one_year_range=one_year_range
    )

if __name__ == '__main__':
    app.run(debug=True)