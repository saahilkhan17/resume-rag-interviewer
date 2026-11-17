---
roles: [backend-engineer, ai-ml-engineer]
topics: [authentication, JWT, OAuth2, security]
---
# Authentication, JWT and API Security

Authentication proves who the caller is; authorization decides what they may do. Passwords are never stored in plain text: they are hashed with a slow, salted algorithm such as bcrypt or Argon2. Secrets and keys live in environment variables or a secret manager, never in source control.

JSON Web Tokens (JWT) carry signed claims (user id, expiry) so a stateless API can verify a caller without a database lookup per request. Access tokens are short-lived; refresh tokens (stored securely, revocable) mint new ones. Tokens must be validated on every request: signature, expiry, issuer and audience. A leaked token is usable until it expires, which is why lifetimes stay short and sensitive actions re-check authorization server-side.

OAuth 2.0 delegates login to an identity provider (Google, GitHub) so the application never handles the user's password. Role-based access control (RBAC) maps users to roles and roles to permissions; checks happen on the server, never only in the UI.

Other basics: HTTPS everywhere, CORS restricted to known origins, rate limiting, input validation, parameterised queries to prevent SQL injection, and never trusting client-supplied data for authorization decisions.
