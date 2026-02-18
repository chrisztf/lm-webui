export interface ConversationUpdate {
  type: 'conversation_updated' | 'new_message' | 'conversation_deleted';
  conversation_id: string;
  title?: string;
  timestamp: number;
  user_id?: number;
}

export interface ConversationWebSocketConfig {
  onConversationUpdate?: (update: ConversationUpdate) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Error) => void;
}

export class ConversationWebSocketService {
  private websocket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private config: ConversationWebSocketConfig;

  constructor(config: ConversationWebSocketConfig = {}) {
    this.config = config;
  }

  updateConfig(config: Partial<ConversationWebSocketConfig>): void {
    this.config = { ...this.config, ...config };
  }

  async connect(): Promise<void> {
    if (this.isConnecting || this.websocket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connecting or connected');
      return;
    }

    this.isConnecting = true;

    try {
      // Get backend URL from environment or use default
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      
      // Parse backend URL to get host and protocol
      const backendUrlObj = new URL(backendUrl);
      const protocol = backendUrlObj.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = backendUrlObj.host;
      const wsUrl = `${protocol}//${host}/ws/chat`;

      console.log('🔌 Connecting to conversation WebSocket:', wsUrl);

      this.websocket = new WebSocket(wsUrl);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.websocket!.onopen = () => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;

          console.log('✅ Conversation WebSocket connected');

          // Start heartbeat
          this.startHeartbeat();

          // Notify connection
          if (this.config.onConnected) {
            this.config.onConnected();
          }

          resolve();
        };

        this.websocket!.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', event.data, error);
          }
        };

        this.websocket!.onclose = (event) => {
          console.log('🔌 Conversation WebSocket disconnected:', event.code, event.reason);
          this.isConnecting = false;
          this.stopHeartbeat();

          // Notify disconnection
          if (this.config.onDisconnected) {
            this.config.onDisconnected();
          }

          // Attempt reconnection if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.websocket!.onerror = (error) => {
          console.error('❌ Conversation WebSocket error:', error);
          this.isConnecting = false;
          this.stopHeartbeat();

          if (this.config.onError) {
            this.config.onError(new Error('WebSocket connection error'));
          }

          reject(error);
        };
      });
    } catch (error) {
      this.isConnecting = false;
      throw error;
    }
  }

  private handleMessage(data: any): void {
    // Check if this is a conversation update message
    if (data.type === 'conversation_updated') {
      const update: ConversationUpdate = {
        type: 'conversation_updated',
        conversation_id: data.conversation_id,
        title: data.title,
        timestamp: data.timestamp,
        user_id: data.user_id
      };

      console.log('📡 Received conversation update:', update);

      if (this.config.onConversationUpdate) {
        this.config.onConversationUpdate(update);
      }
    }
    // Handle other message types as needed
    else if (data.type === 'heartbeat_response') {
      // Heartbeat response, do nothing
    } else {
      console.log('📡 Received WebSocket message:', data);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`🔄 Attempting reconnection in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      if (this.websocket?.readyState !== WebSocket.OPEN) {
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat(); // Clear any existing heartbeat

    this.heartbeatInterval = setInterval(() => {
      if (this.websocket?.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({ action: 'heartbeat' }));
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect(): void {
    console.log('🔌 Disconnecting conversation WebSocket');

    this.stopHeartbeat();

    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect');
      this.websocket = null;
    }

    this.isConnecting = false;
  }

  get isConnected(): boolean {
    return this.websocket?.readyState === WebSocket.OPEN;
  }

  get status(): 'disconnected' | 'connecting' | 'connected' {
    if (!this.websocket) return 'disconnected';
    if (this.isConnecting) return 'connecting';
    if (this.websocket.readyState === WebSocket.OPEN) return 'connected';
    return 'disconnected';
  }
}

// Singleton instance for global use
let globalInstance: ConversationWebSocketService | null = null;

export function getConversationWebSocketService(config?: ConversationWebSocketConfig): ConversationWebSocketService {
  if (!globalInstance) {
    globalInstance = new ConversationWebSocketService(config);
  }
  
  // Update config if provided
  if (config) {
    globalInstance.updateConfig(config);
  }
  
  return globalInstance;
}
