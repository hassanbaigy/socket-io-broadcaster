# Socket.IO Chat Server

A standalone chat server built with FastAPI and Socket.IO that powers real-time chat functionality for a Laravel application. The server is designed as a simple message broker that receives events from Laravel and broadcasts them to connected clients.

## Features

- Real-time messaging with Socket.IO
- No authentication or database required
- Simple API endpoints for Laravel integration
- Conversation room management
- Typing indicators
- Message read receipts
- API key security for all endpoints

## Server Structure

This repository contains:

- `socket_server.py`: The FastAPI Socket.IO server
- `config.py`: Configuration for the server
- `SocketClient.php`: Laravel service class for interacting with the server
- `MessageController.php`: Example Laravel controller using the SocketClient
- `test_client.js`: Node.js test client for testing the Socket.IO server
- `web_client.html`: Browser-based client for testing the Socket.IO server

## Installation

### Standard Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/tuneup-chat.git
cd tuneup-chat
```

2. Install Python dependencies:

```bash
pip install fastapi uvicorn socketio python-socketio[asgi] python-dotenv
```

3. Create a `.env` file in the root directory:

```
TUNEUP_API_KEY=your_secure_api_key_here
```

4. Run the socket server:

```bash
python socket_server.py
```

The server will start at `http://localhost:8001` by default.

### Docker Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/tuneup-chat.git
cd tuneup-chat
```

2. Set your API key in the environment (optional):

```bash
export TUNEUP_API_KEY=your_secure_api_key_here
```

3. Build and start the containers:

```bash
docker-compose up -d
```

This will start:

- The Socket.IO server at `http://localhost:8001`
- A web server for the client at `http://localhost:3000`

4. View logs:

```bash
docker-compose logs -f
```

5. Stop the containers:

```bash
docker-compose down
```

## Testing with the Included Clients

### Node.js Console Client

1. Install Node.js dependencies:

```bash
npm install
```

2. Run the test client:

```bash
node test_client.js 1 your_api_key_here
```

### Browser Client

1. If running without Docker, start a local web server:

```bash
npx http-server -p 3000
```

2. Open in your browser:
   - If using Docker: `http://localhost:3000/web_client.html`
   - If using local server: `http://localhost:3000/web_client.html`

## Security

The server requires a valid API key for all requests. The API key must be provided in the `X-Tuneup-API-Key` header for all HTTP requests and Socket.IO connections.

Make sure to:

- Store your API key in the `.env` file
- Keep your API key secret
- Use a strong, randomly generated API key in production
- Configure the same API key in both your Laravel application and the Socket.IO server

## Integrating with Laravel

### 1. Add the SocketClient service

Copy `SocketClient.php` to your Laravel project's `app/Services` directory.

### 2. Register the service in your service provider

In your `AppServiceProvider.php`:

```php
public function register()
{
    $this->app->singleton(SocketClient::class, function ($app) {
        return new SocketClient();
    });
}
```

### 3. Add the Socket.IO server URL and API key to your config

In `config/services.php`:

```php
'socket' => [
    'url' => env('SOCKET_SERVER_URL', 'http://localhost:8001'),
    'api_key' => env('TUNEUP_API_KEY', ''),
],
```

Then in your `.env` file:

```
SOCKET_SERVER_URL=http://localhost:8001
TUNEUP_API_KEY=your_secure_api_key_here
```

### 4. Use the SocketClient in your controllers

See `MessageController.php` for examples of how to use the SocketClient service to emit events.

## API Endpoints

The server exposes these main endpoints:

- `POST /emit`: General purpose endpoint to emit any event
- `POST /send-message`: Send a message to a conversation
- `POST /typing-status`: Update a user's typing status
- `POST /mark-read`: Mark messages as read

All endpoints require the `X-Tuneup-API-Key` header.

## Socket.IO Events

Clients can listen for these events:

- `new_message`: Emitted when a new message is sent
- `typing_status`: Emitted when a user starts or stops typing
- `messages_read`: Emitted when a user reads messages

## Client-Side Integration

In your JavaScript frontend, use the Socket.IO client to connect to the server and automatically join conversation rooms from Laravel:

```javascript
// Import Socket.IO client
import { io } from "socket.io-client";
import axios from "axios";

// Connect to the Socket.IO server
const socket = io("http://localhost:8001", {
  auth: {
    id: userId, // User ID from Laravel auth
    isStudent: true, // Or false for instructors
  },
  extraHeaders: {
    "X-Tuneup-API-Key": "your_api_key_here", // API key for security
  },
});

// Fetch conversations from Laravel backend and join rooms
async function joinConversationRooms() {
  try {
    // Get conversations from Laravel endpoint
    const response = await axios.get("/api/conversations", {
      headers: {
        Authorization: `Bearer ${yourAuthToken}`, // Your Laravel auth token
      },
    });

    const conversations = response.data.data;

    // Join each conversation room
    conversations.forEach((conversation) => {
      socket.emit(
        "join_conversation",
        { conversation_id: conversation.id },
        (response) => {
          console.log(`Joined conversation ${conversation.id}:`, response);
        }
      );
    });

    return conversations;
  } catch (error) {
    console.error("Failed to fetch conversations:", error);
    return [];
  }
}

// Call this function when your app initializes
const conversations = await joinConversationRooms();

// Set up event listeners for all conversations
socket.on("new_message", (message) => {
  console.log("New message:", message);
  // Check if message belongs to one of our conversations
  if (conversations.some((conv) => conv.id === message.conversation_id)) {
    // Update UI with new message
    // For example: updateConversationMessages(message);
  }
});

// Listen for typing status updates
socket.on("typing_status", (status) => {
  console.log("Typing status:", status);
  // Update typing indicator UI for the specific conversation
  // For example: updateTypingIndicator(status.conversation_id, status.user_id, status.is_typing);
});

// Listen for message read updates
socket.on("messages_read", (status) => {
  console.log("Messages read:", status);
  // Update read receipts UI for the specific conversation
  // For example: updateReadReceipts(status.conversation_id, status.user_id, status.message_ids);
});

// Rejoin rooms when socket reconnects
socket.on("connect", async () => {
  console.log("Socket reconnected, rejoining rooms...");
  await joinConversationRooms();
});
```

With this approach, your client will:

1. Fetch conversations from your Laravel backend
2. Automatically join Socket.IO rooms for each conversation
3. Listen for events and handle them appropriately based on conversation context
4. Reconnect and rejoin rooms if the connection is lost

## Running in Production

For production use:

1. Configure a proper web server (e.g., Nginx) in front of the Socket.IO server
2. Set up proper CORS settings in `config.py`
3. Consider using a process manager like Supervisor to keep the server running
4. Use HTTPS for all communication to prevent API key exposure
5. Generate a strong, random API key and keep it secure

## License

[MIT License](LICENSE)
