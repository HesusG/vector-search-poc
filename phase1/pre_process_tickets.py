# %%
import sys, os, warnings
import eland as ed
import pandas as pd
import re
import html
import numpy as np
from transformers import AutoTokenizer, AutoModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
from tqdm import tqdm

# %%
pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', None)

# %%
# Construct the path to the .env file which is one directory up
dotenv_path = "/home/d3r/Documents/Github/vector_search_poc/.env"

# Load the environment variables from the specified path
load_dotenv(dotenv_path=dotenv_path)

# Access the environment variables using os.environ
es_host = os.environ.get("ELASTICSEARCH_HOST")
es_user = os.environ.get("ELASTICSEARCH_USER")
es_pass = os.environ.get("ELASTICSEARCH_PASS")

# Connect to Elasticsearch
es = Elasticsearch(
    hosts=[es_host],
    basic_auth=(es_user, es_pass)
)
source_index = 'odoo.helpdesk.ticket'
mapping = es.indices.get_mapping(index=source_index)
# %%
date_field = 'create_date'

# Calculate the start date of the past month
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Format dates in a way Elasticsearch expects
start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

# Elasticsearch query to filter data from the past month
query = {
    "query": {
        "range": {
            date_field: {  # Make sure this field name matches your date field in Elasticsearch
                "gte": start_date_str,
                "lt": end_date_str
            }
        }
    },
    "_source": [
    "description",
    "solution",
    "description_plain",
    "product_id",
    "ticket_type_id",
    "team_id",
    "team_level",
    "team",
    "is_alert",
    "stage_id",
    "stage_id_name",
    "handle_type",
    "current_duration",
    "message_total_count",
    "total_hours_spent",
    "cicore_id_name",
    "cicorfe_id",
    "cicore_id_name"]
}

# Initialize scroll
scroll = '2m'  # Keep the scroll context alive for 2 minutes
data = []  # To hold all the documents

# Perform the initial search
response = es.search(index=source_index, body=query, scroll=scroll, size=1000)
scroll_id = response['_scroll_id']

# Fetch subsequent batches of results
while True:
    # Get the next batch of documents
    response = es.scroll(scroll_id=scroll_id, scroll=scroll)
    
    # Break out of the loop when no more documents are returned
    if not response['hits']['hits']:
        break
    
    # Add the documents from this batch to our list
    data.extend([hit["_source"] for hit in response['hits']['hits']])
    
    # Update the scroll ID for the next scroll request
    scroll_id = response['_scroll_id']

# Close the scroll context
es.clear_scroll(scroll_id=scroll_id)

# Convert to Pandas DataFrame
df = pd.DataFrame(data)

# %%
def clean_text(text):

    if not isinstance(text, str):
        text = str(text)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ")
    text = html.unescape(text)
    text = text.replace(u'\xa0', ' ')
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation and other non-word characters
    text = text.strip()  # Remove leading and trailing spaces
    return text


# %%
def safe_convert_to_string(x):
    try:
        # Attempt to convert to string
        result = str(x)
        # Check if the conversion results in an empty or undesirable string
        if result in ['', 'nan', '{}', '[]']:
            return 'Unknown'
        return result
    except:
        # In case of any error during conversion, return 'Unknown'
        return 'Unknown'


# %%
def process_column(data):
    data = clean_text(data)
    data = safe_convert_to_string(data)
    return data

# %%
def print_null_percentage(df):
    """
    This function takes a pandas DataFrame as input and prints the percentage of null
    values in each column, distinguishing between numeric and categorical data types.
    
    Args:
    df (pd.DataFrame): The DataFrame to analyze for null values.
    
    Returns:
    None: Outputs the percentage of null values to the console.
    """
    # Check total number of entries in the DataFrame
    total_rows = len(df)
    
    # Initialize lists to store results
    numeric_nulls = []
    categorical_nulls = []
    
    # Loop through each column in the DataFrame
    for column in df.columns:
        # Calculate percentage of null values
        null_count = df[column].isnull().sum()
        null_percentage = (null_count / total_rows) * 100
        
        # Check data type of the column
        if pd.api.types.is_numeric_dtype(df[column]):
            numeric_nulls.append(f"{column} (Numeric): {null_percentage:.2f}% Null Values")
        else:
            categorical_nulls.append(f"{column} (Categorical): {null_percentage:.2f}% Null Values")
    
    # Print the results
    print("Null Value Percentages by Column:")
    for info in numeric_nulls + categorical_nulls:
        print(info)

