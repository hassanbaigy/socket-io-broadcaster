"""FastAPI Socket.IO chat server."""
import socketio
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import config
import logging
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)                 
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Chat Socket.IO Server",
    description="A FastAPI and Socket.IO server that powers chat functionality with 1-1 and group chat support with typing indicators",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # root_path="/broadcast"ß
)

# Setup CORS - Disabled for development/testing
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=config.CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Security dependency for API key validation
async def verify_api_key(x_tuneup_api_key: str = Header(...)):
    """Verify the API key in request headers"""
    if x_tuneup_api_key != config.API_KEY:
        logger.warning(f"Invalid API key attempt: {x_tuneup_api_key[:4]}...")
        raise HTTPException(
            status_code=403, 
            detail="Invalid or missing API key"
        )
    return x_tuneup_api_key

# Initialize Socket.IO server with custom authentication
async def authenticate_socket(environ):
    """Authenticate Socket.IO connections using API key from headers"""
    # Check if this is a CORS preflight request (OPTIONS method)
    method = environ.get('REQUEST_METHOD', '').upper()
    if method == 'OPTIONS':
        return True  # Allow CORS preflight requests
    
    headers = environ.get('asgi.scope', {}).get('headers', [])
    headers_dict = {k.decode('utf-8').lower(): v.decode('utf-8') 
                    for k, v in headers}
    
    api_key = headers_dict.get('x-tuneup-api-key')
    if api_key != config.API_KEY:
        logger.warning("Socket.IO connection attempt with invalid API key")
        return False
    return True

# Initialize Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    cors_credentials=False,
    logger=True,
    engineio_logger=True,
    auth=authenticate_socket,
)

# Create Socket.IO app
socket_app = socketio.ASGIApp(sio, app)

# Pydantic models for API requests
class MessageData(BaseModel):
    message_id: int = Field(..., description="ID of the message")
    conversation_id: int = Field(..., description="ID of the conversation")
    user_id: int = Field(..., description="ID of the user sending the message")
    is_student: bool = Field(..., description="Whether the user is a student (true) or instructor (false)")
    content: str = Field(..., description="Content of the message")
    type: str = Field("text", description="Type of message (text, image, video, audio)")
    attachment_url: Optional[str] = Field(None, description="URL of any attachment (image, video, audio)")
    
    class Config:
        schema_extra = {
            "example": {
                "message_id": 1,
                "conversation_id": 1,
                "user_id": 123,
                "is_student": True,
                "content": "Hello, how are you?",
                "type": "text",
                "attachment_url": None
            }
        }

class TypingData(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    user_id: int = Field(..., description="ID of the user who is typing")
    is_student: bool = Field(..., description="Whether the user is a student (true) or instructor (false)")
    is_typing: bool = Field(True, description="Whether the user is typing (true) or stopped typing (false)")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "user_id": 123,
                "is_student": True,
                "is_typing": True
            }
        }

class ReadData(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    user_id: int = Field(..., description="ID of the user who read the messages")
    is_student: bool = Field(..., description="Whether the user is a student (true) or instructor (false)")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "user_id": 123,
                "is_student": True
            }
        }

class MessageResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message_id: int = Field(..., description="ID of the message that was sent")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message_id": 456
            }
        }

class SuccessResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True
            }
        }

class EmitEventData(BaseModel):
    event: str = Field(..., description="Name of the event to emit")
    data: Dict[str, Any] = Field(..., description="Data payload to send with the event")
    room: Optional[str] = Field(None, description="Room to emit the event to (optional)")
    
    class Config:
        schema_extra = {
            "example": {
                "event": "new_message",
                "data": {
                    "id": 123,
                    "content": "Hello, how are you?",
                    "sender": {"id": 456, "name": "John Doe"},
                    "conversation_id": 789
                },
                "room": "conversation_789"
            }
        }

