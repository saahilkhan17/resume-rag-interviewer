---
roles: [backend-engineer, ai-ml-engineer]
topics: [async processing, queues, caching, Redis, scalability]
---
# Async Processing, Queues and Caching

Synchronous request handling blocks the response until all work finishes. Slow work (sending email, running an ML model, generating a report) belongs in background jobs: the API returns immediately with a job id, and a worker processes the job from a queue (Redis, RabbitMQ, SQS) and updates its status.

Queues decouple producers from consumers, absorb traffic spikes, and let work retry with backoff when it fails. Idempotent job handlers are essential because queues may deliver a job more than once. Dead-letter queues hold jobs that keep failing so they can be inspected instead of retried forever.

Caching trades freshness for speed. Redis commonly stores session data, rate-limit counters and hot query results with a time-to-live. Cache invalidation is the hard part: write-through, cache-aside and TTL expiry are the standard patterns. Never cache per-user sensitive data under a shared key.

Scaling reads: database replicas, read-only queries against replicas, and pagination. Scaling writes: connection pooling, batching, and partitioning hot tables. Measure before optimising: latency percentiles and error rates per endpoint show where the real bottleneck is.
