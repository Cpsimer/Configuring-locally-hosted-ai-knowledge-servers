# Architecture Documentation Example

This is an example of documenting system architecture for AI agent reference.

## System Overview

This application follows a microservices architecture with the following key components:

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  API Gateway│
└──────┬──────┘
       │
       ├──────────┬──────────┬──────────┐
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Auth    │ │  User    │ │  Order   │ │ Payment  │
│ Service  │ │ Service  │ │ Service  │ │ Service  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │
     └────────────┴────────────┴────────────┘
                  │
                  ▼
            ┌──────────┐
            │ Database │
            │ (PostgreSQL)│
            └──────────┘
```

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Message Queue**: RabbitMQ

### Frontend
- **Framework**: React 18
- **State Management**: Redux Toolkit
- **Styling**: Tailwind CSS
- **Build Tool**: Vite

## Service Communication

### Synchronous Communication
Services communicate via REST APIs:

```python
# Example: User Service calling Order Service
import httpx

async def get_user_orders(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://order-service/api/orders?user_id={user_id}"
        )
        return response.json()
```

### Asynchronous Communication
Services use message queues for event-driven communication:

```python
# Example: Publishing an event when user is created
import pika

def publish_user_created_event(user_id: int, user_email: str):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('rabbitmq')
    )
    channel = connection.channel()
    
    message = {
        "event": "user.created",
        "user_id": user_id,
        "email": user_email
    }
    
    channel.basic_publish(
        exchange='events',
        routing_key='user.created',
        body=json.dumps(message)
    )
```

## Data Flow

### User Registration Flow

1. User submits registration form
2. Frontend sends POST request to API Gateway
3. API Gateway routes to Auth Service
4. Auth Service validates data and creates user
5. User data saved to database
6. `user.created` event published to message queue
7. Email Service consumes event and sends welcome email
8. Response returned to client

## Design Patterns

### Repository Pattern
Used for data access abstraction:

```python
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int):
        pass
    
    @abstractmethod
    async def create(self, user_data: dict):
        pass

class PostgresUserRepository(UserRepository):
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def get_by_id(self, user_id: int):
        query = "SELECT * FROM users WHERE id = $1"
        return await self.db.fetchrow(query, user_id)
    
    async def create(self, user_data: dict):
        query = """
            INSERT INTO users (name, email)
            VALUES ($1, $2)
            RETURNING *
        """
        return await self.db.fetchrow(
            query, user_data['name'], user_data['email']
        )
```

### Service Layer Pattern
Business logic separated from API layer:

```python
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def register_user(self, name: str, email: str):
        # Business logic
        if await self._email_exists(email):
            raise ValueError("Email already registered")
        
        user = await self.user_repo.create({
            'name': name,
            'email': email
        })
        
        await self._send_welcome_email(user)
        return user
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

### Orders Table
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
```

## Caching Strategy

- **User sessions**: Cached in Redis for 24 hours
- **Product catalog**: Cached for 1 hour, invalidated on update
- **User profiles**: Cached for 15 minutes

```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379)

async def get_user_profile(user_id: int):
    # Check cache first
    cache_key = f"user:profile:{user_id}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    user = await user_repo.get_by_id(user_id)
    
    # Cache for 15 minutes
    redis_client.setex(
        cache_key,
        900,  # 15 minutes
        json.dumps(user)
    )
    
    return user
```

## Security Considerations

- **Authentication**: JWT tokens with 1-hour expiration
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: TLS for transport, AES-256 for data at rest
- **Input Validation**: Pydantic models for request validation
- **Rate Limiting**: 100 requests per minute per user

## Deployment

Services deployed using Docker containers on Kubernetes:

```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
      - name: user-service
        image: user-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```
