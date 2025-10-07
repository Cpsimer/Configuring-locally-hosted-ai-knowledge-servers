# Coding Standards Example

This is an example of documenting coding standards for AI agent reference.

## Python Standards

### Naming Conventions

- **Functions**: Use `snake_case`
- **Classes**: Use `PascalCase`
- **Constants**: Use `UPPER_SNAKE_CASE`
- **Private methods**: Prefix with underscore `_method_name`

**Good Examples**:
```python
MAX_RETRY_COUNT = 3

class UserService:
    def get_user(self, user_id):
        return self._fetch_from_database(user_id)
    
    def _fetch_from_database(self, user_id):
        # Private helper method
        pass
```

### Documentation

Always include docstrings for functions and classes:

```python
def calculate_total(items, tax_rate=0.1):
    """
    Calculate the total price including tax.
    
    Args:
        items (list): List of item prices
        tax_rate (float): Tax rate as decimal (default: 0.1)
    
    Returns:
        float: Total price including tax
    
    Example:
        >>> calculate_total([10.0, 20.0], 0.1)
        33.0
    """
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
```

### Error Handling

Always handle exceptions appropriately:

```python
def read_file(filepath):
    """Read file with proper error handling."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return None
    except PermissionError:
        print(f"Permission denied: {filepath}")
        return None
```

## JavaScript/TypeScript Standards

### Naming Conventions

- **Variables/Functions**: Use `camelCase`
- **Classes**: Use `PascalCase`
- **Constants**: Use `UPPER_SNAKE_CASE`

**Good Examples**:
```javascript
const MAX_ITEMS = 100;

class UserManager {
    getUserById(userId) {
        return this.fetchUser(userId);
    }
    
    fetchUser(userId) {
        // Implementation
    }
}
```

### Async/Await

Prefer async/await over raw promises:

```javascript
// Good
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch user:', error);
        throw error;
    }
}

// Avoid
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .catch(error => console.error(error));
}
```

## General Best Practices

### Keep Functions Small

Each function should do one thing well:

```python
# Good - Single responsibility
def validate_email(email):
    """Validate email format."""
    return '@' in email and '.' in email.split('@')[1]

def send_email(to, subject, body):
    """Send an email."""
    if not validate_email(to):
        raise ValueError("Invalid email address")
    # Send email logic
    
# Avoid - Multiple responsibilities
def validate_and_send_email(to, subject, body):
    """Validate and send email."""
    if '@' not in to:
        raise ValueError("Invalid email")
    # Send email logic
```

### Use Type Hints (Python 3.5+)

```python
from typing import List, Dict, Optional

def process_users(users: List[Dict[str, str]]) -> Optional[List[str]]:
    """
    Process a list of users and return their names.
    
    Args:
        users: List of user dictionaries
        
    Returns:
        List of user names, or None if users is empty
    """
    if not users:
        return None
    return [user['name'] for user in users]
```

### Comments

- Write self-documenting code when possible
- Use comments to explain "why", not "what"
- Keep comments up-to-date with code changes

```python
# Good - Explains why
# Using exponential backoff to handle rate limiting
retry_delay = base_delay * (2 ** attempt)

# Avoid - Explains what (obvious from code)
# Multiply base_delay by 2 raised to the power of attempt
retry_delay = base_delay * (2 ** attempt)
```
