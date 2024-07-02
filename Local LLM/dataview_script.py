# %%
import pandas as pd 
import numpy as np 
import requests
import os
from dotenv import load_dotenv
# import ollama

dotenv_path = "/home/d3r/Documents/Github/vector_search_poc/.env"

# Load the environment variables from the specified path
load_dotenv(dotenv_path=dotenv_path)

# Access the environment variables using os.environ
ELASTICSEARCH_HOST = os.environ.get("ElasticURL")
KIBANA_HOST = os.environ.get("KibanaHost")
KIBANA_API_KEY = os.environ.get("KibanaKey")

fields_without_custom_label = []
readable_labels = []
indices_views = {
    "odoo.helpdesk.ticket":"bf4ea9fa-4b4f-493a-8033-aeb706f9db86",
}


 # %%
def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# %%
def fetch_data_view_details(indices_views):
    global fields_without_custom_label
    # Assuming KIBANA_API_KEY is defined elsewhere in your script
    headers = {
        "kbn-xsrf": "true",  # Often needed for Kibana API calls for CSRF protection
        "Authorization": f"ApiKey {KIBANA_API_KEY}"
    }
    
    for index_name, data_view_id in indices_views.items():
        url = f"https://df-us-01.convergetp.com/api/data_views/data_view/{data_view_id}"
        
        # Make the GET request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            print(f"Data view details for {index_name}:")
            data_view_details = response.json()
            print(data_view_details, end="\n\n")
            fields = data_view_details.get('data_view', {}).get('fields', {})
            fields_without_custom_label = [field_name for field_name, field_details in fields.items() if 'customLabel' not in field_details]
            
            print(f"Fields without customLabel for {index_name}:")
            for field in fields_without_custom_label:
                print(field)
        else:
            print(f"Failed to fetch data view details for {index_name}: {response.status_code}")

fetch_data_view_details(indices_views)
# %%

def fetch_data_view_details_with_custom_labels(indices_views):
    headers = {
        "kbn-xsrf": "true",  # Often needed for Kibana API calls for CSRF protection
        "Authorization": f"ApiKey {KIBANA_API_KEY}"
    }

    for index_name, data_view_id in indices_views.items():
        url = f"https://df-us-01.convergetp.com/api/data_views/data_view/{data_view_id}"
        
        # Make the GET request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            print(f"Data view details for {index_name}:")
            data_view_details = response.json()
            fields = data_view_details.get('data_view', {}).get('fields', {})
            
            fields_with_custom_label = [field_name for field_name, field_details in fields.items() if 'customLabel' in field_details]
            
            print(f"Fields with customLabel for {index_name}:")
            for field in fields_with_custom_label:
                print(field)
        else:
            print(f"Failed to fetch data view details for {index_name}: {response.status_code}")
# %%
def generate_readable_labels(fields):
    readable_labels = []
    # chunks = list(chunk_list(fields, 10))
    
    # Initialize the Ollama model
    client = ollama.Client()

    # Construct the prompt
    prompt = "Generate a more readable label name for each of the following fields:\n" + "\n".join(fields)
    
    # Send the request to the local Ollama server
    response = client.generate(prompt=prompt, model="orca-mini")
    return response['response']
# %%
