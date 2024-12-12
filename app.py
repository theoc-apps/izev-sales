# app.py

from flask import Flask, render_template, request, jsonify
from data_loader import load_data, get_unique_values
from brand_sales import brand_sales_bp  # Import the Blueprint
import plotly.express as px
import plotly
import json
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Step 2: Load and preprocess data using data_loader.py
df = load_data()

# Combine Vehicle Make and Model
df['Make and Model'] = df['Vehicle Make'] + ' ' + df['Vehicle Model']
df['Month and Year'] = pd.to_datetime(df['Month and Year'], format='%b %Y')  # Adjust format as needed

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
    fig.update_traces(hovertemplate='%{x|%b %Y}<br>Sales: %{y}')

    # Convert the Plotly figure to HTML
    graph_html = fig.to_html(full_html=False, config={'displayModeBar': False, 'responsive': True})

    # Best Selling Cars Bar Chart
    last_available_month = df['Month and Year'].max()
    latest_month_data = df[df['Month and Year'] == last_available_month]
    best_selling_cars = (
        latest_month_data.groupby(['Vehicle Make', 'Vehicle Model'])['Number of Cars']
        .sum()
        .nlargest(10)
        .reset_index()
    )
    # Combine Vehicle Make and Model for display
    best_selling_cars['Make and Model'] = best_selling_cars['Vehicle Make'] + ' ' + best_selling_cars['Vehicle Model']
    # Extract the actual month name
    latest_month_str = last_available_month.strftime('%B %Y')
    bar_fig = px.bar(
        best_selling_cars,
        x='Make and Model',
        y='Number of Cars',
        title=f'Best Selling Cars in {latest_month_str}',
        labels={'Number of Cars': 'Sales'},
        template='plotly_white'
    )
    bar_fig.update_layout(
        xaxis_title='Car Model',
        yaxis_title='Number of Cars',
        title_x=0.5
    )
    bar_graph_html = bar_fig.to_html(full_html=False, config={'displayModeBar': False, 'responsive': True})

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
        best_selling_cars_graph=bar_graph_html,
        table_data=table_data,
        last_6_months_labels=last_6_months_labels,
        total_last_6_months_range=total_last_6_months_range,
        ytd_range=ytd_range,
        one_year_range=one_year_range,
        vehicle_types=vehicle_types 
    )

