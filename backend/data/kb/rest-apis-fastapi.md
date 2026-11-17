---
roles: [backend-engineer, ai-ml-engineer]
topics: [REST APIs, FastAPI, HTTP, API design]
---
# REST APIs and FastAPI

A REST API exposes resources over HTTP with standard verbs: GET to read, POST to create, PUT/PATCH to update, DELETE to remove. Good APIs use nouns for resources (/sessions/{id}/answers), return correct status codes (200 ok, 201 created, 400 bad request, 404 not found, 422 validation error, 500 server error), and keep responses consistent.

FastAPI is a Python framework built on Starlette and Pydantic. Request and response shapes are declared as Pydantic models, giving automatic validation, serialisation and OpenAPI documentation. Dependency injection supplies database sessions or the current user to endpoints. Async endpoints (async def) let the server handle many concurrent requests while waiting on I/O.

Production concerns: authentication (JWT or OAuth2), rate limiting, pagination for list endpoints, idempotency for creates that clients may retry, structured error responses, request logging, and versioning (for example, /api/v1) so clients do not break when the API evolves. Input validation must happen at the boundary, never deep in business logic.
