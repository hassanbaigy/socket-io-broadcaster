"""FastAPI Socket.IO chat server."""
import socketio
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response
import config
import logging
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

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
    root_path="/broadcast"
)

# Custom CORS middleware to handle tenant subdomains
class TenantCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        is_allowed = False
        if origin:
            # Check explicit origins
            if origin in config.CORS_ORIGINS:
                is_allowed = True
                logger.info(f"CORS: Origin {origin} allowed (explicit)")
            # Check tenant subdomain pattern
            elif re.match(r'^https://[a-zA-Z0-9-]+\.tuneup\.sageteck\.com$', origin):
                is_allowed = True
                logger.info(f"CORS: Origin {origin} allowed (tenant subdomain)")
            # Allow localhost for development
            elif origin.startswith(('http://localhost', 'http://127.0.0.1')):
                is_allowed = True
                logger.info(f"CORS: Origin {origin} allowed (localhost)")
            else:
                logger.warning(f"CORS: Origin {origin} not allowed")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            if is_allowed:
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
            else:
                return Response(status_code=403)
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to response
        if is_allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response

# Add custom CORS middleware
app.add_middleware(TenantCORSMiddleware)

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

# Function to validate Socket.IO origins
def validate_socketio_origin(origin):
    """Validate if an origin is allowed for Socket.IO connections"""
    if not origin:
        logger.warning("Socket.IO: No origin provided")
        return False
    
    # Check explicit origins
    if origin in config.CORS_ORIGINS:
        logger.info(f"Socket.IO: Origin {origin} allowed (explicit)")
        return True
    
    # Check tenant subdomain pattern
    if re.match(r'^https://[a-zA-Z0-9-]+\.tuneup\.sageteck\.com$', origin):
        logger.info(f"Socket.IO: Origin {origin} allowed (tenant subdomain)")
        return True
    
    # Allow localhost for development
    if origin.startswith(('http://localhost', 'http://127.0.0.1')):
        logger.info(f"Socket.IO: Origin {origin} allowed (localhost)")
        return True
    
    logger.warning(f"Socket.IO: Origin {origin} not allowed")
    return False

# Initialize Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=validate_socketio_origin,
    cors_credentials=True,
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
    tenant_id: int = Field(..., description="ID of the tenant")
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
                "tenant_id": 1,
                "user_id": 123,
                "is_student": True,
                "content": "Hello, how are you?",
                "type": "text",
                "attachment_url": None
            }
        }

class TypingData(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    tenant_id: int = Field(..., description="ID of the tenant")
    user_id: int = Field(..., description="ID of the user who is typing")
    is_student: bool = Field(..., description="Whether the user is a student (true) or instructor (false)")
    is_typing: bool = Field(True, description="Whether the user is typing (true) or stopped typing (false)")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "tenant_id": 1,
                "user_id": 123,
                "is_student": True,
                "is_typing": True
            }
        }

class ReadData(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    tenant_id: int = Field(..., description="ID of the tenant")
    user_id: int = Field(..., description="ID of the user who read the messages")
    is_student: bool = Field(..., description="Whether the user is a student (true) or instructor (false)")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "tenant_id": 1,
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
    tenant_id: int = Field(..., description="ID of the tenant")
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
                "tenant_id": 1,
                "room": "conversation_789"
            }
        }

# Storage for connected clients (in-memory, no database)
# Structure: {namespace: {sid: client_info}}
connected_clients = {}

# Helper function to get tenant room name
def get_tenant_room(tenant_id: int) -> str:
    """Get the room name for a specific tenant"""
    return f"tenant_{tenant_id}"

