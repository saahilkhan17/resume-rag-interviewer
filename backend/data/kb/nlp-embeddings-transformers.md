---
roles: [ai-ml-engineer, data-science]
topics: [NLP, embeddings, transformers, attention]
---
# NLP, Embeddings and Transformers

Text must become numbers before a model can use it. Early methods used one-hot vectors or TF-IDF bag-of-words, which ignore word order and meaning. Word embeddings (Word2Vec, GloVe) learn dense vectors where similar words sit close together, capturing semantic relationships.

The transformer replaced recurrence with self-attention: each token attends to all other tokens in the sequence, weighting them by relevance. Multi-head attention learns several relevance patterns in parallel, and positional encodings inject word order. This parallel structure trains far faster than recurrent networks on long sequences.

Pre-trained language models (BERT for understanding, GPT-style models for generation) learn general language patterns from large corpora and are then fine-tuned on small task datasets. Prompting and in-context learning let large models perform tasks with few or no labelled examples.

Practical concerns: tokenization (subword methods like BPE handle rare words), context-window limits, hallucination when generating, and evaluation that measures real task performance rather than fluency alone.