# %%
print_null_percentage(df)

# %%
columns_to_impute = ['team_id', 'stage_id', 'ticket_type_id','product_id', 'cicore_id_name', 'team','stage_id_name','handle_type','stage_id_name']

for column in columns_to_impute:
    df[column] = df[column].fillna(9999)

# %%
df = df.dropna(subset=['description', 'description_plain','solution'])
columns_to_process = ['description', 'description_plain', 'solution']
for col in columns_to_process:
    df[col] = df[col].apply(process_column)
    
# %%
df = pd.concat([df.drop('team', axis=1), df['team'].apply(pd.Series)], axis=1).drop(columns=[0]) 
df = df.drop('id', axis=1)
df['team_category'] = df['team_category'].fillna('999')
df['team_level'] = df['team_level'].fillna('999')
df['owner_id_name'] = df['owner_id_name'].fillna('Unknown')

# %% 
df['combined_text'] = df['description'].str.strip() + " [solution] " + df['solution'].str.strip()

# %%
# Mappings
mapping = {
    "mappings": {
        "properties": {
            "current_duration": {"type": "float"},
            "message_total_count": {"type": "integer"},
            "team_id": {"type": "keyword"},  # Changed to keyword for categorical data
            "solution": {"type": "text"},
            "product_id": {"type": "keyword"},  # Confirm as keyword for categorical data
            "description_plain": {"type": "text"},
            "stage_id": {"type": "keyword"},  # Changed to keyword for categorical data
            "ticket_type_id": {"type": "keyword"},  # Changed to keyword for categorical data
            "description": {"type": "text"},
            "cicore_id_name": {"type": "keyword"},
            "is_alert": {"type": "text"},
            "stage_id_name": {"type": "text"},
            "handle_type": {"type": "text"},
            "team_level": {"type": "text"},
            "total_hours_spent": {"type": "float"},
            "team_category": {"type": "text"},
            "owner_id_name": {"type": "text"},
            "combined_text": {"type": "text"},
            "description_plain_vector": {"type": "dense_vector", "dims": 768},
            "solution_vector": {"type": "dense_vector", "dims": 768},
            "combined_text_vector": {"type": "dense_vector", "dims": 768}
        }
    }
}

# %%
index_name = "ticket_similarity"

# Create the index with the specified mapping
if not es.indices.exists(index=index_name):
    es.indices.create(index=index_name, body=mapping)
    print("Index created successfully!")
else:
    print("Index already exists!")

# %%
from transformers import AutoTokenizer, AutoModel
import torch

tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
model = AutoModel.from_pretrained('bert-base-uncased')

def get_bert_embeddings(text):
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    return embeddings.tolist()

# %%
# Generate embeddings for each relevant field
for column in ['description_plain', 'solution', 'combined_text']:
    if column in df.columns:
        df[column + '_vector'] = df[column].apply(get_bert_embeddings)

# %%
# Function to convert DataFrame row to dictionary
def row_to_dict(row):
    return row.to_dict()

# Index each row in the DataFrame as a document in Elasticsearch
for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Indexing documents"):
    doc = row_to_dict(row)
    es.index(index="ticket_similarity", body=doc)

# %%
df.to_pickle("my_dataframe.pkl")
# %%
df = pd.read_pickle('my_dataframe.pkl')

# %%
numeric_columns = ['current_duration', 'message_total_count', 'team_id', 'stage_id', 'ticket_type_id', 'total_hours_spent']

