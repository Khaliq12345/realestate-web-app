import httpx
import json, math
import numpy as np
import asyncio
import pandas as pd
# from sqlalchemy.dialects import postgresql
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app_model import Tbl_Property
import psycopg2
from psycopg2.extras import Json
psycopg2.extensions.register_adapter(dict, Json)
import config

class scraperDB:
    properties = []
    
db = scraperDB()

headers = {
  'Content-Type': 'application/json',
  'x-api-key': 'RMD-87a8-76eb-952d-3f35dc057092'
}

query_string = '''INSERT INTO property_2 (p_id, first_name, last_name, address, property_type, pre_foreclosure, 
           vacant, owner_occupied, other_info) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (p_id) DO UPDATE 
           SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, address = EXCLUDED.address, 
           property_type = EXCLUDED.property_type, pre_foreclosure = EXCLUDED.pre_foreclosure,
           vacant = EXCLUDED.vacant, owner_occupied = EXCLUDED.owner_occupied, other_info = EXCLUDED.other_info;
        '''

async def log_response(resp: httpx.Response):
    print(f'Response url: {resp.request.url} | Status: {resp.status_code}')

async def log_request(req: httpx.Request):
    print(f'Request url: {req.url} | Request method: {req.method}')
    
def save_data():
    df = pd.DataFrame(db.properties)
    df['other_info'] = df['other_info'].map(lambda x: Json(x))
    df_tuples = list(df.itertuples(index=False, name=None))
    with psycopg2.connect(config.con_string) as conn:
        with conn.cursor() as cur:
            cur.executemany(query_string, df_tuples)
            conn.commit()
            
    print("DONE")
    return df
    
def data_parser(p_data: dict):
    return {
    'p_id': p_data['data']['id'],
    'first_name': try_except("p_data['data']['ownerInfo'].get('owner1FirstName')", p_data),
    'last_name': try_except("p_data['data']['ownerInfo'].get('owner1LastName')", p_data),
    'address': try_except("p_data['data']['propertyInfo']['address'].get('label')", p_data),
    'property_type': try_except("p_data['data'].get('propertyType')", p_data),
    'pre_foreclosure': try_except("p_data['data'].get('preForeclosure')", p_data),
    'vacant': try_except("p_data['data'].get('vacant')", p_data),
    'owner_occupied': try_except("p_data['data'].get('ownerOccupied')", p_data),
    'other_info': p_data
    }

def try_except(query: str, p_data):
    try:
        return str(eval(query)) if type(eval(query)) == bool else eval(query)
    except AttributeError:
        return None

async def get_prop_data(p_id: str):
    url = "https://api.realestateapi.com/v2/PropertyDetail"
    eh = {"request": [log_request], "response": [log_response]}
    payload = {"id": f'{p_id}'}
    async with httpx.AsyncClient(event_hooks=eh, headers=headers, timeout=None) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            p_data = response.json()
            p_data = data_parser(p_data)
            db.properties.append(p_data)
    
def get_property_id(payload: dict):
    propert_ids = []
    search_metadata = {}
    error = None
    url = "https://api.realestateapi.com/v2/PropertySearch"
    with httpx.Client(headers=headers, timeout=None) as client:
        response = client.post(url, json=payload)
        print(f'Url: {url} | Status: {response.status_code}')
        if response.status_code == 200:
            propert_ids = response.json().get('data')
            search_metadata['input'] = response.json().get('input')
            search_metadata['record_count'] = response.json().get('recordCount')
            search_metadata['credits'] = response.json().get('credits')
        else:
            error = response.text
    return propert_ids, search_metadata, error

async def get_property_details(p_ids):
    db.properties = []
    limit = math.ceil(len(p_ids)/10)
    if limit == 0:
        return []
    else:
        batches = np.array_split(p_ids, limit)
        for batch in batches:
            tasks = []
            for p_id in batch:
                tasks.append(
                    asyncio.create_task(get_prop_data(p_id))
                )
            await asyncio.gather(*tasks)
    
    final_df = save_data()
    return final_df
    
    


        