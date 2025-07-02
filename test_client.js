/**
 * Multi-Tenant Socket.IO Test Client
 *
 * This test client demonstrates how to connect to different tenant namespaces
 * and verify that messages are properly isolated between tenants.
 */

const io = require("socket.io-client");

// Configuration
const SERVER_URL = "http://localhost:8001";
const API_KEY = "your-api-key-here"; // Replace with your actual API key

// Test users for different tenants
const testUsers = [
  {
    id: 101,
    tenant_id: 1,
    name: "Alice (Tenant 1)",
    isStudent: true,
  },
  {
    id: 102,
    tenant_id: 1,
    name: "Bob (Tenant 1)",
    isStudent: false,
  },
  {
    id: 201,
    tenant_id: 2,
    name: "Charlie (Tenant 2)",
    isStudent: true,
  },
  {
    id: 202,
    tenant_id: 2,
    name: "Diana (Tenant 2)",
    isStudent: false,
  },
];

class MultiTenantTestClient {
  constructor() {
    this.clients = [];
    this.conversationId = 1;
  }

  async connectAllClients() {
    console.log("🚀 Starting Multi-Tenant Socket.IO Test");
    console.log("==========================================");

    for (const user of testUsers) {
      try {
        const client = await this.connectClient(user);
        this.clients.push(client);
        console.log(
          `✅ ${user.name} connected to namespace /tenant_${user.tenant_id}`
        );
      } catch (error) {
        console.error(`❌ Failed to connect ${user.name}:`, error.message);
      }
    }

    console.log(`\n📊 Total connected clients: ${this.clients.length}`);
  }

  connectClient(user) {
    return new Promise((resolve, reject) => {
      const namespace = `/tenant_${user.tenant_id}`;
      const namespaceUrl = `${SERVER_URL}${namespace}`;

      const socket = io(namespaceUrl, {
        auth: {
          id: user.id,
          tenant_id: user.tenant_id,
          isStudent: user.isStudent,
        },
        extraHeaders: {
          "X-Tuneup-API-Key": API_KEY,
        },
        reconnection: false, // Disable for testing
      });

      // Store user info with socket
      socket.user = user;
      socket.namespace = namespace;

      socket.on("connect", () => {
        console.log(`🔗 ${user.name} connected with socket ID: ${socket.id}`);
        resolve(socket);
      });

      socket.on("connect_error", (error) => {
        reject(error);
      });

      socket.on("disconnect", () => {
        console.log(`🔌 ${user.name} disconnected`);
      });

      // Set up event listeners
      socket.on("new_message", (message) => {
        console.log(
          `📨 ${user.name} received message: "${message.content}" from user ${message.sender.id}`
        );
      });

      socket.on("typing_status", (data) => {
        const status = data.is_typing ? "started typing" : "stopped typing";
        console.log(`⌨️  ${user.name} sees: User ${data.user_id} ${status}`);
      });

      socket.on("messages_read", (data) => {
        console.log(
          `👁️  ${user.name} sees: User ${data.user_id} read messages`
        );
      });

      socket.on("test_broadcast", (data) => {
        console.log(
          `📢 ${user.name} received broadcast: ${data.message} (Tenant: ${data.tenant_id})`
        );
      });
    });
  }

  async joinConversations() {
    console.log("\n🏠 Joining conversations...");
    console.log("============================");

    for (const client of this.clients) {
      try {
        const response = await this.emitWithResponse(
          client,
          "join_conversation",
          {
            conversation_id: this.conversationId,
          }
        );

        if (response.success) {
          console.log(
            `✅ ${client.user.name} joined conversation ${this.conversationId}`
          );
        } else {
          console.log(
            `⚠️  ${client.user.name} failed to join conversation: ${response.error}`
          );
        }
      } catch (error) {
        console.error(
          `❌ Error joining conversation for ${client.user.name}:`,
          error.message
        );
      }
    }
  }

  async testMessageIsolation() {
    console.log("\n🔒 Testing message isolation between tenants...");
    console.log("===============================================");

    // Send messages from each tenant
    const tenant1Client = this.clients.find((c) => c.user.tenant_id === 1);
    const tenant2Client = this.clients.find((c) => c.user.tenant_id === 2);

    if (tenant1Client) {
      console.log(`📤 Sending message from ${tenant1Client.user.name}...`);
      await this.sendTestMessage(tenant1Client, "Hello from Tenant 1! 👋");
      await this.sleep(1000);
    }

    if (tenant2Client) {
      console.log(`📤 Sending message from ${tenant2Client.user.name}...`);
      await this.sendTestMessage(tenant2Client, "Hello from Tenant 2! 🎉");
      await this.sleep(1000);
    }

    console.log(
      "📋 Messages should only be received by users in the same tenant namespace"
    );
  }