# Helper function to get conversation room name
def get_conversation_room(tenant_id: int, conversation_id: int) -> str:
    """Get the room name for a conversation within a tenant scope"""
    return f"tenant_{tenant_id}_conversation_{conversation_id}"

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize server on startup."""
    logger.info("Message broker server starting up - no database required")
    logger.info("Multi-tenant namespaces enabled")
    logger.info(f"API Key configured: {config.API_KEY[:4]}...")

# REST API endpoints to receive messages from Laravel
@app.post("/send-message", response_model=MessageResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_send_message(data: MessageData):
    """
    Send a new message to a conversation within a tenant namespace.
    
    This endpoint receives a message from the Laravel backend and broadcasts it to all connected Socket.IO clients
    in the specified conversation room within the tenant's namespace. Use this when a user sends a new message through your Laravel app.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **tenant_id**: ID of the tenant (determines namespace)
    - **user_id**: ID of the user sending the message
    - **is_student**: Whether the sender is a student (true) or instructor (false)
    - **content**: Message content
    - **type**: Message type (text, image, video, audio)
    - **attachment_url**: URL to any media attachment (optional)
    
    Returns:
    - **success**: Whether the message was successfully sent
    - **message_id**: ID of the message that was sent
    """
    # Create a standardized message format
    message = {
        "id": data.message_id,
        "content": data.content,
        "type": data.type,
        "attachment_url": data.attachment_url,
        "sent_at": datetime.now().isoformat(),
        "sender": {
            "id": data.user_id,
            "is_student": data.is_student
        },
        "conversation_id": data.conversation_id,
        "tenant_id": data.tenant_id
    }
    
    # Get the conversation room
    room = get_conversation_room(data.tenant_id, data.conversation_id)
    
    # Broadcast message to the conversation room
    await sio.emit("new_message", message, room=room)
    logger.info(f"Message {data.message_id} sent to conversation {data.conversation_id} in tenant {data.tenant_id}")
    
    return {"success": True, "message_id": data.message_id}

@app.post("/typing-status", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_typing_status(data: TypingData):
    """
    Update typing status for a user in a conversation within a tenant namespace.
    
    This endpoint receives typing status updates from the Laravel backend and broadcasts them to all connected
    Socket.IO clients in the specified conversation room within the tenant's namespace.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **tenant_id**: ID of the tenant (determines namespace)
    - **user_id**: ID of the user who is typing
    - **is_student**: Whether the user is a student (true) or instructor (false)
    - **is_typing**: Whether the user is typing (true) or stopped typing (false)
    
    Returns:
    - **success**: Whether the typing status was successfully updated
    """
    typing_status = {
        "user_id": data.user_id,
        "is_student": data.is_student,
        "is_typing": data.is_typing,
        "conversation_id": data.conversation_id,
        "tenant_id": data.tenant_id
    }
    
    # Get the conversation room
    room = get_conversation_room(data.tenant_id, data.conversation_id)
    
    # Broadcast typing status to the conversation room
    await sio.emit("typing_status", typing_status, room=room)
    logger.info(f"Typing status for user {data.user_id} in conversation {data.conversation_id} in tenant {data.tenant_id}")
    
    return {"success": True}

@app.post("/mark-read", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def api_mark_read(data: ReadData):
    """
    Mark messages as read for a user in a conversation within a tenant namespace.
    
    This endpoint receives read status updates from the Laravel backend and broadcasts them to all connected
    Socket.IO clients in the specified conversation room within the tenant's namespace.
    
    Parameters:
    - **conversation_id**: ID of the conversation
    - **tenant_id**: ID of the tenant (determines namespace)
    - **user_id**: ID of the user who read the messages
    - **is_student**: Whether the user is a student (true) or instructor (false)
    
    Returns:
    - **success**: Whether the read status was successfully updated
    """
    read_status = {
        "user_id": data.user_id,
        "is_student": data.is_student,
        "conversation_id": data.conversation_id,
        "tenant_id": data.tenant_id
    }
    
    # Get the conversation room
    room = get_conversation_room(data.tenant_id, data.conversation_id)
    
    # Broadcast read status to the conversation room
    await sio.emit("messages_read", read_status, room=room)
    logger.info(f"Messages read by user {data.user_id} in conversation {data.conversation_id} in tenant {data.tenant_id}")
    
    return {"success": True}

@app.post("/emit", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def emit_event(data: EmitEventData):
    """
    Emit a custom event to a tenant namespace.
    
    This is a generic endpoint that allows you to emit any custom event to a specific tenant namespace,
    optionally to a specific room within that namespace.
    
    Parameters:
    - **event**: Name of the event to emit
    - **data**: Data payload to send with the event
    - **tenant_id**: ID of the tenant (determines namespace)
    - **room**: Optional room to emit the event to (if not provided, emits to entire namespace)
    
    Returns:
    - **success**: Whether the event was successfully emitted
    """
    # Get the tenant room for broadcasting to all tenant's clients
    tenant_room = get_tenant_room(data.tenant_id)
    
    if data.room:
        # Emit to specific room (e.g., a conversation room)
        await sio.emit(data.event, data.data, room=data.room)
        logger.info(f"Event '{data.event}' emitted to room '{data.room}' in tenant {data.tenant_id}")
    else:
        # Emit to all tenant's clients via tenant room
        await sio.emit(data.event, data.data, room=tenant_room)
        logger.info(f"Event '{data.event}' emitted to all clients in tenant {data.tenant_id}")
    
    return {"success": True}

@app.post("/test-broadcast", response_model=SuccessResponse, tags=["Laravel Integration"], dependencies=[Depends(verify_api_key)])
async def test_broadcast(data: dict):
    """
    Test broadcast endpoint for debugging tenant namespaces.
    
    This endpoint sends a test message to a specific conversation within a tenant namespace.
    Useful for testing the multi-tenant Socket.IO setup.
    
    Parameters:
    - **conversation_id**: ID of the conversation (optional, defaults to 1)
    - **tenant_id**: ID of the tenant (optional, defaults to 1)
    - **message**: Test message content (optional)
    
    Returns:
    - **success**: Whether the test message was successfully broadcast
    """
    conversation_id = data.get("conversation_id", 1)
    tenant_id = data.get("tenant_id", 1)
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
        "conversation_id": conversation_id,
        "tenant_id": tenant_id
    }
    
    # Get tenant and conversation rooms
    tenant_room = get_tenant_room(tenant_id)
    conversation_room = get_conversation_room(tenant_id, conversation_id)
    
    # Broadcast to specific conversation room
    await sio.emit("new_message", test_message, room=conversation_room)
    logger.info(f"Test message broadcast to conversation {conversation_id} in tenant {tenant_id}")
    
    # Also broadcast to all tenant's clients for testing
    await sio.emit("test_broadcast", {
        "message": message,
        "conversation_room": conversation_room,
        "tenant_id": tenant_id
    }, room=tenant_room)
    logger.info(f"Test broadcast sent to all clients in tenant {tenant_id}")
    
    return {"success": True}


@app.get("/connected-clients", tags=["System"], dependencies=[Depends(verify_api_key)])
async def get_connected_clients():
    """Get the status of all connected clients across all tenant namespaces."""
    all_clients = []
    total_clients = 0
    
    for namespace, clients in connected_clients.items():
        for sid, client_info in clients.items():
            all_clients.append({
                "sid": sid,
                "namespace": namespace,
                "user_id": client_info.get('user_id', 'unknown'),
                "tenant_id": client_info.get('tenant_id', 0),
                "user_type": client_info.get('user_type', 'unknown'),
                "rooms": client_info.get('rooms', [])
            })
            total_clients += 1

    logger.info(f"Total connected clients across all namespaces: {total_clients}")
    return {
        "total_connected_clients": total_clients,
        "connected_clients": all_clients,
        "namespaces": list(connected_clients.keys())
    }

# Dynamic namespace event handlers
@sio.on('connect')
async def connect(sid, environ, auth):
    """Handle client connection and tenant room isolation."""
    try:
        # Extract user data from auth
        user_data = auth or {}
        user_id = user_data.get("id")
        tenant_id = user_data.get("tenant_id", 0)
        user_type = "student" if user_data.get("isStudent", True) else "instructor"
        
        # Validate required fields
        if not user_id:
            logger.warning(f"Connection rejected for {sid}: Missing user_id in auth data")
            return False
            
        if not tenant_id or tenant_id <= 0:
            logger.warning(f"Connection rejected for {sid}: Invalid tenant_id ({tenant_id}) in auth data")
            return False
        
        # Initialize storage for root namespace if needed
        if "/" not in connected_clients:
            connected_clients["/"] = {}
        
        # Store client connection info
        connected_clients["/"][sid] = {
            "user_id": user_id,
            "user_type": user_type,
            "tenant_id": tenant_id,
            "rooms": []
        }
        
        # Automatically join the tenant room for isolation
        tenant_room = get_tenant_room(tenant_id)
        sio.enter_room(sid, tenant_room)
        connected_clients["/"][sid]["rooms"].append(tenant_room)
        
        logger.info(f"Client connected: {sid} (User ID: {user_id}, Tenant ID: {tenant_id}, Type: {user_type})")
        logger.info(f"Client {sid} joined tenant room: {tenant_room}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling connection for {sid}: {str(e)}")
        logger.error(f"Auth data received: {auth}")
        return False

@sio.on('disconnect')
async def disconnect(sid):
    """Handle client disconnection."""
    try:
        if sid in connected_clients.get("/", {}):
            client_info = connected_clients["/"][sid]
            tenant_id = client_info["tenant_id"]
            del connected_clients["/"][sid]
            logger.info(f"Client disconnected: {sid} (Tenant ID: {tenant_id})")
    except Exception as e:
        logger.error(f"Error handling disconnect for {sid}: {str(e)}")

@sio.on('join_conversation')
async def join_conversation(sid, data):
    """Join a conversation room within the client's tenant scope."""
    try:
        # Get client info from root namespace
        if sid not in connected_clients.get("/", {}):
            return {"error": "Client not found"}
        
        client_info = connected_clients["/"][sid]
        tenant_id = client_info["tenant_id"]
        
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return {"error": "Missing conversation_id"}
        
        # Join the tenant-scoped conversation room
        room_name = get_conversation_room(tenant_id, conversation_id)
        sio.enter_room(sid, room_name)
        
        # Update client's room list
        if room_name not in client_info["rooms"]:
            client_info["rooms"].append(room_name)
        
        logger.info(f"Client {sid} joined conversation {conversation_id} in tenant {tenant_id}")
        
        return {"success": True, "conversation_id": conversation_id, "room": room_name}
        
    except Exception as e:
        logger.error(f"Error joining conversation for {sid}: {str(e)}")
        return {"error": f"Failed to join conversation: {str(e)}"}

