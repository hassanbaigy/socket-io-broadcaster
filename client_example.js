/**
 * Socket.IO Chat Client Example
 *
 * This file demonstrates how to connect to the chat server from the Laravel frontend
 * and use the various chat functionality including 1-1 and group chat with typing indicators.
 */

// Import Socket.IO client
// Make sure to include socket.io-client in your package.json
// npm install socket.io-client

class ChatClient {
  constructor(serverUrl) {
    this.socket = null;
    this.serverUrl = serverUrl || "http://localhost:8001";
    this.connected = false;
    this.currentUser = null;
    this.callbacks = {
      onConnect: null,
      onDisconnect: null,
      onError: null,
      onMessage: null,
      onTypingStatus: null,
      onMessagesRead: null,
    };
  }

  /**
   * Connect to the Socket.IO server
   * @param {Object} user - User information for authentication
   * @param {number} user.id - User ID
   * @param {boolean} user.isStudent - Whether the user is a student (true) or instructor (false)
   */
  connect(user) {
    return new Promise((resolve, reject) => {
      try {
        // Import the socket.io-client library
        const io = require("socket.io-client");

        // Store user info
        this.currentUser = user;

        // Connect to the Socket.IO server with authentication
        this.socket = io(this.serverUrl, {
          auth: {
            user_id: user.id,
            is_student: user.isStudent,
          },
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 3000,
        });

        // Set up event listeners
        this.socket.on("connect", () => {
          this.connected = true;
          console.log("Connected to chat server");

          if (this.callbacks.onConnect) {
            this.callbacks.onConnect();
          }

          resolve();
        });

        this.socket.on("disconnect", () => {
          this.connected = false;
          console.log("Disconnected from chat server");

          if (this.callbacks.onDisconnect) {
            this.callbacks.onDisconnect();
          }
        });

        this.socket.on("connect_error", (error) => {
          console.error("Connection error:", error);

          if (this.callbacks.onError) {
            this.callbacks.onError(error);
          }

          reject(error);
        });

        // Set up chat event listeners
        this.socket.on("new_message", (message) => {
          console.log("New message received:", message);

          if (this.callbacks.onMessage) {
            this.callbacks.onMessage(message);
          }
        });

        this.socket.on("typing_status", (data) => {
          console.log("Typing status update:", data);

          if (this.callbacks.onTypingStatus) {
            this.callbacks.onTypingStatus(data);
          }
        });

        this.socket.on("messages_read", (data) => {
          console.log("Messages marked as read:", data);

          if (this.callbacks.onMessagesRead) {
            this.callbacks.onMessagesRead(data);
          }
        });
      } catch (error) {
        console.error("Error connecting to chat server:", error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the Socket.IO server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.currentUser = null;
    }
  }

  /**
   * Set callback functions for events
   * @param {Object} callbacks - Callback functions
   */
  setCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Join a conversation
   * @param {number} conversationId - ID of the conversation to join
   */
  joinConversation(conversationId) {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "join_conversation",
        { conversation_id: conversationId },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Leave a conversation
   * @param {number} conversationId - ID of the conversation to leave
   */
  leaveConversation(conversationId) {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "leave_conversation",
        { conversation_id: conversationId },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Send a message to a conversation
   * @param {Object} message - Message information
   * @param {number} message.conversationId - ID of the conversation
   * @param {string} message.content - Message content
   * @param {string} message.type - Message type (text, image, video, audio)
   * @param {string} message.attachmentUrl - URL of the attachment (if any)
   */
  sendMessage(message) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "send_message",
        {
          conversation_id: message.conversationId,
          content: message.content,
          type: message.type || "text",
          attachment_url: message.attachmentUrl,
          user_id: this.currentUser.id,
          is_student: this.currentUser.isStudent,
        },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Mark messages in a conversation as read
   * @param {number} conversationId - ID of the conversation
   */
  markMessagesAsRead(conversationId) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "mark_read",
        {
          conversation_id: conversationId,
          user_id: this.currentUser.id,
          is_student: this.currentUser.isStudent,
        },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Update typing status
   * @param {Object} typingData - Typing status information
   * @param {number} typingData.conversationId - ID of the conversation
   * @param {boolean} typingData.isTyping - Whether the user is typing
   */
  updateTypingStatus(typingData) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "typing",
        {
          conversation_id: typingData.conversationId,
          user_id: this.currentUser.id,
          is_student: this.currentUser.isStudent,
          is_typing: typingData.isTyping,
        },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Get conversations for the current user
   */
  getConversations() {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "get_conversations",
        {
          user_id: this.currentUser.id,
          is_student: this.currentUser.isStudent,
        },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response.conversations);
          }
        }
      );
    });
  }

  /**
   * Get messages for a conversation
   * @param {Object} params - Query parameters
   * @param {number} params.conversationId - ID of the conversation
   * @param {number} params.limit - Maximum number of messages to return
   * @param {number} params.offset - Offset for pagination
   */
  getMessages(params) {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "get_messages",
        {
          conversation_id: params.conversationId,
          limit: params.limit || 50,
          offset: params.offset || 0,
        },
        (response) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response.messages);
          }
        }
      );
    });
  }
}

// Usage example:

// In your Laravel Blade view or Vue component:
/*
const chatClient = new ChatClient('http://localhost:8001');

// Set up callbacks
chatClient.setCallbacks({
  onMessage: (message) => {
    // Update UI with new message
    console.log('Received message:', message);
  },
  onTypingStatus: (data) => {
    // Update typing indicator UI
    const typingUsers = data.typing_users;
    console.log('Users typing:', typingUsers);
  }
});

// Connect to the chat server
chatClient.connect({
  id: 123, // User ID from Laravel auth
  isStudent: true // Or false for instructors
})
.then(() => {
  // Get user conversations
  return chatClient.getConversations();
})
.then((conversations) => {
  console.log('User conversations:', conversations);
  
  // Join a conversation
  return chatClient.joinConversation(conversations[0].id);
})
.then(() => {
  // Get messages for the conversation
  return chatClient.getMessages({ conversationId: conversations[0].id });
})
.then((messages) => {
  console.log('Conversation messages:', messages);
})
.catch((error) => {
  console.error('Error:', error);
});

// Send a message
chatClient.sendMessage({
  conversationId: 1,
  content: 'Hello world!'
});

// Update typing status - typically on input field changes
const inputField = document.getElementById('message-input');

inputField.addEventListener('focus', () => {
  chatClient.updateTypingStatus({
    conversationId: 1,
    isTyping: true
  });
});

inputField.addEventListener('blur', () => {
  chatClient.updateTypingStatus({
    conversationId: 1,
    isTyping: false
  });
});

// Mark messages as read when conversation is opened
chatClient.markMessagesAsRead(1);

// Disconnect when component is destroyed
// For example, in Vue component's beforeDestroy hook
function beforeDestroy() {
  chatClient.disconnect();
}
*/

// Export the ChatClient class
module.exports = ChatClient;
