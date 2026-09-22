# SPREEGO - Authentication API (Phase 1)

This is the Clean Architecture Authentication API for **SPREEGO**, a social-commerce platform built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

---

## 🏛️ Architecture Overview

The backend follows Clean Architecture principles with clear separation of concerns:

```
backend/
├── src/
│   ├── config/          # App settings, DB engine, JWT security
│   ├── controllers/     # Request/response orchestration layer
│   ├── middlewares/     # Auth dependencies and token validation
│   ├── models/          # SQLAlchemy ORM models (User, Profile, UserSession, OTPCode)
│   ├── repositories/    # Data access layer (User, Profile, Session, OTP)
│   ├── routes/          # FastAPI APIRouters and endpoint definitions
│   ├── services/        # Business logic (AuthService, OTPService, TokenService)
│   ├── utils/           # Shared utilities (logger, mock OTP output)
│   ├── validations/     # Pydantic request/response schemas
│   └── main.py          # FastAPI application entrypoint
├── tests/               # Pytest verification suite (SQLite in-memory)
│   ├── conftest.py      # Fixtures, test client, in-memory DB configuration
│   └── test_auth.py     # Comprehensive tests for all 5 auth endpoints
├── .env.example         # Example environment variables
├── pyproject.toml       # Pytest & project configuration
└── requirements.txt     # Python package dependencies
```

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your database and JWT secret:
```bash
cp .env.example .env
```

### 3. Run the Development Server
```bash
uvicorn src.main:app --reload --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 Running the Verification Suite

Run the full programmatic test suite with `pytest`:
```bash
pytest
```
Or with verbose output and stdout display (to observe mock OTP logs):
```bash
pytest -v -s
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/send-otp` | Generates mock 6-digit OTP & logs to stdout/test output | No |
| `POST` | `/auth/verify-otp` | Verifies OTP, provisions user, returns JWT tokens | No |
| `POST` | `/auth/refresh-token`| Rotates refresh token & issues new access token | No |
| `POST` | `/auth/logout` | Revokes user session(s) | Bearer JWT |
| `GET` | `/auth/me` | Returns current user profile and verification status | Bearer JWT |
| `GET` | `/api/v1/users/{id}` | Public user profile lookup with followers/following counts | No |
| `PATCH`| `/api/v1/users/me` | Updates personal user profile (partial updates, unique username) | Bearer JWT |
| `POST` | `/api/v1/users/{id}/follow` | Follow a user (prevents self/duplicate follow) | Bearer JWT |
| `DELETE`|`/api/v1/users/{id}/follow` | Unfollow a user | Bearer JWT |
| `GET` | `/api/v1/users/{id}/followers`| Paginated list of followers | No |
| `GET` | `/api/v1/users/{id}/following`| Paginated list of users followed | No |
| `GET` | `/health` | Health check endpoint | No |

---

## 🔒 Security Features

1. **Cryptographic OTP Generation**: Uses `secrets.choice` to generate non-predictable 6-digit codes.
2. **Timing-Attack Resistance**: Uses `hmac.compare_digest` for OTP validation.
3. **Attempt Limiting**: Max 5 attempts per OTP code before automatic invalidation.
4. **Expiry Enforcement**: 5-minute default TTL on OTP codes.
5. **Token Revocation & Rotation**: Refresh tokens are single-use / rotated upon refresh, stored in `user_sessions`, and revoked immediately on logout.
6. **Clean Architecture Isolation**: Repositories abstract DB queries, preventing SQL injection via parameterized SQLAlchemy ORM.
