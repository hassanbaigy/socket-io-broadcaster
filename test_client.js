// Socket.IO client test script
// To run this script: node test_client.js <conversation_id> <api_key>

const { io } = require("socket.io-client");

// Get command line arguments
const args = process.argv.slice(2);
const conversationId = args[0] || 1; // Default to conversation ID 1 if not provided
const apiKey = args[1]; // API key must be provided

if (!apiKey) {
  console.error("Error: API key must be provided as the second argument");
  console.error("Usage: node test_client.js <conversation_id> <api_key>");
  process.exit(1);
}

console.log(`Socket.IO Client Test - Conversation ID: ${conversationId}`);
console.log("Connecting to server...");

// Connect to the Socket.IO server
const socket = io("http://localhost:8001", {
  auth: {
    id: 123, // Example user ID
    isStudent: true, // Example user type (true for student, false for instructor)
  },
  extraHeaders: {
    "X-Tuneup-API-Key": apiKey, // Pass the API key in headers
  },
  transports: ["websocket", "polling"], // Try WebSocket first, fall back to polling
});

// Connection events
socket.on("connect", () => {
  console.log("Connected to server with socket ID:", socket.id);

  // Join a conversation room
  socket.emit(
    "join_conversation",
    { conversation_id: parseInt(conversationId) },
    (response) => {
      if (response.success) {
        console.log(`Successfully joined conversation ${conversationId}`);

        // Setup event listeners after joining
        setupEventListeners();

        // After joining, simulate sending a test message
        setTimeout(() => {
          console.log("Sending a test typing status update...");
          socket.emit("typing_status", {
            conversation_id: parseInt(conversationId),
            user_id: 123,
            is_student: true,
            is_typing: true,
          });
        }, 2000);
      } else {
        console.error("Failed to join conversation:", response);
      }
    }
  );
});

socket.on("connect_error", (error) => {
  console.error("Connection error:", error.message);
  if (error.message.includes("auth")) {
    console.error(
      "This may be due to an invalid API key. Check your API key and try again."
    );
  }
});

socket.on("disconnect", (reason) => {
  console.log("Disconnected from server:", reason);
});

// Set up event listeners for various message types
function setupEventListeners() {
  // Listen for new messages
  socket.on("new_message", (message) => {
    console.log("\n📩 New message received:");
    console.log(
      "  From:",
      message.sender
        ? `User ${message.sender.id} (${
            message.sender.is_student ? "Student" : "Instructor"
          })`
        : "Unknown sender"
    );
    console.log("  Content:", message.content);
    console.log("  Type:", message.type);
    console.log("  Time:", message.sent_at);
    if (message.attachment_url) {
      console.log("  Attachment:", message.attachment_url);
    }
  });

  // Listen for typing status updates
  socket.on("typing_status", (status) => {
    console.log("\n⌨️ Typing status update:");
    const users = status.typing_users || [];

    if (users.length === 0) {
      console.log("  No one is typing");
    } else {
      users.forEach((user) => {
        console.log(
          `  User ${user.user_id} (${
            user.is_student ? "Student" : "Instructor"
          }) is typing...`
        );
      });
    }
  });

  // Listen for message read updates
  socket.on("messages_read", (status) => {
    console.log("\n👁️ Messages read update:");
    console.log(
      `  User ${status.user_id} (${
        status.is_student ? "Student" : "Instructor"
      }) has read messages in conversation ${status.conversation_id}`
    );
    if (status.messages_read) {
      console.log(`  Number of messages read: ${status.messages_read}`);
    }
  });
}

// Handle keyboard input to send test messages
const readline = require("readline");
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

console.log("\n--- Commands ---");
console.log(
  "Type a message and press Enter to send a message to the conversation"
);
console.log("Type 'typing' to send a typing indicator");
console.log("Type 'read' to mark messages as read");
console.log("Type 'exit' to disconnect and exit");
console.log("----------------\n");

rl.on("line", (input) => {
  if (input.toLowerCase() === "exit") {
    console.log("Disconnecting...");
    socket.disconnect();
    rl.close();
    process.exit(0);
  } else if (input.toLowerCase() === "typing") {
    console.log("Sending typing status...");
    socket.emit("typing_status", {
      conversation_id: parseInt(conversationId),
      user_id: 123,
      is_student: true,
      is_typing: true,
    });

    // Automatically stop typing after 5 seconds
    setTimeout(() => {
      console.log("Stopped typing...");
      socket.emit("typing_status", {
        conversation_id: parseInt(conversationId),
        user_id: 123,
        is_student: true,
        is_typing: false,
      });
    }, 5000);
  } else if (input.toLowerCase() === "read") {
    console.log("Marking messages as read...");
    socket.emit("messages_read", {
      conversation_id: parseInt(conversationId),
      user_id: 123,
      is_student: true,
    });
  } else {
    // Send as a message
    console.log("Sending message:", input);

    // Use test_message event for local testing
    socket.emit("test_message", {
      conversation_id: parseInt(conversationId),
      content: input,
      user_id: 123,
    });
  }
});

// Handle process termination
process.on("SIGINT", () => {
  console.log("\nDisconnecting...");
  socket.disconnect();
  rl.close();
  process.exit(0);
});
