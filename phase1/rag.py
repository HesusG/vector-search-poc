# %% 
import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import ollama
# %%
dotenv_path = "/path/to/your/.env"
load_dotenv(dotenv_path=dotenv_path)
es_host = os.environ.get("ELASTICSEARCH_HOST")
es_user = os.environ.get("ELASTICSEARCH_USER")
es_pass = os.environ.get("ELASTICSEARCH_PASS")

es = Elasticsearch(
    hosts=f"{es_host}", 
    basic_auth=(f"{es_user}", f"{es_pass}")
)

# %% 


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
    
    response = es.search(index=index, body=search_body)
    return response['hits']['hits']

def get_random_document(index):
    result = es.search(index=index, body={"size": 1, "query": {"function_score": {"random_score": {}}}})
    return result['hits']['hits'][0]

index_name = 'ticket_similarity'
field_name = 'combined_text_vector'

random_doc = get_random_document(index_name)
query_vector = random_doc['_source'][field_name]

results = knn_search(index=index_name, field=field_name, query_vector=query_vector, k=10)

retrieved_docs = [hit['_source'] for hit in results]
# %% 
client = ollama.Client()

def summarize_with_context(context):
    prompt = f"Summarize the following tickets:\n{context}"
    response = client.generate(
        model="llama3",
        prompt=prompt
    )
    return response

# Example context
context = " ".join([doc['combined_text'] for doc in retrieved_docs])

# Generate a summary using the retrieved context
summary = summarize_with_context(context)
print(summary)

# %%
from collections import Counter

def sample_tickets(index, size=100):
    query_body = {
        "size": size,
        "query": {
            "bool": {
                "must_not": [
                    {"term": {"solution": "Unknown"}}
                ]
            }
        }
    }
    
    response = es.search(index=index, body=query_body)
    tickets = [hit['_source'] for hit in response['hits']['hits']]
    return tickets

def most_common_solution(tickets):
    solutions = [ticket['solution'] for ticket in tickets]
    solution_counts = Counter(solutions)
    most_common = solution_counts.most_common(1)
    return most_common[0] if most_common else None

client = ollama.Client()

def generate_text_with_context(context, query):
    prompt = f"{context}\n\nQuery: {query}"
    response = client.generate(
        model="llama3",
        prompt=prompt
    )
    return response

# %% Test no stream
index_name = 'ticket_similarity'
sampled_tickets = sample_tickets(index_name)
print(f"Sampled {len(sampled_tickets)} tickets.")

most_common_sol = most_common_solution(sampled_tickets)
print(f"Most common solution: {most_common_sol}")


context = "\n".join([f"Ticket ID: {i+1}, Solution: {ticket['solution']}" for i, ticket in enumerate(sampled_tickets)])
query = "What is the most common solution?"


generated_response = generate_text_with_context(context, query)
print(generated_response)


# %% Stream

def generate_text_with_context_streaming(context, query):
    stream = ollama.chat(
        model='llama3',
        messages = [
        {'role': 'user', 'content': f"{context}\n\nQuery: {query}"}
    ],
        stream=True,
    )
    return stream
   
index_name = 'ticket_similarity'
sampled_tickets = sample_tickets(index_name)
print(f"Sampled {len(sampled_tickets)} tickets.")

most_common_sol = most_common_solution(sampled_tickets)
print(f"Most common solution: {most_common_sol}")

context = "\n".join([f"Ticket ID: {i+1}, Solution: {ticket['solution']}" for i, ticket in enumerate(sampled_tickets)])
user_message = "What is the most common solution?"
stream = generate_text_with_context_streaming(context, user_message)
# %%