@sio.on('leave_room')
async def leave_room(sid, data):
    """Leave a conversation room."""
    try:
        # Get client info from root namespace
        if sid not in connected_clients.get("/", {}):
            return {"error": "Client not found"}
            
        client_info = connected_clients["/"][sid]
        tenant_id = client_info["tenant_id"]
        
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return {"error": "Missing conversation_id"}
        
        # Get the conversation room name
        room_name = get_conversation_room(tenant_id, conversation_id)
        
        # Don't allow leaving tenant room
        tenant_room = get_tenant_room(tenant_id)
        if room_name == tenant_room:
            return {"error": "Cannot leave tenant room"}
        
        sio.leave_room(sid, room_name)
        
        # Update client's room list
        if room_name in client_info["rooms"]:
            client_info["rooms"].remove(room_name)
        
        logger.info(f"Client {sid} left conversation {conversation_id} in tenant {tenant_id}")
        
        return {"success": True, "conversation_id": conversation_id}
        
    except Exception as e:
        logger.error(f"Error leaving room for {sid}: {str(e)}")
        return {"error": f"Failed to leave room: {str(e)}"}

@sio.on("typing_status")
async def on_typing_status(sid, data):
    """Handle typing status updates from clients."""
    try:
        # Get client info from root namespace
        if sid not in connected_clients.get("/", {}):
            return {"error": "Client not found"}
            
        client_info = connected_clients["/"][sid]
        tenant_id = client_info["tenant_id"]
        
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return {"error": "Missing conversation_id"}
        
        # Get the conversation room
        room = get_conversation_room(tenant_id, conversation_id)
        
        # Add tenant_id to the data if not present
        if "tenant_id" not in data:
            data["tenant_id"] = tenant_id
        
        # Relay to everyone in the room except sender
        sio.emit("typing_status", data, room=room, skip_sid=sid)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error handling typing status for {sid}: {str(e)}")
        return {"error": f"Failed to update typing status: {str(e)}"}

