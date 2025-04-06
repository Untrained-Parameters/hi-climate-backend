import datetime
import aiohttp
import asyncio
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://api.hcdp.ikewai.org"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('OAUTH_TOKEN')}"  # Read token from .env file
}

async def fetch(session, url, method="GET", params=None, json=None):
    """
    Helper function to make asynchronous HTTP requests.
    """
    async with session.request(method, url, params=params, json=json) as response:
        return await response.json()

async def get_raster(date, datatype, extent, return_empty_not_found=True):
    """
    Fetches a raster file from the HCDP API.
    """
    url = f"{BASE_URL}/raster"
    params = {
        "date": date,
        "datatype": datatype,
        "extent": extent,
        "returnEmptyNotFound": str(return_empty_not_found).lower()
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_raster_timeseries(start, end, datatype, extent, **location_params):
    """
    Fetches a raster timeseries from the HCDP API.
    """
    url = f"{BASE_URL}/raster/timeseries"
    params = {
        "start": start,
        "end": end,
        "datatype": datatype,
        "extent": extent,
        **location_params
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def post_genzip_email(email, data, zip_name=None):
    """
    Requests a zip file to be sent to the specified email.
    """
    url = f"{BASE_URL}/genzip/email"
    payload = {
        "email": email,
        "data": data
    }
    if zip_name:
        payload["zipName"] = zip_name
    async with aiohttp.ClientSession(headers={**HEADERS, "Content-Type": "application/json"}) as session:
        return await fetch(session, url, method="POST", json=payload)

async def post_genzip_instant_content(email, data):
    """
    Requests a zip file and returns its content.
    """
    url = f"{BASE_URL}/genzip/instant/content"
    payload = {
        "email": email,
        "data": data
    }
    async with aiohttp.ClientSession(headers={**HEADERS, "Content-Type": "application/json"}) as session:
        return await fetch(session, url, method="POST", json=payload)

async def post_genzip_instant_link(email, data, zip_name=None):
    """
    Requests a zip file and returns a link to the data.
    """
    url = f"{BASE_URL}/genzip/instant/link"
    payload = {
        "email": email,
        "data": data
    }
    if zip_name:
        payload["zipName"] = zip_name
    async with aiohttp.ClientSession(headers={**HEADERS, "Content-Type": "application/json"}) as session:
        return await fetch(session, url, method="POST", json=payload)

async def get_raw_list(date, station_id=None, location="hawaii"):
    """
    Fetches a list of raw data files for a specific date.
    """
    url = f"{BASE_URL}/raw/list"
    params = {
        "date": date,
        "station_id": station_id,
        "location": location
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_production_list(data):
    """
    Fetches a list of production data files.
    """
    url = f"{BASE_URL}/production/list"
    params = {"data": data}
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_files_explore(path):
    """
    Explores files in a specific directory or retrieves a file.
    """
    url = f"{BASE_URL}/files/explore/{path}"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url)

async def get_files_retrieve_production(date, datatype, extent, file_type="data_map"):
    """
    Retrieves a production file.
    """
    url = f"{BASE_URL}/files/retrieve/production"
    params = {
        "date": date,
        "datatype": datatype,
        "extent": extent,
        "file": file_type
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_stations(query, limit=10000, offset=0):
    """
    Fetches station data based on a query.
    """
    url = f"{BASE_URL}/stations"
    params = {
        "q": query,
        "limit": limit,
        "offset": offset
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_mesonet_measurements(location="hawaii", **query_params):
    """
    Fetches mesonet measurements.
    """
    url = f"{BASE_URL}/mesonet/db/measurements"
    params = {
        "location": location,
        **query_params
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_mesonet_stations(location="hawaii", **query_params):
    """
    Fetches mesonet station data.
    """
    url = f"{BASE_URL}/mesonet/db/stations"
    params = {
        "location": location,
        **query_params
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

async def get_mesonet_variables(**query_params):
    """
    Fetches mesonet variable data.
    """
    url = f"{BASE_URL}/mesonet/db/variables"
    params = query_params
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        return await fetch(session, url, params=params)

# function to get response from already formed request
# https://api.hcdp.ikewai.org/raster/timeseries?start=1990-01-01&end=2024-01-01&lat=19.5&lng=-155.5&extent=statewide&datatype=rainfall&production=new&period=month\

async def get_response_from_request(request):
    """
    Fetches a response from the HCDP API based on a pre-formed request.
    """
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        response = await fetch(session, request)
        return response
    
async def get_location(location: str) -> list[dict]:
    """
    Get latitude and longitude for a given location.

    Args:
        location (str): Location name.

    Returns:
        list[dict]: A list of dictionaries with the latitude and longitude of the given location.
                    Returns an empty list if the location cannot be determined.
    """
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{location}, Hawaii",
        "format": "json",
    }

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "none"}) as session:
            async with session.get(base_url, params=params) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error fetching location data: {e}")
        return []

async def request_from_params(params):
    """
    Constructs a request URL from the provided parameters.
    """
    today = datetime.datetime.now().isoformat()

    api_defaults = {
            "time_start": "1990-01-01",
            "time_end": today,
            "location": "hawaii",
            "lat": 19.5,
            "lng": -155.5,
            "datatype": "rainfall",
            "period": "month",
            "aggregation": "mean",
            "extent": "statewide",
            "production": "new",
        }
    for key, value in params.items():
        if key == "location":
            location_data = await get_location(value)
            if location_data:
                api_defaults["lat"] = location_data[0]["lat"]
                api_defaults["lng"] = location_data[0]["lon"]
            else:
                print(f"Could not find coordinates for location: {value}")
        api_defaults[key] = value.lower() if isinstance(value, str) else value
    
    api_params = {
        "start": api_defaults.get("time_start"),
        "end": api_defaults.get("time_end"),
        "lat": api_defaults.get("lat"),
        "lng": api_defaults.get("lng"),
        "datatype": api_defaults.get("datatype"),
        "extent": api_defaults.get("extent"),
        "period": api_defaults.get("period"),        
    }

    if api_params.get("datatype") == "temperature":
        api_params["aggregation"] = api_defaults.get("aggregation")
    if api_params.get("datatype") == "rainfall":
        api_params["production"] = api_defaults.get("production")

    url = f"{BASE_URL}/raster/timeseries"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, params=api_params) as response:
            print(response)
            response.raise_for_status()
            data = await response.json()
            if "error" in data:
                print(f"Error fetching data: {data['error']}")
                return None
            else:
                return data