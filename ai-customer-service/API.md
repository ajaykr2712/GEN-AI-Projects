# API Documentation

## Overview

The AI Customer Service Assistant API provides endpoints for user authentication, AI-powered chat interactions, and customer log management.

**Base URL:** `http://localhost:8000`
**API Version:** `v1`
**Authentication:** JWT Bearer Token

## Authentication Endpoints

### Register User
```http
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string",
  "full_name": "string" // optional
}
```

**Response:**
```json
{
  "id": 1,
  "username": "string",
  "email": "user@example.com",
  "full_name": "string",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Login
```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "jwt-token-string",
  "token_type": "bearer"
}
```

### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "username": "string",
  "email": "user@example.com",
  "full_name": "string",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Chat Endpoints

### Send Message to AI
```http
POST /api/v1/chat/chat
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "message": "How can I reset my password?",
  "conversation_id": 123 // optional, creates new if not provided
}
```

**Response:**
```json
{
  "response": "To reset your password, please follow these steps...",
  "conversation_id": 123,
  "tokens_used": 45,
  "response_time": 1250
}
```

### Get Conversations
```http
GET /api/v1/chat/conversations
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Password Reset Help",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z",
    "messages": []
  }
]
```

### Get Specific Conversation
```http
GET /api/v1/chat/conversations/{conversation_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Password Reset Help",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z",
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "content": "How can I reset my password?",
      "role": "user",
      "timestamp": "2024-01-01T00:00:00Z",
      "tokens_used": 0,
      "response_time": 0
    },
    {
      "id": 2,
      "conversation_id": 1,
      "content": "To reset your password, please follow these steps...",
      "role": "assistant",
      "timestamp": "2024-01-01T00:00:30Z",
      "tokens_used": 45,
      "response_time": 1250
    }
  ]
}
```

### Get FAQs
```http
GET /api/v1/chat/faqs?category={category}
```

**Query Parameters:**
- `category` (optional): Filter by category (account, billing, technical, etc.)

**Response:**
```json
[
  {
    "id": 1,
    "question": "How do I reset my password?",
    "answer": "To reset your password, click on 'Forgot Password'...",
    "category": "account",
    "view_count": 156
  }
]
```

## Customer Logs Endpoints

### Create Customer Log
```http
POST /api/v1/logs/logs
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "Unable to login to account",
  "description": "I keep getting invalid credentials error",
  "log_type": "support",
  "priority": "medium",
  "category": "account"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Unable to login to account",
  "description": "I keep getting invalid credentials error",
  "log_type": "support",
  "status": "open",
  "priority": "medium",
  "category": "account",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null,
  "resolved_at": null
}
```

### Get Customer Logs
```http
GET /api/v1/logs/logs?status={status}&category={category}&priority={priority}&hours={hours}
Authorization: Bearer {token}
```

**Query Parameters:**
- `status` (optional): Filter by status (open, in_progress, resolved, closed)
- `category` (optional): Filter by category
- `priority` (optional): Filter by priority (low, medium, high, urgent)
- `hours` (optional): Timeframe in hours (default: 24)

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Unable to login to account",
    "description": "I keep getting invalid credentials error",
    "log_type": "support",
    "status": "open",
    "priority": "medium",
    "category": "account",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": null,
    "resolved_at": null
  }
]
```

### Update Customer Log
```http
PUT /api/v1/logs/logs/{log_id}
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "status": "resolved",
  "description": "Updated description with resolution details"
}
```

### Get Logs Summary
```http
GET /api/v1/logs/logs/summary?hours={hours}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "timeframe_hours": 24,
  "total_logs": 15,
  "status_breakdown": {
    "open": 8,
    "in_progress": 4,
    "resolved": 3,
    "closed": 0
  },
  "category_breakdown": {
    "technical": 6,
    "billing": 4,
    "account": 3,
    "general": 2
  },
  "priority_breakdown": {
    "urgent": 1,
    "high": 3,
    "medium": 8,
    "low": 3
  }
}
```

### Get Trending Issues (Admin Only)
```http
GET /api/v1/logs/logs/trending?hours={hours}
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "issue": "login",
    "count": 8
  },
  {
    "issue": "password",
    "count": 6
  },
  {
    "issue": "billing",
    "count": 4
  }
]
```

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message description"
}
```

### Common Error Codes

- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Authentication Errors

```json
{
  "detail": "Could not validate credentials"
}
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limiting

- **Default Limit**: 60 requests per minute per user
- **Headers**: Rate limit information in response headers
  - `X-RateLimit-Limit`: Requests per minute limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset time (Unix timestamp)

## Pagination

For endpoints that return lists, pagination is supported:

**Query Parameters:**
- `skip`: Number of items to skip (default: 0)
- `limit`: Maximum number of items to return (default: 100, max: 1000)

**Response Format:**
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 100
}
```

## WebSocket Support (Future)

Real-time chat functionality will be available via WebSocket connections:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/chat');

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'Hello AI!',
  conversation_id: 123
}));

// Receive response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('AI Response:', data.content);
};
```

## SDK Examples

### Python SDK Example

```python
import requests

class AICustomerServiceClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def send_message(self, message, conversation_id=None):
        data = {'message': message}
        if conversation_id:
            data['conversation_id'] = conversation_id
        
        response = requests.post(
            f'{self.base_url}/api/v1/chat/chat',
            json=data,
            headers=self.headers
        )
        return response.json()
    
    def create_log(self, title, description, log_type='inquiry'):
        data = {
            'title': title,
            'description': description,
            'log_type': log_type
        }
        response = requests.post(
            f'{self.base_url}/api/v1/logs/logs',
            json=data,
            headers=self.headers
        )
        return response.json()

# Usage
client = AICustomerServiceClient('http://localhost:8000', 'your-jwt-token')
response = client.send_message('How do I reset my password?')
print(response['response'])
```

### JavaScript SDK Example

```javascript
class AICustomerServiceClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async sendMessage(message, conversationId = null) {
    const data = { message };
    if (conversationId) {
      data.conversation_id = conversationId;
    }

    const response = await fetch(`${this.baseUrl}/api/v1/chat/chat`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(data)
    });

    return await response.json();
  }

  async createLog(title, description, logType = 'inquiry') {
    const data = {
      title,
      description,
      log_type: logType
    };

    const response = await fetch(`${this.baseUrl}/api/v1/logs/logs`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(data)
    });

    return await response.json();
  }
}

// Usage
const client = new AICustomerServiceClient('http://localhost:8000', 'your-jwt-token');
const response = await client.sendMessage('How do I reset my password?');
console.log(response.response);
```