@sio.on("messages_read")
async def on_messages_read(sid, data):
    """Handle messages read updates from clients."""
    try:
        # Get client info from root namespace
        if sid not in connected_clients.get("/", {}):
            return {"error": "Client not found"}
            
        client_info = connected_clients["/"][sid]
        tenant_id = client_info["tenant_id"]
        
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return {"error": "Missing conversation_id"}
        
        # Get the conversation room
        room = get_conversation_room(tenant_id, conversation_id)
        
        # Add tenant_id to the data if not present
        if "tenant_id" not in data:
            data["tenant_id"] = tenant_id
        
        # Relay to everyone in the room except sender
        sio.emit("messages_read", data, room=room, skip_sid=sid)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error handling messages read for {sid}: {str(e)}")
        return {"error": f"Failed to update read status: {str(e)}"}

@sio.on("test_message")
async def test_message(sid, data):
    """Test message event for client testing."""
    try:
        # Get client info from root namespace
        if sid not in connected_clients.get("/", {}):
            return {"error": "Client not found"}
            
        client_info = connected_clients["/"][sid]
        tenant_id = client_info["tenant_id"]
        
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
            "conversation_id": conversation_id,
            "tenant_id": tenant_id
        }
        
        # Get the conversation room
        room = get_conversation_room(tenant_id, conversation_id)
        
        # Broadcast message to the conversation room
        sio.emit("new_message", message, room=room)
        logger.info(f"Test message sent to conversation {conversation_id} in tenant {tenant_id}")
        
        return {"success": True, "message": message}
        
    except Exception as e:
        logger.error(f"Error sending test message for {sid}: {str(e)}")
        return {"error": f"Failed to send test message: {str(e)}"}

# FastAPI routes
@app.get("/", tags=["System"], dependencies=[Depends(verify_api_key)])
async def root():
    """
    Health check endpoint.
    
    Returns the current status of the chat server with multi-tenant namespace information.
    """
    # Count connected users by type and namespace
    namespace_stats = {}
    total_users = 0
    
    for namespace, clients in connected_clients.items():
        user_counts = {"student": 0, "instructor": 0}
        for client in clients.values():
            user_type = client.get("user_type", "student")
            user_counts[user_type] += 1
            total_users += 1
        
        namespace_stats[namespace] = {
            "total_users": sum(user_counts.values()),
            "users_by_type": user_counts
        }
        
    return {
        "status": "online", 
        "service": "socket.io-chat-server",
        "multi_tenant": True,
        "total_connected_users": total_users,
        "namespace_stats": namespace_stats,
        "active_namespaces": list(connected_clients.keys()),
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