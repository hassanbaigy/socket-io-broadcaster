"""Chat service for handling chat-related operations."""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import models
from typing import List, Optional, Dict, Any, Union

def get_user_conversations(db: Session, user_id: int, is_student: bool = True) -> List[Dict[str, Any]]:
    """Get all conversations for a user."""
    participant_filter = models.ConversationParticipant.student_id == user_id if is_student else models.ConversationParticipant.instructor_id == user_id
    
    participants = db.query(models.ConversationParticipant).filter(
        and_(
            participant_filter,
            models.ConversationParticipant.left_at.is_(None)
        )
    ).all()
    
    conversations = []
    for participant in participants:
        conv = participant.conversation
        other_participants = []
        
        for p in conv.participants:
            if (is_student and p.student_id != user_id) or (not is_student and p.instructor_id != user_id):
                other_participants.append({
                    "id": p.id,
                    "student_id": p.student_id,
                    "instructor_id": p.instructor_id
                })
        
        # Get latest message
        latest_message = db.query(models.Message).filter(
            models.Message.participant_id.in_([p.id for p in conv.participants])
        ).order_by(models.Message.sent_at.desc()).first()
        
        unread_count = db.query(models.Message).filter(
            and_(
                models.Message.participant_id.in_([p.id for p in conv.participants if (is_student and p.student_id != user_id) or (not is_student and p.instructor_id != user_id)]),
                models.Message.read_at.is_(None)
            )
        ).count()
        
        conversations.append({
            "id": conv.id,
            "type": conv.type,
            "name": conv.name,
            "participants": other_participants,
            "latest_message": {
                "content": latest_message.content if latest_message else None,
                "sent_at": latest_message.sent_at.isoformat() if latest_message else None,
                "type": latest_message.type if latest_message else None
            } if latest_message else None,
            "unread_count": unread_count
        })
    
    return conversations

def get_conversation_messages(db: Session, conversation_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get messages for a conversation."""
    participants = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id
    ).all()
    
    messages = db.query(models.Message).filter(
        models.Message.participant_id.in_([p.id for p in participants])
    ).order_by(models.Message.sent_at.desc()).offset(offset).limit(limit).all()
    
    participant_map = {p.id: p for p in participants}
    
    message_list = []
    for message in messages:
        participant = participant_map.get(message.participant_id)
        message_list.append({
            "id": message.id,
            "content": message.content,
            "type": message.type,
            "sent_at": message.sent_at.isoformat(),
            "read_at": message.read_at.isoformat() if message.read_at else None,
            "sender": {
                "id": participant.id,
                "student_id": participant.student_id,
                "instructor_id": participant.instructor_id
            }
        })
    
    return message_list

def send_message(
    db: Session, 
    conversation_id: int, 
    user_id: int, 
    is_student: bool,
    content: str, 
    message_type: str = "text",
    attachment_url: str = None
) -> Dict[str, Any]:
    """Send a message to a conversation."""
    # Get participant ID
    participant_filter = models.ConversationParticipant.student_id == user_id if is_student else models.ConversationParticipant.instructor_id == user_id
    participant = db.query(models.ConversationParticipant).filter(
        and_(
            models.ConversationParticipant.conversation_id == conversation_id,
            participant_filter
        )
    ).first()
    
    if not participant:
        return None
    
    # Create message
    new_message = models.Message(
        participant_id=participant.id,
        content=content,
        type=message_type,
        attachment_url=attachment_url,
        sent_at=datetime.utcnow()
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return {
        "id": new_message.id,
        "content": new_message.content,
        "type": new_message.type,
        "sent_at": new_message.sent_at.isoformat(),
        "sender": {
            "id": participant.id,
            "student_id": participant.student_id,
            "instructor_id": participant.instructor_id
        }
    }

def mark_messages_as_read(db: Session, conversation_id: int, user_id: int, is_student: bool) -> int:
    """Mark all unread messages in a conversation as read."""
    # Get user's participant record
    participant_filter = models.ConversationParticipant.student_id == user_id if is_student else models.ConversationParticipant.instructor_id == user_id
    user_participant = db.query(models.ConversationParticipant).filter(
        and_(
            models.ConversationParticipant.conversation_id == conversation_id,
            participant_filter
        )
    ).first()
    
    if not user_participant:
        return 0
    
    # Get all participants in this conversation except the user
    other_participants = db.query(models.ConversationParticipant).filter(
        and_(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.id != user_participant.id
        )
    ).all()
    
    # Mark unread messages from other participants as read
    now = datetime.utcnow()
    count = 0
    
    for message in db.query(models.Message).filter(
        and_(
            models.Message.participant_id.in_([p.id for p in other_participants]),
            models.Message.read_at.is_(None)
        )
    ).all():
        message.read_at = now
        count += 1
    
    db.commit()
    return count

def save_typing_status(db: Session, socket_id: str, user_id: int, is_student: bool, is_typing: bool, conversation_id: Optional[int] = None) -> Dict[str, Any]:
    """Update typing status for a user."""
    connection = db.query(models.ActiveConnection).filter(
        models.ActiveConnection.socket_id == socket_id
    ).first()
    
    if not connection:
        connection = models.ActiveConnection(
            socket_id=socket_id,
            user_id=user_id,
            is_student=1 if is_student else 0,
            connected_at=datetime.utcnow()
        )
        db.add(connection)
    
    connection.is_typing = 1 if is_typing else 0
    connection.typing_in_conversation = conversation_id
    connection.last_activity = datetime.utcnow()
    
    db.commit()
    db.refresh(connection)
    
    return {
        "id": connection.id,
        "user_id": connection.user_id,
        "is_student": connection.is_student == 1,
        "is_typing": connection.is_typing == 1,
        "conversation_id": connection.typing_in_conversation
    }

def get_typing_users(db: Session, conversation_id: int) -> List[Dict[str, Any]]:
    """Get users who are currently typing in a conversation."""
    connections = db.query(models.ActiveConnection).filter(
        and_(
            models.ActiveConnection.typing_in_conversation == conversation_id,
            models.ActiveConnection.is_typing == 1
        )
    ).all()
    
    return [
        {
            "user_id": conn.user_id,
            "is_student": conn.is_student == 1
        }
        for conn in connections
    ]

def record_connection(db: Session, socket_id: str, user_id: int, is_student: bool) -> Dict[str, Any]:
    """Record a new socket connection."""
    connection = db.query(models.ActiveConnection).filter(
        models.ActiveConnection.socket_id == socket_id
    ).first()
    
    if not connection:
        connection = models.ActiveConnection(
            socket_id=socket_id,
            user_id=user_id,
            is_student=1 if is_student else 0,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        db.add(connection)
        db.commit()
        db.refresh(connection)
    
    return {
        "socket_id": connection.socket_id,
        "user_id": connection.user_id,
        "is_student": connection.is_student == 1
    }

def remove_connection(db: Session, socket_id: str) -> bool:
    """Remove a socket connection."""
    connection = db.query(models.ActiveConnection).filter(
        models.ActiveConnection.socket_id == socket_id
    ).first()
    
    if connection:
        db.delete(connection)
        db.commit()
        return True
    
    return False 