# API Documentation Example

This is an example of how to document APIs for AI agent consumption.

## Overview

This API provides user management functionality.

## Endpoints

### Get User

**Endpoint**: `GET /api/users/{id}`

**Description**: Retrieves a user by their ID

**Parameters**:
- `id` (path parameter): User ID (integer)

**Response**:
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Example Usage**:
```python
import requests

response = requests.get('https://api.example.com/api/users/1')
user = response.json()
print(user['name'])
```

### Create User

**Endpoint**: `POST /api/users`

**Description**: Creates a new user

**Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com"
}
```

**Response**:
```json
{
  "id": 2,
  "name": "Jane Doe",
  "email": "jane@example.com",
  "created_at": "2024-01-02T00:00:00Z"
}
```

**Example Usage**:
```python
import requests

data = {
    "name": "Jane Doe",
    "email": "jane@example.com"
}
response = requests.post('https://api.example.com/api/users', json=data)
new_user = response.json()
```

## Authentication

All API requests require an API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

API requests are limited to 100 requests per minute per API key.
