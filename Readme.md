# Elasticsearch Vector Search Project Proposal

## Overview

This project aims to enhance search functionalities by implementing vector search in Elasticsearch. By using a small index (less than 10,000 entries) to ensure manageable memory requirements, the project focuses on generating dense vectors and applying vector search techniques to improve search relevance and performance.

### Objectives

- **Select a familiar index** for validation, ensuring the model's accuracy over time.
- **Implement model or API** for calculating similarity.
- **Generate dense vector embeddings** to represent data.
- **Apply vector search** using either KNN or ANN methods, with script scoring.
- **Deploy vector search**, including benchmarking and A/B testing.

### Requirements

- Model or API for similarity calculation.
- Vector embeddings generation.
- Vector function for script scoring.

## Project Phases

### Phase 1: Data Collection and Preprocessing
- **Dates:** April 3 - April 7, 2024
- **Activities:** Identify and select the index to be used. Prepare and preprocess data for vector generation.

### Phase 2: Generation of Dense Vectors
- **Dates:** April 8 - April 12, 2024
- **Activities:** Generate dense vectors to represent the data, following guidelines from Elasticsearch documentation (https://www.elastic.co/guide/en/elasticsearch/reference/current/dense-vector.html).

### Phase 3: Applying Vector Search
- **Dates:** April 13 - April 17, 2024
- **Activities:** Decide on the search algorithm (KNN vs. ANN). Implement script scoring with vector function. Optionally, personalize search and integrate search history.

### Phase 4: Deploying Vector Search
- **Dates:** April 18 - April 26, 2024
- **Activities:** Deploy the vector search solution. Conduct benchmark tests and perform A/B testing to evaluate performance and relevance improvements.

## Why Elasticsearch?

Elasticsearch's ability to index vectors allows for efficient and scalable searches, significantly improving search relevance by considering the similarity in vector space.

## Candidates

The primary focus will be on ticket, text, and   security-related indices. 
## Next Steps

Post-project, explore the possibility of implementing hybrid search techniques to further refine search results and user experience.

