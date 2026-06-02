"""
Superset Configuration
======================
Custom configuration mounted into the Superset container.
Enables cross-filtering, Oracle connections, and Redis caching
(using DB 1 to avoid conflicts with Spring Boot on DB 0).
"""

# Feature flags for enhanced dashboard functionality
FEATURE_FLAGS = {
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "EMBEDDED_SUPERSET": True,
}

# Allow Oracle database connections (required for non-standard DBs)
PREVENT_UNSAFE_DB_CONNECTIONS = False

# Cache configuration using the shared Redis container (DB 1)
# Spring Boot uses DB 0, so we isolate Superset cache on DB 1
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 60,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

# Data cache for query results
DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_data_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

# Filter state cache
FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_filter_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

# Explore form data cache
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_explore_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

# Secret key (override in production via environment variable)
SECRET_KEY = "your-secret-key-change-in-production"

# Enable CORS for embedding in Angular frontend
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": ["http://localhost:4200", "http://frontend:80"],
}

# Allow embedding dashboards in iframes
HTTP_HEADERS = {
    "X-Frame-Options": "ALLOWALL"
}

# Guest token for embedded dashboards (allows unauthenticated embedding)
GUEST_ROLE_NAME = "Public"
GUEST_TOKEN_JWT_SECRET = "your-guest-token-secret-change-in-production"
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
