# Troubleshooting Guide Example

This is an example of how to document troubleshooting information for AI agent reference.

## Common Issues

### Issue 1: Database Connection Timeout

**Problem**: Application fails to connect to database with timeout error.

**Symptoms**:
```
Error: connection to server at "localhost" (127.0.0.1), port 5432 failed: timeout expired
```

**Possible Causes**:
1. Database server is not running
2. Firewall blocking port 5432
3. Wrong connection string
4. Network connectivity issues

**Solutions**:

#### Check if database is running
```bash
# For PostgreSQL
sudo systemctl status postgresql

# Check if port is listening
netstat -an | grep 5432
```

#### Verify connection string
```python
# Check your connection string format
DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"

# Test connection
import psycopg2
try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

#### Adjust timeout settings
```python
# Increase connection timeout
import psycopg2
conn = psycopg2.connect(
    DATABASE_URL,
    connect_timeout=30  # Increase from default 10 seconds
)
```

### Issue 2: API Returns 401 Unauthorized

**Problem**: API calls fail with 401 status code.

**Symptoms**:
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

**Possible Causes**:
1. Missing Authorization header
2. Expired token
3. Invalid token format
4. Wrong API key

**Solutions**:

#### Verify token is included
```python
import requests

headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.example.com/users",
    headers=headers
)
```

#### Check token expiration
```python
import jwt
from datetime import datetime

def check_token_expiry(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded.get('exp')
        
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            now = datetime.now()
            
            if now > exp_date:
                print(f"Token expired on {exp_date}")
                return False
            else:
                print(f"Token valid until {exp_date}")
                return True
    except Exception as e:
        print(f"Error checking token: {e}")
        return False
```

#### Refresh token
```python
def refresh_auth_token(refresh_token):
    response = requests.post(
        "https://api.example.com/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    if response.status_code == 200:
        new_token = response.json()["access_token"]
        return new_token
    else:
        raise Exception("Failed to refresh token")
```

### Issue 3: Memory Leak in Long-Running Process

**Problem**: Application memory usage increases over time.

**Symptoms**:
- Gradual increase in memory consumption
- Eventually leads to out-of-memory errors
- Process becomes slow over time

**Debugging Steps**:

#### Profile memory usage
```python
import tracemalloc
import time

# Start tracking
tracemalloc.start()

# Your code here
def potentially_leaky_function():
    data = []
    for i in range(1000000):
        data.append({"id": i, "value": f"item_{i}"})
    # Forgot to clear data or return causes it to stay in memory

# Take snapshots
snapshot1 = tracemalloc.take_snapshot()
potentially_leaky_function()
snapshot2 = tracemalloc.take_snapshot()

# Compare
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:10]:
    print(stat)
```

#### Common causes and fixes

**Cause 1: Unclosed connections**
```python
# Bad - connection not closed
def get_user(user_id):
    conn = database.connect()
    user = conn.execute("SELECT * FROM users WHERE id = ?", user_id)
    return user

# Good - using context manager
def get_user(user_id):
    with database.connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", user_id)
        return user
```

**Cause 2: Circular references**
```python
# Bad - circular reference
class Node:
    def __init__(self, value):
        self.value = value
        self.parent = None
        self.children = []
    
    def add_child(self, child):
        child.parent = self  # Creates circular reference
        self.children.append(child)

# Good - use weak references
import weakref

class Node:
    def __init__(self, value):
        self.value = value
        self._parent = None
        self.children = []
    
    @property
    def parent(self):
        return self._parent() if self._parent else None
    
    @parent.setter
    def parent(self, parent):
        self._parent = weakref.ref(parent) if parent else None
    
    def add_child(self, child):
        child.parent = self
        self.children.append(child)
```

### Issue 4: Slow API Response Times

**Problem**: API endpoints taking too long to respond.

**Symptoms**:
- Response times > 3 seconds
- Timeouts from clients
- Poor user experience

**Diagnostic Tools**:

```python
import time
from functools import wraps

def timing_decorator(func):
    """Measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

@timing_decorator
def slow_endpoint():
    # Your endpoint logic
    pass
```

**Common Solutions**:

#### Add caching
```python
from functools import lru_cache
import redis

# Simple in-memory cache
@lru_cache(maxsize=1000)
def get_user_profile(user_id):
    # Expensive database query
    return database.query(f"SELECT * FROM users WHERE id = {user_id}")

# Redis cache
redis_client = redis.Redis(host='localhost', port=6379)

def get_cached_user(user_id):
    # Check cache
    cached = redis_client.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    
    # Fetch and cache
    user = database.query(f"SELECT * FROM users WHERE id = {user_id}")
    redis_client.setex(f"user:{user_id}", 300, json.dumps(user))
    return user
```

#### Optimize database queries
```python
# Bad - N+1 query problem
def get_users_with_orders():
    users = User.query.all()
    for user in users:
        user.orders = Order.query.filter_by(user_id=user.id).all()
    return users

# Good - use join or eager loading
def get_users_with_orders():
    users = User.query.join(Order).all()
    return users

# Or with SQLAlchemy
from sqlalchemy.orm import joinedload

def get_users_with_orders():
    users = User.query.options(joinedload(User.orders)).all()
    return users
```

#### Add pagination
```python
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/users")
async def get_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    offset = (page - 1) * per_page
    users = await database.fetch_all(
        "SELECT * FROM users LIMIT :limit OFFSET :offset",
        values={"limit": per_page, "offset": offset}
    )
    return {
        "users": users,
        "page": page,
        "per_page": per_page
    }
```

## Debugging Techniques

### Enable Verbose Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def process_data(data):
    logger.debug(f"Processing data: {data}")
    try:
        result = transform(data)
        logger.info(f"Successfully processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing data: {e}", exc_info=True)
        raise
```

### Use Interactive Debugger

```python
# Add breakpoint in code
def complex_function(data):
    processed = initial_processing(data)
    
    # Execution will pause here
    import pdb; pdb.set_trace()
    
    result = further_processing(processed)
    return result

# Python 3.7+ breakpoint
def complex_function(data):
    processed = initial_processing(data)
    breakpoint()  # Built-in debugger
    result = further_processing(processed)
    return result
```

## Getting Help

If you've tried these solutions and still have issues:

1. **Check logs**: Look for error messages and stack traces
2. **Search existing issues**: See if others have reported similar problems
3. **Create minimal reproduction**: Isolate the problem in a simple example
4. **Ask for help**: Provide context, error messages, and what you've tried

## Prevention

### Code Review Checklist
- [ ] All resources properly closed (connections, files, etc.)
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Performance considerations addressed
- [ ] Security best practices followed

### Testing
- Unit tests for individual functions
- Integration tests for workflows
- Load testing for performance
- Security testing for vulnerabilities
