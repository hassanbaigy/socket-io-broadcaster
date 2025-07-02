"""
Main entry point for the FastAPI Socket.IO Chat Server.
"""
import uvicorn
import config
from fastapi import APIRouter

if __name__ == "__main__":
    print(f"Starting chat server at {config.HOST}:{config.PORT}")
    print("Database connections are disabled for testing purposes.")
    
    uvicorn.run(
        "socket_server:socket_app", 
        host=config.HOST, 
        port=config.PORT,
        reload=True,
        log_level="info"
    ) 