# %%
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()

# Scale the numeric columns and replace them in the DataFrame
df[numeric_columns] = scaler.fit_transform(df[numeric_columns])
# %%
from sklearn.feature_extraction import FeatureHasher

import pandas as pd

def apply_frequency_encoding(dataframe, column_name):
    # Count the frequency of each category
    frequency = dataframe[column_name].value_counts()
    # Map each category to its corresponding frequency
    dataframe[column_name + '_freq'] = dataframe[column_name].map(frequency)
    return dataframe

# List of categorical columns to encode
categorical_cols = ['solution', 'product_id', 'description_plain', 'description',
                    'cicore_id_name', 'is_alert', 'stage_id_name', 'handle_type', 'team_category', 'owner_id_name', 'combined_text']

# Apply frequency encoding to each categorical column
for col in categorical_cols:
    df = apply_frequency_encoding(df, col)
#%%
numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

# Manually specify your dense vector columns
vector_cols = ['description_plain_vector', 'solution_vector', 'combined_text_vector']

# Combine lists
selected_columns = numerical_cols + vector_cols

# Select these columns from the DataFrame
df_selected = df[selected_columns]
# %%
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
# %%
import pandas as pd
import numpy as np
from sklearn.preprocessing import Normalizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


# %%
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from sklearn.preprocessing import Normalizer

# Assuming df is your DataFrame and combined_text_vector is stored as lists
# Convert the list of vectors into a NumPy array
vectors = np.array(df['combined_text_vector'].tolist())

# Optionally normalize the vectors
normalizer = Normalizer()
vectors_normalized = normalizer.fit_transform(vectors)
# %%
k_range = range(1, 11)
inertias = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(vectors_normalized)
    inertias.append(kmeans.inertia_)

# Plotting the elbow curve
plt.figure(figsize=(8, 4))
plt.plot(k_range, inertias, 'bo-')
plt.xlabel('Number of Clusters (k)')
plt.ylabel('Inertia')
plt.title('Elbow Method For Optimal k')
plt.xticks(k_range)
plt.grid(True)
plt.show()

# %%
# Assuming k_optimal is chosen based on the elbow plot
k_optimal = 5  # Example value; adjust based on your observation
kmeans_final = KMeans(n_clusters=k_optimal, init='k-means++', random_state=42)
df['cluster'] = kmeans_final.fit_predict(vectors_normalized)

# Analyze the result
print(df[['combined_text_vector', 'cluster']].head())



# %%
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# Assume 'vectors_normalized' contains your normalized dense vectors
# Reduce dimensions
pca = PCA(n_components=2)
reduced_vectors = pca.fit_transform(vectors_normalized)

# Extract cluster labels
cluster_labels = kmeans_final.labels_

# Plotting
plt.figure(figsize=(10, 6))
plt.scatter(reduced_vectors[:, 0], reduced_vectors[:, 1], c=cluster_labels, cmap='viridis', marker='o', edgecolor='k', s=50, alpha=0.5)
plt.colorbar()
plt.title('PCA-based Clustering Visualization')
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.show()
# %%
from sklearn.manifold import TSNE

# Reducing dimension to 2D using t-SNE
tsne = TSNE(n_components=2, verbose=1, perplexity=40, n_iter=300)
tsne_results = tsne.fit_transform(vectors_normalized)

# Plotting
plt.figure(figsize=(10, 6))
plt.scatter(tsne_results[:, 0], tsne_results[:, 1], c=cluster_labels, cmap='viridis', marker='o', edgecolor='k', s=50, alpha=0.5)
plt.colorbar()
plt.title('t-SNE based Clustering Visualization')
plt.xlabel('t-SNE Feature 1')
plt.ylabel('t-SNE Feature 2')
plt.show()
# %%
cluster_means = df.groupby('cluster').mean()
print("Mean values per cluster for all numerical features:")
print(cluster_means)

