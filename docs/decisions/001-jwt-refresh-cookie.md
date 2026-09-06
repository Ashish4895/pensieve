# ADR 001: Store JWT refresh tokens in an HTTP-only cookie

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

Pensieve's browser client needs renewable sessions without exposing long-lived
credentials to JavaScript. Access tokens are short-lived and returned in API
responses, while refresh tokens remain valid for seven days.

## Decision

Store the refresh token in a `Secure` (outside development), `HttpOnly`,
`SameSite=Lax` cookie scoped to `/api/v1/auth/`. Return access tokens in JSON.
Require Django CSRF validation for refresh and logout requests, rotate refresh
tokens, and blacklist rotated or logged-out tokens.

## Consequences

- Browser JavaScript cannot read the long-lived refresh token, reducing token
  theft through cross-site scripting.
- Cookie-authenticated refresh and logout requests require CSRF protection.
- API clients must retain cookies and a CSRF token to renew or end a session.
- Cross-site deployments may require coordinated cookie, CORS, and CSRF
  configuration.
