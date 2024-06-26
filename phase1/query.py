# %% 
import os
import torch
import pandas as pd
import time 
import random 
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# %% 
pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', None)

# %%
dotenv_path = "/home/d3r/Documents/Github/vector_search_poc/.env"

load_dotenv(dotenv_path=dotenv_path)

es_host = os.environ.get("ELASTICSEARCH_HOST")
es_user = os.environ.get("ELASTICSEARCH_USER")
es_pass = os.environ.get("ELASTICSEARCH_PASS")

es = Elasticsearch(
    hosts=[es_host],
    basic_auth=(es_user, es_pass)
)

# %%
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
model = AutoModel.from_pretrained('bert-base-uncased')

def generate_query_vector(query):
    inputs = tokenizer(query, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        output = model(**inputs).last_hidden_state.mean(dim=1).squeeze(0).numpy()
    return output

def knn_search(index, field, query_vector, k=3, num_candidates=400):
    search_body = {
        "knn": {
            "field": field,
            "query_vector": query_vector.tolist(),
            "k": k,
            "num_candidates": num_candidates
        },
        "_source": ["description", "solution", "combined_text", "cicore_id_name", "is_alert", "stage_id_name", "handle_type", "team_category", "owner_id_name"]
    }
    response = es.search(index=index, body=search_body)
    return response['hits']['hits']

queries = {
    "combined_text": "System crash when trying to generate report in Odoo for GCB",
    "description_plain": "dear it support please assign petra berger the following phone number 0049 621 49494048 former beate rahns number thank you christian",
    "solution": "unarchive dell record"
}
# %%

query_vectors = {field: generate_query_vector(query) for field, query in queries.items()}

for field, query_vector in query_vectors.items():
    print(f"Results for {field}:")
    results = knn_search(index='ticket_similarity', field=f"{field}_vector", query_vector=query_vector)
    for hit in results:
        print(f"Ticket: {hit['_source']}")

# %%
def get_random_document(index):
    result = es.search(index=index, body={"size": 1, "query": {"function_score": {"random_score": {}}}})
    return result['hits']['hits'][0]

# %%
index_name = 'ticket_similarity'
field_name = 'combined_text_vector'

random_doc = get_random_document(index_name)
query_vector = random_doc['_source'][field_name]
# %%
def knn_search(index, field, query_vector, k=10):
    search_body = {
        "knn": {
            "field": field,
            "query_vector": query_vector,
            "k": k,
            "num_candidates": 100 
        },
        "_source": ["description", "solution", "combined_text", "cicore_id_name", "is_alert", "stage_id_name", "handle_type", "team_category", "owner_id_name"]
    }
    
    start_time = time.time()
    response = es.search(index=index, body=search_body)
    duration = time.time() - start_time
    return response['hits']['hits'], duration

# %%
results, duration = knn_search(index=index_name, field=field_name, query_vector=query_vector, k=10)

print(f"Time taken for KNN search: {duration:.4f} seconds")
for hit in results:
    print(f"Ticket: {hit['_source']}")
# %%
