# data_loader.py

import pandas as pd

def load_data():
    """
    Load and preprocess the car sales data from a CSV file.
    
    Returns:
        pd.DataFrame: Preprocessed DataFrame containing car sales data.
    """
    try:
        # Replace 'car_sales_data.csv' with your actual CSV file name
        df = pd.read_csv('car_summary.csv')
        
        # Preprocess data as needed
        df['Month and Year'] = pd.to_datetime(df['Month and Year'], format='%B %Y')
        df['Vehicle Make'] = df['Vehicle Make'].str.strip()
        df['Vehicle Model'] = df['Vehicle Model'].str.strip()
        df['Vehicle Type'] = df['Battery-Electric Vehicle (BEV), Plug-in Hybrid Electric Vehicle (PHEV) or Fuel Cell Electric Vehicle (FCEV)']
        df['Province/Territory'] = df['Recipient Province/Territory']
        
        return df
    except FileNotFoundError:
        print("Error: The data file 'car_sales_data.csv' was not found.")
        return pd.DataFrame()

def get_unique_values(df):
    """
    Extract unique vehicle types and provinces/territories from the DataFrame.
    
    Args:
        df (pd.DataFrame): The car sales DataFrame.
        
    Returns:
        tuple: (vehicle_types, provinces, vehicle_models)
    """
    vehicle_types = ['All'] + sorted(df['Vehicle Type'].dropna().unique())
    provinces = ['All'] + sorted(df['Province/Territory'].dropna().unique())
    vehicle_models = sorted(df['Vehicle Model'].dropna().unique())
    
    return vehicle_types, provinces, vehicle_models