@app.route('/update_graph', methods=['POST'])
def update_graph():
    data = request.get_json()
    selected_vehicle_type = data.get('vehicle_type')

    # Filter data based on selected vehicle type
    filtered_df = df
    title = 'Total Sales Over Time'
    if selected_vehicle_type != 'All':
        filtered_df = df[df['Vehicle Type'] == selected_vehicle_type]
        title = f'Total Sales Over Time for {selected_vehicle_type}'

    # Generate updated graph
    sales_over_time = filtered_df.groupby('Month and Year')['Number of Cars'].sum().reset_index()
    fig = px.line(
        sales_over_time,
        x='Month and Year',
        y='Number of Cars',
        title=f'{title}',
        labels={'Number of Cars': 'Sales'},
        template='plotly_white'
    )
    fig.update_traces(line=dict(width=2))
    fig.update_layout(
        xaxis_title='Month and Year',
        yaxis_title='Number of Cars',
        title_x=0.5
    )
    fig.update_traces(hovertemplate='%{x|%b %Y}<br>Sales: %{y}')

    # Convert the Plotly figure to HTML
    graph_html = fig.to_html(full_html=False, config={'displayModeBar': False, 'responsive': True})

    # Best Selling Cars Bar Chart
    latest_month = filtered_df['Month and Year'].max()
    latest_month_data = filtered_df[filtered_df['Month and Year'] == latest_month]
    best_selling_cars = (
        latest_month_data.groupby(['Vehicle Make', 'Vehicle Model'])['Number of Cars']
        .sum()
        .nlargest(10)
        .reset_index()
    )

    if best_selling_cars.empty:
        bar_graph_html = '<p>No best selling cars data available for the latest month.</p>'
    else:
        # Combine Vehicle Make and Model for display
        best_selling_cars['Make and Model'] = best_selling_cars['Vehicle Make'] + ' ' + best_selling_cars['Vehicle Model']
        # Extract the actual month name
        latest_month_str = latest_month.strftime('%B %Y')
        bar_fig = px.bar(
            best_selling_cars,
            x='Make and Model',
            y='Number of Cars',
            title=f'Best Selling Cars in {latest_month_str}',
            labels={'Number of Cars': 'Sales'},
            template='plotly_white'
        )
        bar_fig.update_layout(
            xaxis_title='Car Model',
            yaxis_title='Number of Cars',
            title_x=0.5
        )
        bar_graph_html = bar_fig.to_html(full_html=False, config={'displayModeBar': False, 'responsive': True})

    # Update table data
    latest_month = filtered_df['Month and Year'].max()
    last_6_months = filtered_df['Month and Year'].sort_values().drop_duplicates().iloc[-6:]
    last_6_months = last_6_months[::-1]

    last_6_months_labels = [month.strftime('%b %Y') for month in last_6_months]

    ytd_start = pd.Timestamp(year=latest_month.year, month=1, day=1)
    one_year_ago = latest_month - pd.DateOffset(years=1) + pd.DateOffset(days=1)

    total_last_6_months = filtered_df[filtered_df['Month and Year'].isin(last_6_months)]['Number of Cars'].sum()
    ytd_sales = filtered_df[(filtered_df['Month and Year'] >= ytd_start) & (filtered_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()
    one_year_sales = filtered_df[(filtered_df['Month and Year'] >= one_year_ago) & (filtered_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

    canada_sales = filtered_df[filtered_df['Month and Year'].isin(last_6_months)].groupby('Month and Year')['Number of Cars'].sum().reindex(last_6_months).fillna(0)
    total_canada_last_6 = canada_sales.sum()
    canada_ytd = filtered_df[(filtered_df['Month and Year'] >= ytd_start) & (filtered_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()
    canada_one_year = filtered_df[(filtered_df['Month and Year'] >= one_year_ago) & (filtered_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()

    latest_month_sales_per_province = filtered_df[filtered_df['Month and Year'] == latest_month].groupby('Province/Territory')['Number of Cars'].sum()
    sorted_provinces = latest_month_sales_per_province.sort_values(ascending=False).index.tolist()

    table_data = []

    canada_row = {
        'Priority': 0,
        'Province': 'Canada',
        'Last 6 Months': [int(canada_sales[month]) for month in last_6_months],
        'Total Last 6 Months': int(total_canada_last_6),
        'YTD': int(canada_ytd),
        '1 Year': int(canada_one_year)
    }
    table_data.append(canada_row)

    for province in sorted_provinces:
        province_df = filtered_df[filtered_df['Province/Territory'] == province]
        province_sales_last_6 = province_df[province_df['Month and Year'].isin(last_6_months)].groupby('Month and Year')['Number of Cars'].sum().reindex(last_6_months).fillna(0)
        total_province_last_6 = province_sales_last_6.sum()
        province_ytd = province_df[(province_df['Month and Year'] >= ytd_start) & (province_df['Month and Year'] <= latest_month)]['Number of Cars'].sum()
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

    return jsonify({
        'graph_html': graph_html,
        'best_selling_cars_graph': bar_graph_html,
        'table_data': table_data,
        'last_6_months_labels': last_6_months_labels,
        'total_last_6_months_range': f"{last_6_months.iloc[-1].strftime('%b %Y')} - {last_6_months.iloc[0].strftime('%b %Y')}",
        'ytd_range': f"{ytd_start.strftime('%b %Y')} - {latest_month.strftime('%b %Y')}",
        'one_year_range': f"{(latest_month - pd.DateOffset(years=1)).strftime('%b %Y')} - {latest_month.strftime('%b %Y')}"
    })

@app.route('/get_province_sales_data', methods=['POST'])
def get_province_sales_data():
    data = request.get_json()
    selected_vehicle_type = data.get('vehicle_type', 'All')

    # Set date range to include all data
    end_date = df['Month and Year'].max()
    start_date = end_date - pd.DateOffset(years=10)  # Adjust as needed for historical data span

    # Filter data based on vehicle type only
    filtered_df = df.copy()
    if selected_vehicle_type != 'All':
        filtered_df = filtered_df[filtered_df['Vehicle Type'] == selected_vehicle_type]
    
    # Group data by 'Month and Year' and 'Province/Territory'
    province_time_sales = filtered_df.groupby(['Month and Year', 'Province/Territory'])['Number of Cars'].sum().reset_index()

    # Pivot the data to have 'Month and Year' as x-axis and provinces as lines
    pivot_df = province_time_sales.pivot(index='Month and Year', columns='Province/Territory', values='Number of Cars').fillna(0)

    # Determine the top 4 provinces based on the most recent month's sales
    latest_month = pivot_df.index.max()
    top_provinces = pivot_df.loc[latest_month].sort_values(ascending=False).nlargest(4).index.tolist()
    
    # **New Code Starts Here**
    # Sort all provinces based on sales in the latest month
    sorted_provinces = pivot_df.loc[latest_month].sort_values(ascending=False).index.tolist()
    
    # Reorder pivot_df columns based on sorted_provinces
    pivot_df = pivot_df[sorted_provinces]
    # **New Code Ends Here**

    # Create the Plotly line chart with all provinces
    fig = px.line(
        pivot_df,
        x=pivot_df.index,
        y=pivot_df.columns,
        title='Sales by Province/Territory Over Time',
        labels={'value': 'Number of Cars', 'Month and Year': 'Date'},
        template='plotly_white'
    )
    fig.update_layout(
        xaxis_title='Month and Year',
        yaxis_title='Number of Cars',
        legend_title_text='Province/Territory',
        title_x=0.5,
        xaxis=dict(
            range=[end_date - pd.DateOffset(years=1), end_date],  # Default to past year
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(count=2, label="2y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )

    # Set visibility: top 4 provinces visible, others legendonly
    for trace in fig.data:
        if trace.name not in top_provinces:
            trace.visible = 'legendonly'
        # **New Code Starts Here**
        # Update hover template to include Province/Territory name
        trace.hovertemplate = '%{fullData.name}<br>%{x|%b %Y}<br>Cars Sold: %{y}<extra></extra>'
        # **New Code Ends Here**

    # Enable panning and zooming
    fig.update_xaxes(rangeslider_visible=True)

    # Convert the figure to HTML
    province_graph_html = fig.to_html(full_html=False, config={'displayModeBar': False, 'responsive': True})

    return jsonify({
        'province_graph_html': province_graph_html
    })

if __name__ == '__main__':
    app.run(debug=True)