import requests
import pandas as pd
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration
APP_KEY = os.environ.get('TFL_API_KEY')
BASE_URL = "https://api.tfl.gov.uk"
LONDON_LAT, LONDON_LON = 51.5074, -0.1278
TARGET_ROUTES = ["25", "73", "149"]

def make_api_call(endpoint, base_url=BASE_URL, params=None):
    """Make API call with error handling"""
    url = f"{base_url}{endpoint}"
    params = params or {}
    if base_url == BASE_URL:
        params["app_key"] = APP_KEY
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  [!] API Error for {endpoint}: {e}")
        return None

def save_dataframe(data, folder_path, filename):
    """Appends data to a single persistent CSV file with all original fields"""
    if not data:
        return
    
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{filename}.csv"
    
    df = pd.DataFrame(data)
    file_exists = file_path.exists()
    
    # Append mode 'a', write header only if file is new
    df.to_csv(file_path, mode='a', index=False, header=not file_exists)
    print(f"  [+] Success: Appended {len(data)} rows to {file_path}")

def get_route_stops(route_id):
    """Get all stops for a bus route (Metadata)"""
    endpoint = f"/Line/{route_id}/Route/Sequence/outbound"
    data = make_api_call(endpoint)
    if not data: return []
    
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

def main():
    print(f"--- Data Collection Session Started: {datetime.now()} ---")
    
    if not APP_KEY:
        print("ERROR: TFL_API_KEY not found in environment")
        sys.exit(1)

    # 1. ROUTE METADATA
    stops_file = Path("data/stops/route_stops.csv")
    if not stops_file.exists():
        print("Collecting route metadata...")
        all_stops = []
        for route in TARGET_ROUTES:
            all_stops.extend(get_route_stops(route))
        save_dataframe(all_stops, "data/stops", "route_stops")
    
    stops_df = pd.read_csv(stops_file)

    # 2. BUS ARRIVALS (ALL ORIGINAL FIELDS)
    try:
        print("Collecting bus arrivals...")
        all_arrivals = []
        timestamp_now = datetime.now().isoformat()
        
        for route in TARGET_ROUTES:
            route_stops = stops_df[stops_df['route_id'] == route]['stop_id'].unique()
            sampled_stops = route_stops[::3] # Every 3rd stop
            
            for stop_id in sampled_stops:
                endpoint = f"/StopPoint/{stop_id}/Arrivals"
                data = make_api_call(endpoint)
                if data:
                    for arrival in data:
                        if arrival.get('lineId') == route:
                            all_arrivals.append({
                                'collection_time': timestamp_now,
                                'route_id': route,
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
                time.sleep(0.1) # Prevent rate limiting
        save_dataframe(all_arrivals, "data/arrivals", "arrivals")
    except Exception as e:
        print(f"Arrivals Task Error: {e}")

    # 3. DISRUPTIONS (ALL ORIGINAL FIELDS)
    try:
        print("Collecting disruptions...")
        data = make_api_call("/Road/all/Disruption")
        if data:
            timestamp_now = datetime.now().isoformat()
            disruptions = []
            for d in data:
                disruptions.append({
                    'collection_time': timestamp_now,
                    'disruption_id': d.get('id'),
                    'category': d.get('category'),
                    'severity': d.get('severity'),
                    'location': d.get('location'),
                    'corridor': str(d.get('corridorIds')),
                    'comments': d.get('comments')
                })
            save_dataframe(disruptions, "data/disruptions", "disruptions")
    except Exception as e:
        print(f"Disruptions Task Error: {e}")

    # 4. WEATHER (ALL ORIGINAL FIELDS)
    try:
        print("Collecting weather data...")
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': LONDON_LAT, 'longitude': LONDON_LON,
            'current': 'temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m',
            'timezone': 'Europe/London'
        }
        response = requests.get(weather_url, params=params, timeout=30)
        data = response.json()
        current = data.get('current', {})
        if current:
            weather_record = [{
                'collection_time': datetime.now().isoformat(),
                'temperature_c': current.get('temperature_2m'),
                'humidity_percent': current.get('relative_humidity_2m'),
                'precipitation_mm': current.get('precipitation'),
                'rain_mm': current.get('rain'),
                'weather_code': current.get('weather_code'),
                'wind_speed_kmh': current.get('wind_speed_10m'),
                'observation_time': current.get('time')
            }]
            save_dataframe(weather_record, "data/weather", "weather")
    except Exception as e:
        print(f"Weather Task Error: {e}")

    print(f"--- Collection Complete: {datetime.now()} ---")

if __name__ == "__main__":
    main()