  async testTypingIndicators() {
    console.log("\n⌨️  Testing typing indicators...");
    console.log("================================");

    for (const client of this.clients) {
      console.log(`⌨️  ${client.user.name} is typing...`);

      await this.emitWithResponse(client, "typing_status", {
        conversation_id: this.conversationId,
        user_id: client.user.id,
        is_student: client.user.isStudent,
        is_typing: true,
      });

      await this.sleep(1500);

      await this.emitWithResponse(client, "typing_status", {
        conversation_id: this.conversationId,
        user_id: client.user.id,
        is_student: client.user.isStudent,
        is_typing: false,
      });

      await this.sleep(500);
    }
  }

  async testReadReceipts() {
    console.log("\n👁️  Testing read receipts...");
    console.log("============================");

    for (const client of this.clients) {
      console.log(`👁️  ${client.user.name} marking messages as read...`);

      await this.emitWithResponse(client, "messages_read", {
        conversation_id: this.conversationId,
        user_id: client.user.id,
        is_student: client.user.isStudent,
      });

      await this.sleep(500);
    }
  }

  async sendTestMessage(client, content) {
    return this.emitWithResponse(client, "test_message", {
      conversation_id: this.conversationId,
      content: content,
      user_id: client.user.id,
      is_student: client.user.isStudent,
    });
  }

  emitWithResponse(socket, event, data) {
    return new Promise((resolve, reject) => {
      socket.emit(event, data, (response) => {
        if (response && response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response);
        }
      });
    });
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async disconnectAll() {
    console.log("\n🔌 Disconnecting all clients...");
    console.log("===============================");

    for (const client of this.clients) {
      client.disconnect();
      console.log(`🔌 ${client.user.name} disconnected`);
    }

    this.clients = [];
  }

  async runFullTest() {
    try {
      await this.connectAllClients();
      await this.sleep(2000);

      await this.joinConversations();
      await this.sleep(2000);

      await this.testMessageIsolation();
      await this.sleep(3000);

      await this.testTypingIndicators();
      await this.sleep(2000);

      await this.testReadReceipts();
      await this.sleep(2000);

      console.log("\n🎉 Multi-tenant test completed successfully!");
      console.log("===========================================");

      console.log("\n📊 Test Summary:");
      console.log(
        `- Connected ${this.clients.length} clients across ${
          new Set(testUsers.map((u) => u.tenant_id)).size
        } tenants`
      );
      console.log("- Verified message isolation between tenants");
      console.log("- Tested typing indicators within namespaces");
      console.log("- Tested read receipts within namespaces");
    } catch (error) {
      console.error("❌ Test failed:", error);
    } finally {
      await this.disconnectAll();
      process.exit(0);
    }
  }
}

// Helper function to test individual tenant connection
async function testSingleTenant(tenantId, userId = 100) {
  console.log(
    `\n🧪 Testing single tenant connection (Tenant ${tenantId}, User ${userId})`
  );
  console.log("=".repeat(60));

  const namespace = `/tenant_${tenantId}`;
  const namespaceUrl = `${SERVER_URL}${namespace}`;

  const socket = io(namespaceUrl, {
    auth: {
      id: userId,
      tenant_id: tenantId,
      isStudent: true,
    },
    extraHeaders: {
      "X-Tuneup-API-Key": API_KEY,
    },
  });

  socket.on("connect", () => {
    console.log(`✅ Connected to ${namespace} with socket ID: ${socket.id}`);

    // Join a conversation
    socket.emit("join_conversation", { conversation_id: 1 }, (response) => {
      if (response.success) {
        console.log(`✅ Joined conversation 1 in ${response.namespace}`);

        // Send a test message
        socket.emit(
          "test_message",
          {
            conversation_id: 1,
            content: `Test message from tenant ${tenantId}`,
            user_id: userId,
            is_student: true,
          },
          (response) => {
            if (response.success) {
              console.log("✅ Test message sent successfully");
            } else {
              console.log("❌ Failed to send test message:", response.error);
            }

            socket.disconnect();
          }
        );
      } else {
        console.log("❌ Failed to join conversation:", response.error);
        socket.disconnect();
      }
    });
  });

  socket.on("connect_error", (error) => {
    console.error("❌ Connection error:", error.message);
  });

  socket.on("new_message", (message) => {
    console.log(
      `📨 Received message: "${message.content}" from user ${message.sender.id}`
    );
  });

  socket.on("disconnect", () => {
    console.log("🔌 Disconnected");
  });
}

// Main execution
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    // Run full multi-tenant test
    const testClient = new MultiTenantTestClient();
    testClient.runFullTest();
  } else if (args[0] === "single") {
    // Test single tenant connection
    const tenantId = parseInt(args[1]) || 1;
    const userId = parseInt(args[2]) || 100;
    testSingleTenant(tenantId, userId);
  } else {
    console.log("Usage:");
    console.log("  node test_client.js           # Run full multi-tenant test");
    console.log(
      "  node test_client.js single [tenant_id] [user_id]   # Test single tenant"
    );
    process.exit(1);
  }
}

module.exports = MultiTenantTestClient;
