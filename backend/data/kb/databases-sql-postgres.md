---
roles: [backend-engineer, ai-ml-engineer, data-science]
topics: [databases, SQL, PostgreSQL, indexing, migrations]
---
# Databases, SQL and PostgreSQL

Relational databases store data in tables with enforced schemas and relationships. SQL queries join tables, filter with WHERE, aggregate with GROUP BY, and sort with ORDER BY. Normalisation reduces duplication; denormalisation is a deliberate tradeoff for read speed.

Indexes make lookups fast by letting the database find rows without scanning the whole table, at the cost of slower writes and storage. The right index depends on query patterns: equality filters, range scans and join keys. EXPLAIN ANALYZE shows whether a query actually uses an index.

Transactions group operations atomically (all succeed or all roll back) and isolation levels control what concurrent transactions can see. ACID guarantees matter for money and state changes; eventual consistency is acceptable for derived data like caches.

PostgreSQL adds JSONB columns, full-text search, and extensions such as pgvector for vector similarity. Schema changes go through migrations (for example, Alembic) so every environment evolves the same way. An ORM like SQLAlchemy maps tables to Python classes but raw SQL is still the right tool for complex reporting queries.