# Storage for connected clients (in-memory, no database)
connected_clients = {}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize server on startup."""
    logger.info("Message broker server starting up - no database required")
    logger.info(f"API Key configured: {config.API_KEY[:4]}...")

# REST API endpoints to receive messages from Laravel
@app.post("/send-message", response_model=MessageResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_send_message(data: MessageData):
    """
    Send a new message to a conversation.
    
    This endpoint receives a message from the Laravel backend and broadcasts it to all connected Socket.IO clients
    in the specified conversation room. Use this when a user sends a new message through your Laravel app.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **user_id**: ID of the user sending the message
    - **is_student**: Whether the sender is a student (true) or instructor (false)
    - **content**: Message content
    - **type**: Message type (text, image, video, audio)
    - **attachment_url**: URL to any media attachment (optional)
    
    Returns:
    - **success**: Whether the message was successfully broadcast
    - **message_id**: ID of the sent message
    """
    message = {
        "id": data.message_id, 
        "content": data.content,
        "type": data.type,
        "attachment_url": data.attachment_url,
        "sent_at": datetime.now().isoformat(),  # Use current timestamp
        "sender": {
            "id": data.user_id,
            "is_student": data.is_student
        },
        "conversation_id": data.conversation_id
    }

    logger.info(f"Message: {message}")
    
    room_name = f"conversation_{data.conversation_id}"
    logger.info(f"Broadcasting to room: {room_name}")
    
    # Broadcast message to conversation room
    await sio.emit("new_message", message, room=room_name)
    logger.info(f"Message from Laravel broadcast to conversation {data.conversation_id}")
    
    return {"success": True, "message_id": data.message_id}

@app.post("/typing-status", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_typing_status(data: TypingData):
    """
    Update typing status for a user.
    
    This endpoint receives typing status updates from the Laravel backend and broadcasts them to all connected
    Socket.IO clients in the specified conversation room. Use this when a user starts or stops typing in your Laravel app.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **user_id**: ID of the user who is typing
    - **is_student**: Whether the user is a student (true) or instructor (false)
    - **is_typing**: Whether the user is typing (true) or stopped typing (false)
    
    Returns:
    - **success**: Whether the typing status update was successfully broadcast
    """
    typing_data = {
        "conversation_id": data.conversation_id,
        "typing_users": [
            {
                "user_id": data.user_id,
                "is_student": data.is_student
            }
        ]
    }
    
    # Broadcast typing status
    await sio.emit("typing_status", typing_data, room=f"conversation_{data.conversation_id}")
    logger.info(f"Typing status from Laravel broadcast for conversation {data.conversation_id}")
    
    return {"success": True}

@app.post("/mark-read", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_mark_read(data: ReadData):
    """
    Mark messages as read.
    
    This endpoint receives read status updates from the Laravel backend and broadcasts them to all connected
    Socket.IO clients in the specified conversation room. Use this when a user reads messages in your Laravel app.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **user_id**: ID of the user who read the messages
    - **is_student**: Whether the user is a student (true) or instructor (false)
    
    Returns:
    - **success**: Whether the read status update was successfully broadcast
    """
    read_data = {
        "conversation_id": data.conversation_id,
        "user_id": data.user_id,
        "is_student": data.is_student
    }
    
    # Broadcast read status
    await sio.emit("messages_read", read_data, room=f"conversation_{data.conversation_id}")
    logger.info(f"Read status from Laravel broadcast for conversation {data.conversation_id}")
    
    return {"success": True}

@app.post("/emit", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def emit_event(data: EmitEventData):
    """
    Emit an event to connected Socket.IO clients.
    
    This endpoint receives events from your Laravel backend and broadcasts them to the appropriate
    Socket.IO clients. The event can be sent to all clients or to a specific room.
    
    Parameters:
    - **event**: Name of the event to emit (e.g., new_message)
    - **data**: The data payload to send with the event
    - **room**: (Optional) The room to emit the event to
    
    Returns:
    - **success**: Whether the event was successfully broadcast
    """
    if data.room:
        # Emit to specific room
        await sio.emit(data.event, data.data, room=data.room)
        logger.info(f"Event {data.event} emitted to room {data.room}")
    else:
        # Emit to all clients
        await sio.emit(data.event, data.data)
        logger.info(f"Event {data.event} emitted to all clients")
    
    return {"success": True}

@app.post("/test-broadcast", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def test_broadcast(data: dict):
    """
    Test endpoint to broadcast a message to all connected clients.
    
    This endpoint is for testing purposes only. It broadcasts a test message to all connected clients
    to verify that the Socket.IO server is working properly.
    
    Parameters:
    - **conversation_id**: ID of the conversation to broadcast to
    - **message**: Test message to broadcast
    
    Returns:
    - **success**: Whether the test message was successfully broadcast
    """
    conversation_id = data.get("conversation_id", 1)
    message = data.get("message", "Test message from server")
    
    test_message = {
        "id": 9999,
        "content": message,
        "type": "text",
        "attachment_url": None,
        "sent_at": datetime.now().isoformat(),
        "sender": {
            "id": 0,
            "is_student": False
        },
        "conversation_id": conversation_id
    }
    
    room_name = f"conversation_{conversation_id}"
    
    # Broadcast to specific room
    await sio.emit("new_message", test_message, room=room_name)
    logger.info(f"Test message broadcast to room {room_name}")
    
    # Also broadcast to all clients for testing
    await sio.emit("test_broadcast", {"message": message, "room": room_name})
    logger.info(f"Test broadcast sent to all clients")
    
    return {"success": True}


@app.get("/connected-clients", tags=["System"], dependencies=[Depends(verify_api_key)])
async def get_connected_clients():
    """Get the status of the server."""
        # Also log all connected clients for debugging

    connected_clients_list = []
    for sid, client_info in connected_clients.items():
        connected_clients_list.append({
            "sid": sid,
            "user_id": client_info.get('user_id', 'unknown'),
            "user_type": client_info.get('user_type', 'unknown'),
            "rooms": client_info.get('rooms', [])
        })

    logger.info(f"Total connected clients: {len(connected_clients)}")
    return {"connected_clients": connected_clients_list}

# Socket.IO event handlers
@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    user_data = auth or {}
    user_id = user_data.get("id")
    user_type = "student" if user_data.get("isStudent", True) else "instructor"
    
    connected_clients[sid] = {
        "user_id": user_id,
        "user_type": user_type,
        "rooms": []
    }
    
    logger.info(f"Client connected: {sid} (User ID: {user_id}, Type: {user_type})")
    return True

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    if sid in connected_clients:
        del connected_clients[sid]
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def join_conversation(sid, data):
    """Join a conversation room."""
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return {"error": "Missing conversation_id"}
    
    room_name = f"conversation_{conversation_id}"
    sio.enter_room(sid, room_name)
    
    # Update client's room list
    if sid in connected_clients:
        if room_name not in connected_clients[sid]["rooms"]:
            connected_clients[sid]["rooms"].append(room_name)
    
    logger.info(f"Client {sid} joined room {room_name}")
    logger.info(f"Client {sid} is now in rooms: {connected_clients.get(sid, {}).get('rooms', [])}")
    
    return {"success": True, "conversation_id": conversation_id}

@sio.event
async def leave_room(sid, data):
    """Leave a conversation room."""
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return {"error": "Missing conversation_id"}
    
    room_name = f"conversation_{conversation_id}"
    sio.leave_room(sid, room_name)
    
    # Update client's room list
    if sid in connected_clients and room_name in connected_clients[sid]["rooms"]:
        connected_clients[sid]["rooms"].remove(room_name)
    
    logger.info(f"Client {sid} left room {room_name}")
    
    return {"success": True, "conversation_id": conversation_id}

@sio.on("typing_status")
async def on_typing_status(sid, data):
    """Handle typing status updates from clients."""
    # Don't need to store this, just relay to the room
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return {"error": "Missing conversation_id"}
    
    room = f"conversation_{conversation_id}"
    # Relay to everyone in the room except sender
    await sio.emit("typing_status", data, room=room, skip_sid=sid)
    return {"success": True}

@sio.on("messages_read")
async def on_messages_read(sid, data):
    """Handle messages read updates from clients."""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return {"error": "Missing conversation_id"}
    
    room = f"conversation_{conversation_id}"
    # Relay to everyone in the room except sender
    await sio.emit("messages_read", data, room=room, skip_sid=sid)
    return {"success": True}

@sio.event
async def test_message(sid, data):
    """Test message event for client testing."""
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return {"error": "Missing conversation_id"}
    
    # Create a standardized message format
    message = {
        "id": 999,  # Test message ID
        "content": data.get("content", "Test message"),
        "type": data.get("type", "text"),
        "attachment_url": data.get("attachment_url"),
        "sent_at": datetime.now().isoformat(),
        "sender": {
            "id": data.get("user_id", 0),
            "is_student": data.get("is_student", True)
        },
        "conversation_id": conversation_id
    }
    
    room = f"conversation_{conversation_id}"
    # Broadcast message to the conversation room
    await sio.emit("new_message", message, room=room)
    logger.info(f"Test message sent to conversation {conversation_id}")
    
    return {"success": True, "message": message}

# FastAPI routes
@app.get("/", tags=["System"], dependencies=[Depends(verify_api_key)])
async def root():
    """
    Health check endpoint.
    
    Returns the current status of the chat server.
    """
    # Count connected users by type
    user_counts = {"student": 0, "instructor": 0}
    for client in connected_clients.values():
        user_type = client.get("user_type", "student")
        user_counts[user_type] += 1
        
    return {
        "status": "online", 
        "service": "socket.io-chat-server",
        "connected_users": sum(user_counts.values()),
        "connected_by_type": user_counts,
        "server_time": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "socket_server:socket_app", 
        host=config.HOST, 
        port=config.PORT,
        reload=True,
        log_level="info"
    ) 