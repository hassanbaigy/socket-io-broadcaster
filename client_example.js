/**
 * Socket.IO Chat Client Example with Multi-Tenant Namespace Support
 *
 * This file demonstrates how to connect to the chat server from the Laravel frontend
 * and use the various chat functionality including 1-1 and group chat with typing indicators.
 *
 * Updated to support multi-tenant namespaces - each tenant gets its own namespace isolation.
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
    this.tenantId = null;
    this.namespace = null;
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
   * Connect to the Socket.IO server with tenant namespace support
   * @param {Object} user - User information for authentication
   * @param {number} user.id - User ID
   * @param {number} user.tenant_id - Tenant ID (determines namespace)
   * @param {boolean} user.isStudent - Whether the user is a student (true) or instructor (false)
   * @param {string} user.apiKey - API key for authentication
   */
  connect(user) {
    return new Promise((resolve, reject) => {
      try {
        // Import the socket.io-client library
        const io = require("socket.io-client");

        // Store user info
        this.currentUser = user;
        this.tenantId = user.tenant_id;
        this.namespace = `/tenant_${user.tenant_id}`;

        // Construct the full URL with namespace
        const namespaceUrl = `${this.serverUrl}${this.namespace}`;

        console.log(`Connecting to tenant namespace: ${this.namespace}`);

        // Connect to the Socket.IO server with authentication and namespace
        this.socket = io(namespaceUrl, {
          auth: {
            id: user.id,
            tenant_id: user.tenant_id,
            isStudent: user.isStudent,
          },
          extraHeaders: {
            "X-Tuneup-API-Key": user.apiKey,
          },
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 3000,
        });

        // Set up event listeners
        this.socket.on("connect", () => {
          this.connected = true;
          console.log(`Connected to chat server namespace: ${this.namespace}`);
          console.log(`Socket ID: ${this.socket.id}`);

          if (this.callbacks.onConnect) {
            this.callbacks.onConnect(this.namespace);
          }

          resolve();
        });

        this.socket.on("disconnect", () => {
          this.connected = false;
          console.log(
            `Disconnected from chat server namespace: ${this.namespace}`
          );

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

        this.socket.on("test_broadcast", (data) => {
          console.log("Test broadcast received:", data);
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
      this.tenantId = null;
      this.namespace = null;
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
   * Join a conversation within the tenant namespace
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
            console.error("Error joining conversation:", response.error);
            reject(new Error(response.error));
          } else {
            console.log(
              `Joined conversation ${conversationId} in namespace ${response.namespace}`
            );
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Leave a conversation within the tenant namespace
   * @param {number} conversationId - ID of the conversation to leave
   */
  leaveConversation(conversationId) {
    return new Promise((resolve, reject) => {
      if (!this.connected) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      this.socket.emit(
        "leave_room",
        { conversation_id: conversationId },
        (response) => {
          if (response.error) {
            console.error("Error leaving conversation:", response.error);
            reject(new Error(response.error));
          } else {
            console.log(
              `Left conversation ${conversationId} in namespace ${response.namespace}`
            );
            resolve(response);
          }
        }
      );
    });
  }

  /**
   * Send a test message to a conversation (for testing purposes)
   * @param {Object} message - Message information
   * @param {number} message.conversationId - ID of the conversation
   * @param {string} message.content - Message content
   * @param {string} message.type - Message type (text, image, video, audio)
   * @param {string} message.attachmentUrl - URL of the attachment (if any)
   */
  sendTestMessage(message) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      const messageData = {
        conversation_id: message.conversationId,
        content: message.content || "Test message",
        type: message.type || "text",
        attachment_url: message.attachmentUrl || null,
        user_id: this.currentUser.id,
        is_student: this.currentUser.isStudent,
      };

      this.socket.emit("test_message", messageData, (response) => {
        if (response.error) {
          console.error("Error sending test message:", response.error);
          reject(new Error(response.error));
        } else {
          console.log("Test message sent successfully:", response);
          resolve(response);
        }
      });
    });
  }

  /**
   * Mark messages as read in a conversation
   * @param {number} conversationId - ID of the conversation
   */
  markMessagesAsRead(conversationId) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      const readData = {
        conversation_id: conversationId,
        user_id: this.currentUser.id,
        is_student: this.currentUser.isStudent,
      };

      this.socket.emit("messages_read", readData, (response) => {
        if (response.error) {
          console.error("Error marking messages as read:", response.error);
          reject(new Error(response.error));
        } else {
          console.log("Messages marked as read successfully");
          resolve(response);
        }
      });
    });
  }

  /**
   * Update typing status in a conversation
   * @param {Object} typingData - Typing status information
   * @param {number} typingData.conversationId - ID of the conversation
   * @param {boolean} typingData.isTyping - Whether the user is typing (true) or stopped typing (false)
   */
  updateTypingStatus(typingData) {
    return new Promise((resolve, reject) => {
      if (!this.connected || !this.currentUser) {
        reject(new Error("Not connected to chat server"));
        return;
      }

      const statusData = {
        conversation_id: typingData.conversationId,
        user_id: this.currentUser.id,
        is_student: this.currentUser.isStudent,
        is_typing: typingData.isTyping,
      };

      this.socket.emit("typing_status", statusData, (response) => {
        if (response.error) {
          console.error("Error updating typing status:", response.error);
          reject(new Error(response.error));
        } else {
          console.log("Typing status updated successfully");
          resolve(response);
        }
      });
    });
  }

  /**
   * Get current connection info
   */
  getConnectionInfo() {
    return {
      connected: this.connected,
      namespace: this.namespace,
      tenantId: this.tenantId,
      socketId: this.socket ? this.socket.id : null,
      currentUser: this.currentUser,
    };
  }
}

// Example usage:
//
// const chatClient = new ChatClient("http://localhost:8001");
//
// // Set up event callbacks
// chatClient.setCallbacks({
//   onConnect: (namespace) => {
//     console.log(`Connected to namespace: ${namespace}`);
//   },
//   onDisconnect: () => {
//     console.log("Disconnected from chat server");
//   },
//   onMessage: (message) => {
//     console.log("Received message:", message);
//     // Update your UI with the new message
//   },
//   onTypingStatus: (data) => {
//     console.log("Typing status:", data);
//     // Show/hide typing indicators in your UI
//   },
//   onMessagesRead: (data) => {
//     console.log("Messages read:", data);
//     // Update read receipts in your UI
//   }
// });
//
// // Connect to tenant namespace
// chatClient.connect({
//   id: 123,
//   tenant_id: 1,  // This determines the namespace (/tenant_1)
//   isStudent: true,
//   apiKey: "your-api-key-here"
// }).then(() => {
//   console.log("Connected successfully!");
//
//   // Join a conversation
//   return chatClient.joinConversation(1);
// }).then(() => {
//   console.log("Joined conversation successfully!");
//
//   // Send a test message
//   return chatClient.sendTestMessage({
//     conversationId: 1,
//     content: "Hello from the client!"
//   });
// }).catch((error) => {
//   console.error("Error:", error);
// });

module.exports = ChatClient;
