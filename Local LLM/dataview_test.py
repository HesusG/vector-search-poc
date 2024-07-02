# %% 
import pandas as pd 
import numpy as np 
from dotenv import load_dotenv

dotenv_path = "/home/d3r/Documents/Github/vector_search_poc/.env"

# Load the environment variables from the specified path
load_dotenv(dotenv_path=dotenv_path)

# Access the environment variables using os.environ
ELASTICSEARCH_HOST = os.environ.get("ElasticURL")
KIBANA_HOST = os.environ.get("KibanaHost")
KIBANA_API_KEY = os.environ.get("KibanaKey")

# %%
import json
import requests
from elasticsearch import Elasticsearch
# %%
es = Elasticsearch(ELASTICSEARCH_HOST)

# Data view ID and field details
data_view_id = '3c5ca248-2566-4712-9418-99b65d39902c'
field_name = 'CostUSD'
custom_label = 'Costo'

# Kibana API endpoint
kibana_api_url = f'{KIBANA_HOST}/api/data_views/data_view/{data_view_id}'

# Headers for the Kibana API request
headers = {
    'kbn-xsrf': 'true',
    'Content-Type': 'application/json'
}

# Optional: Add authentication header if required
# headers['Authorization'] = f'ApiKey {KIBANA_API_KEY}'

# Payload to update the data view
payload = {
  "data_view": {
    "fieldAttrs": {
      field_name: {
        "customLabel": custom_label
      }
    }
  }
}

# Send PUT request to update the data view
response = requests.put(kibana_api_url, headers=headers, data=json.dumps(payload))

# Check response
if response.status_code == 200:
    print(f'Successfully updated data view: {data_view_id}')
else:
    print(f'Failed to update data view: {response.status_code}, {response.text}')
# %%
import json
import pandas as pd

# Load the mappings from the provided file
with open('./data/mappings_azcost.txt', 'r') as file:
    mappings = json.load(file)

# Extract the field names
fields = mappings['azure.costmanager']['mappings']

# Filter for tags fields
tags_fields = {k: v for k, v in fields.items() if 'tags.' in k}

# Count the number of tags fields
num_tags_fields = len(tags_fields)

# Create a DataFrame to store the original and custom field names
df = pd.DataFrame({
    'Original Field Name': tags_fields.keys(),
    'Custom Field Name': [k.replace('tags.', '').replace('_', ' ').title() for k in tags_fields.keys()]
})

# Display the count of tags fields
num_tags_fields, df.head()
# %%
with open('./data/odoo_ticket.txt', 'r') as file:
    json_data = json.load(file)

fields_without_custom_label = [field for field, details in json_data['data_view']['fields'].items() if 'customLabel' not in details]

print("Fields without customLabel:", fields_without_custom_label)
# %%
import json

# Load the JSON file
file_path = "./info/response.json"
with open(file_path, "r") as file:
    data = json.load(file)

# Function to check if the field matches the criteria
def check_field(field):
    if field.endswith(("id", "keyword", "name")):
        words = field.split('.')
        if len(words) >= 3 and (len(words[-2]) > 2 or len(words[-3]) > 2):
            return True
    return False

# Find all matching fields
matching_items = [key for key in data.keys() if check_field(key)]

# %%