# Calculate count, max, min, and other statistics as needed
cluster_counts = df.groupby('cluster').count()  # Counts can indicate the size of each cluster
print("\nCounts per cluster:")
print(cluster_counts)

# %%
from sklearn.manifold import TSNE

# Assuming 'data' is your high-dimensional data
tsne = TSNE(n_components=2, random_state=42)
tsne_results = tsne.fit_transform(vectors_normalized)

from sklearn.cluster import KMeans

# Use k-means or another clustering algorithm on the t-SNE output
k = 5  # Number of clusters
kmeans = KMeans(n_clusters=k, random_state=42)
clusters = kmeans.fit_predict(tsne_results)

# Now 'clusters' contains the cluster labels assigned to your data

import matplotlib.pyplot as plt

# Plotting the t-SNE results with cluster labels
plt.figure(figsize=(10, 8))
plt.scatter(tsne_results[:, 0], tsne_results[:, 1], c=clusters, cmap='viridis', alpha=0.5)
plt.colorbar()
plt.title('t-SNE visualization with cluster labels')
plt.xlabel('t-SNE Feature 1')
plt.ylabel('t-SNE Feature 2')
plt.show()

# %%
df['cluster_labels'] = clusters
# %%
import pandas as pd

# Assuming 'df' is your DataFrame
# Initialize lists to store column names
num_cols = []
cat_cols = []
selected_cols = []

# Categorize columns based on data type and name
for col in df.columns:
    if "_freq" in col or "_vector" in col or col in ["cluster", "kmeans"]:
        continue  # Skip columns based on exclusion criteria
    elif df[col].dtype in ['int64', 'float64']:
        num_cols.append(col)
    else:
        cat_cols.append(col)

# Optionally, combine lists if needed
selected_cols = num_cols + cat_cols

# Output to check lists
print("Numerical Columns:", num_cols)
print("Categorical Columns:", cat_cols)
print("Selected Columns:", selected_cols)

# %%
cat_cols = ['cicore_id_name', 'is_alert', 'stage_id_name', 'handle_type', 'team_category', 'owner_id_name']

# %%
for col in cat_cols:
    plt.figure(figsize=(10, 6))
    sns.countplot(x=col, hue='cluster', data=df)
    plt.title(f'Distribution of {col} by Cluster')
    plt.xticks(rotation=45)  # Rotate labels if they overlap
    plt.legend(title='Cluster')
    plt.show()
# %%
for col in num_cols:
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='cluster', y=col, data=df)
    plt.title(f'Distribution of {col} by Cluster')
    plt.show()
# %%
for col in num_cols:
    print(f"Descriptive Statistics for {col} by Cluster:")
    display(df.groupby('cluster')[col].describe())
# %%
cluster_samples = {}
selected_cols = [
    'current_duration', 'message_total_count', 'team_id', 'stage_id', 'ticket_type_id', 
    'total_hours_spent', 'solution', 'product_id', 'description_plain', 
    'cicore_id_name', 'is_alert', 'stage_id_name', 'handle_type', 'team_category', 'owner_id_name'
]

# Get unique clusters
clusters = df['cluster'].unique()
# Sample 10 tickets from each cluster, but only include selected columns
for cluster in clusters:
    # Filter df for selected columns and then sample
    cluster_samples[f'cluster_{cluster}'] = df.loc[df['cluster'] == cluster, selected_cols].sample(n=10, random_state=42)

# %%
cluster_samples['cluster_0'].to_clipboard(index=False)
# %%
clusters = df['cluster'].unique()

# Initialize an empty DataFrame to store combined samples
all_cluster_samples = pd.DataFrame()

# Loop through each cluster and sample 10 tickets
for cluster in clusters:
    # Sample 10 tickets from each cluster
    cluster_sample = df[df['cluster'] == cluster].sample(n=10, random_state=42)
    all_cluster_samples = pd.concat([all_cluster_samples, cluster_sample], ignore_index=True)


# %%
