# brand_sales.py

from flask import Blueprint, render_template, request
from data_loader import load_data
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset

# Initialize the Blueprint
brand_sales_bp = Blueprint('brand_sales_bp', __name__, template_folder='templates')

# Load and preprocess data
df = load_data()

# Get unique vehicle types and provinces/territories
vehicle_types = ['All'] + sorted(df['Vehicle Type'].dropna().unique())
provinces = ['All'] + sorted(df['Province/Territory'].dropna().unique())

@brand_sales_bp.route('/brand_sales', methods=['GET', 'POST'])
def brand_sales():
    # Determine the last available month in the data
    last_available_month = df['Month and Year'].max()

    # Get selected filters from form
    selected_vehicle_type = request.form.get('vehicle_type', 'All')
    selected_province = request.form.get('province', 'All')

    # Apply filters
    df_filtered = df.copy()
    if selected_vehicle_type != 'All':
        df_filtered = df_filtered[df_filtered['Vehicle Type'] == selected_vehicle_type]
    if selected_province != 'All':
        df_filtered = df_filtered[df_filtered['Province/Territory'] == selected_province]

    # Calculate the start dates
    start_date_6m = last_available_month - DateOffset(months=5)
    start_date_ytd = datetime(last_available_month.year, 1, 1)
    start_date_1y = last_available_month - DateOffset(years=1) + DateOffset(days=1)

    # Prepare the past 6 months list (latest to earliest)
    months_list = pd.date_range(end=last_available_month, periods=6, freq='MS')[::-1]

    # Filter data for the different periods
    df_6m = df_filtered[(df_filtered['Month and Year'] >= start_date_6m) & (df_filtered['Month and Year'] <= last_available_month)]
    df_ytd = df_filtered[(df_filtered['Month and Year'] >= start_date_ytd) & (df_filtered['Month and Year'] <= last_available_month)]
    df_1y = df_filtered[(df_filtered['Month and Year'] >= start_date_1y) & (df_filtered['Month and Year'] <= last_available_month)]

    # Prepare brand data
    # Sum sales per brand per month for the past 6 months
    brand_monthly_sales = df_6m.groupby(['Vehicle Make', df_6m['Month and Year'].dt.to_period('M')])['Number of Cars'].sum().unstack(fill_value=0)

    # Reorder columns to match months_list
    month_periods = [month.to_period('M') for month in months_list]
    brand_monthly_sales = brand_monthly_sales.reindex(columns=month_periods, fill_value=0)

    # Add total columns
    brand_monthly_sales['Past 6 Months Total'] = brand_monthly_sales.sum(axis=1)
    brand_monthly_sales['YTD Total'] = df_ytd.groupby('Vehicle Make')['Number of Cars'].sum()
    brand_monthly_sales['Past Year Total'] = df_1y.groupby('Vehicle Make')['Number of Cars'].sum()
    brand_monthly_sales = brand_monthly_sales.fillna(0).reset_index()

    # Sort by latest month's sales in descending order
    latest_month_period = last_available_month.to_period('M')
    brand_monthly_sales.sort_values(by=latest_month_period, ascending=False, inplace=True)

    # Prepare model data
    model_monthly_sales = df_6m.groupby(['Vehicle Make', 'Vehicle Model', df_6m['Month and Year'].dt.to_period('M')])['Number of Cars'].sum().unstack(fill_value=0)

    # Reorder columns to match months_list
    model_monthly_sales = model_monthly_sales.reindex(columns=month_periods, fill_value=0)

    # Add total columns
    model_monthly_sales['Past 6 Months Total'] = model_monthly_sales.sum(axis=1)
    model_monthly_sales['YTD Total'] = df_ytd.groupby(['Vehicle Make', 'Vehicle Model'])['Number of Cars'].sum()
    model_monthly_sales['Past Year Total'] = df_1y.groupby(['Vehicle Make', 'Vehicle Model'])['Number of Cars'].sum()
    model_monthly_sales = model_monthly_sales.fillna(0).reset_index()

    # Sort by latest month's sales in descending order
    latest_month_period = last_available_month.to_period('M')
    model_monthly_sales.sort_values(by=latest_month_period, ascending=False, inplace=True)

    # Convert months to string format for display
    months_str = [month.strftime('%b %Y') for month in months_list]

    # Prepare brand data records
    brand_data = brand_monthly_sales.to_dict('records')

    # Prepare model data records, organized by brand
    model_data = {}
    for _, row in model_monthly_sales.iterrows():
        brand = row['Vehicle Make']
        if brand not in model_data:
            model_data[brand] = []
        model_data[brand].append(row.to_dict())

    # Calculate date ranges for tooltips
    past_6_months_range = f"{months_str[-1]} to {months_str[0]}"
    ytd_range = f"{start_date_ytd.strftime('%b %Y')} to {last_available_month.strftime('%b %Y')}"
    past_year_range = f"{(last_available_month - DateOffset(years=1) + DateOffset(days=1)).strftime('%b %Y')} to {last_available_month.strftime('%b %Y')}"

    # **New Code Starts Here**
    # Identify top 5 brands based on total sales in the past month
    latest_month = df_filtered['Month and Year'].max()
    sales_past_month = df_filtered[df_filtered['Month and Year'] == latest_month]
    sales_by_brand_past_month = sales_past_month.groupby('Vehicle Make')['Number of Cars'].sum().sort_values(ascending=False)
    top_5_brands = sales_by_brand_past_month.head(5).index.tolist()
    # **New Code Ends Here**

    # Aggregate monthly sales data per brand for the line chart
    sales_by_brand = df_filtered.groupby(['Vehicle Make', 'Month and Year'])['Number of Cars'].sum().reset_index()
    
    # Pivot the data to have months as x-axis and brands as separate lines
    sales_pivot = sales_by_brand.pivot(index='Month and Year', columns='Vehicle Make', values='Number of Cars').fillna(0)
    
    # Convert the pivot table to JSON for Plotly
    sales_by_brand_json = sales_pivot.to_json(date_format='iso')

    return render_template('brand_sales/brand_sales.html',
                           brand_data=brand_data,
                           model_data=model_data,
                           months=months_str,
                           month_periods=month_periods,
                           vehicle_types=vehicle_types,
                           selected_vehicle_type=selected_vehicle_type,
                           provinces=provinces,
                           selected_province=selected_province,
                           past_6_months_range=past_6_months_range,
                           ytd_range=ytd_range,
                           past_year_range=past_year_range,
                           sales_by_brand_json=sales_by_brand_json,
                           top_5_brands=top_5_brands)  # **Added Parameter**