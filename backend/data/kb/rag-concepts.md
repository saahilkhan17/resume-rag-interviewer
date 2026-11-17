---
roles: [ai-ml-engineer, data-science]
topics: [RAG, retrieval, vector databases, grounding]
---
# Retrieval-Augmented Generation (RAG)

RAG grounds a language model's output in external knowledge. Instead of relying only on what the model memorised during training, the system retrieves relevant passages from a knowledge base at query time and gives them to the model as context, reducing hallucination and letting the model answer about private or recent information.

The pipeline has two phases. Indexing: documents are split into chunks, each chunk is embedded into a vector, and vectors are stored in a vector database with metadata. Retrieval: the user query is embedded the same way, the nearest chunks are found by cosine similarity, and the top-k chunks are passed to the generator.

Chunking strategy matters: chunks must be large enough to preserve meaning but small enough to stay focused. Overlapping chunks and section-aware splitting preserve context across boundaries. Metadata (source, section, role) enables filtering before similarity search.

Retrieval quality decides output quality. Improvements include hybrid search (dense vectors plus keyword/BM25), re-ranking retrieved chunks with a cross-encoder, query rewriting or expansion, and evaluating with hit rate and answer-grounding checks rather than trusting the generator alone.
