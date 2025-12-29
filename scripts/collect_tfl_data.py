"""
TfL London Bus Data Collection Script - Enhanced with Weather & Traffic
Collects bus arrivals, disruptions, weather, and road conditions
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime
import sys

# Configuration
APP_KEY = os.environ.get('TFL_API_KEY')
BASE_URL = "https://api.tfl.gov.uk"

# London coordinates for weather
LONDON_LAT = 51.5074
LONDON_LON = -0.1278

TARGET_ROUTES = ["25", "73", "149"]

def make_api_call(endpoint, base_url=BASE_URL, params=None):
    """Make API call with error handling"""
    url = f"{base_url}{endpoint}"
    
    if params is None:
        params = {}
    
    # Add TfL API key only for TfL endpoints
    if base_url == BASE_URL:
        params["app_key"] = APP_KEY
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error for {endpoint}: {e}")
        return None

def get_route_stops(route_id):
    """Get all stops for a bus route"""
    endpoint = f"/Line/{route_id}/Route/Sequence/outbound"
    data = make_api_call(endpoint)
    
    if not data:
        return []
    
    stops = []
    for stop_sequence in data.get('stopPointSequences', []):
        for stop in stop_sequence.get('stopPoint', []):
            stops.append({
                'route_id': route_id,
                'stop_id': stop.get('id'),
                'stop_name': stop.get('name'),
                'lat': stop.get('lat'),
                'lon': stop.get('lon')
            })
    
    return stops

def get_bus_arrivals(stop_id, route_id):
    """Get predicted arrivals for a specific stop and route"""
    endpoint = f"/StopPoint/{stop_id}/Arrivals"
    data = make_api_call(endpoint)
    
    if not data:
        return []
    
    arrivals = []
    timestamp = datetime.now().isoformat()
    
    for arrival in data:
        if arrival.get('lineId') == route_id:
            arrivals.append({
                'collection_time': timestamp,
                'route_id': route_id,
                'stop_id': stop_id,
                'stop_name': arrival.get('stationName'),
                'vehicle_id': arrival.get('vehicleId'),
                'destination': arrival.get('destinationName'),
                'expected_arrival': arrival.get('expectedArrival'),
                'time_to_station': arrival.get('timeToStation'),
                'current_location': arrival.get('currentLocation'),
                'towards': arrival.get('towards'),
                'direction': arrival.get('direction'),
                'timestamp': arrival.get('timestamp')
            })
    
    return arrivals

def get_disruptions():
    """Get current road disruptions"""
    endpoint = "/Road/all/Disruption"
    data = make_api_call(endpoint)
    
    if not data:
        return []
    
    disruptions = []
    timestamp = datetime.now().isoformat()
    
    for disruption in data:
        disruptions.append({
            'collection_time': timestamp,
            'disruption_id': disruption.get('id'),
            'category': disruption.get('category'),
            'severity': disruption.get('severity'),
            'location': disruption.get('location'),
            'corridor': str(disruption.get('corridorIds')),
            'comments': disruption.get('comments')
        })
    
    return disruptions

def get_weather_data():
    """Get current weather for London using Open-Meteo API (FREE, no key needed)"""
    # Open-Meteo API - completely free, no API key required
    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': LONDON_LAT,
        'longitude': LONDON_LON,
        'current': 'temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m',
        'timezone': 'Europe/London'
    }
    
    try:
        response = requests.get(weather_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        current = data.get('current', {})
        timestamp = datetime.now().isoformat()
        
        return [{
            'collection_time': timestamp,
            'temperature_c': current.get('temperature_2m'),
            'humidity_percent': current.get('relative_humidity_2m'),
            'precipitation_mm': current.get('precipitation'),
            'rain_mm': current.get('rain'),
            'weather_code': current.get('weather_code'),
            'wind_speed_kmh': current.get('wind_speed_10m'),
            'observation_time': current.get('time')
        }]
    except Exception as e:
        print(f"Weather API Error: {e}")
        return []

def main():
    """Main collection function"""
    print(f"Starting data collection at {datetime.now()}")
    
    if not APP_KEY:
        print("ERROR: TFL_API_KEY not found in environment")
        sys.exit(1)
    
    # Collect route stops (only if not exists)
    stops_file = "data/stops/route_stops.csv"
    if not os.path.exists(stops_file):
        print("Collecting route metadata...")
        all_stops = []
        for route in TARGET_ROUTES:
            stops = get_route_stops(route)
            all_stops.extend(stops)
        
        if all_stops:
            os.makedirs("data/stops", exist_ok=True)
            pd.DataFrame(all_stops).to_csv(stops_file, index=False)
            print(f"Saved {len(all_stops)} stops")
    
    # Load stops
    stops_df = pd.read_csv(stops_file)
    
    # Collect arrivals
    print("Collecting bus arrivals...")
    all_arrivals = []
    for route in TARGET_ROUTES:
        route_stops = stops_df[stops_df['route_id'] == route]['stop_id'].unique()
        sampled_stops = route_stops[::3]  # Every 3rd stop
        
        for stop_id in sampled_stops:
            arrivals = get_bus_arrivals(stop_id, route)
            all_arrivals.extend(arrivals)
    
    # Save arrivals
    if all_arrivals:
        date_str = datetime.now().strftime('%Y%m%d')
        arrivals_file = f"data/arrivals/arrivals_{date_str}.csv"
        os.makedirs("data/arrivals", exist_ok=True)
        
        df = pd.DataFrame(all_arrivals)
        if os.path.exists(arrivals_file):
            df.to_csv(arrivals_file, mode='a', header=False, index=False)
        else:
            df.to_csv(arrivals_file, index=False)
        
        print(f"Saved {len(all_arrivals)} arrivals to {arrivals_file}")
    
    # Collect disruptions
    print("Collecting disruptions...")
    disruptions = get_disruptions()
    
    if disruptions:
        date_str = datetime.now().strftime('%Y%m%d')
        disrupt_file = f"data/disruptions/disruptions_{date_str}.csv"
        os.makedirs("data/disruptions", exist_ok=True)
        
        df = pd.DataFrame(disruptions)
        if os.path.exists(disrupt_file):
            df.to_csv(disrupt_file, mode='a', header=False, index=False)
        else:
            df.to_csv(disrupt_file, index=False)
        
        print(f"Saved {len(disruptions)} disruptions to {disrupt_file}")
    
    # Collect weather data
    print("Collecting weather data...")
    weather = get_weather_data()
    
    if weather:
        date_str = datetime.now().strftime('%Y%m%d')
        weather_file = f"data/weather/weather_{date_str}.csv"
        os.makedirs("data/weather", exist_ok=True)
        
        df = pd.DataFrame(weather)
        if os.path.exists(weather_file):
            df.to_csv(weather_file, mode='a', header=False, index=False)
        else:
            df.to_csv(weather_file, index=False)
        
        print(f"Saved {len(weather)} weather records to {weather_file}")
    
    print("Collection complete!")

if __name__ == "__main__":
    main()