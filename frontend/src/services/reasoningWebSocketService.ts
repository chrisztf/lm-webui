import { useReasoningStore, ReasoningEvent } from '../store/reasoningStore';
import { toast } from 'sonner';
import { logger } from '@/utils/loggingService';
import { websocketOptimizer } from '@/utils/websocketOptimizer';

class ReasoningWebSocketService {
  private static instance: ReasoningWebSocketService;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private reconnectDelay = 1000;
  private url: string = '';
  private sessionId: string = '';
  private conversationId: string = '';
  private provider: string = '';
  private model: string = '';
  private message: string = '';
  private webSearch: boolean = false;
  private searchProvider: string = 'duckduckgo';
  private deepThinkingMode: boolean = false;

  private constructor() {
    // Singleton pattern
  }

  public static getInstance(): ReasoningWebSocketService {
    if (!ReasoningWebSocketService.instance) {
      ReasoningWebSocketService.instance = new ReasoningWebSocketService();
    }
    return ReasoningWebSocketService.instance;
  }

  public connect(url: string, sessionId: string, conversationId: string, provider?: string, model?: string, message?: string, webSearch?: boolean, searchProvider?: string, deepThinkingMode?: boolean) {
    // Prevent reconnecting if already connected to the same session
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      if (this.sessionId === sessionId) {
        logger.websocket('Already connected to session', sessionId);
        return;
      }
      // different session, close existing
      this.ws.close();
    }

    this.url = url;
    this.sessionId = sessionId;
    this.conversationId = conversationId;
    this.provider = provider || 'openai';
    this.model = model || 'gpt-4o-mini';
    this.webSearch = webSearch || false;
    this.searchProvider = searchProvider || 'duckduckgo';
    this.deepThinkingMode = deepThinkingMode || false;
    
    // Reset reconnect attempts on new explicit connection
    this.reconnectAttempts = 0;
    
    if (message) {
      this.message = message;
    }

    try {
      this.ws = new WebSocket(url);
      this.setupWebSocketHandlers();
      useReasoningStore.getState().setConnected(false); // Will be set to true on open
    } catch (error) {
      logger.error('websocket', 'Failed to create WebSocket connection:', error);
      toast.error('Failed to connect to reasoning service', {
        description: 'Please check your network connection and try again.',
        duration: 5000,
      });
      this.handleConnectionError();
    }
  }

  private setupWebSocketHandlers() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      logger.websocket('Reasoning WebSocket connected', { url: this.url, sessionId: this.sessionId });
      this.reconnectAttempts = 0;
      useReasoningStore.getState().setConnected(true);

      // Send initial connection message with selected provider and model
      // Using standard chat format for compatibility with /ws/chat endpoint
      this.send({
        type: 'chat',
        sessionId: this.sessionId,
        message: this.message,
        model: this.model,
        provider: this.provider,
        conversationId: this.conversationId,
        webSearch: this.webSearch,
        searchProvider: this.searchProvider,
        deepThinkingMode: this.deepThinkingMode,
        requires_rag: false, // Reasoning typically doesn't need RAG
        metadata: {
          reasoning_mode: true,
          original_session_id: this.sessionId
        }
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        logger.websocket('Received WebSocket message', { type: message.type, contentLength: message.content?.length || 0 });
        this.handleMessage(message);
      } catch (err) {
        logger.error('websocket', 'Failed to parse WebSocket message', err);
      }
    };

    this.ws.onclose = (event) => {
      logger.websocket('Reasoning WebSocket disconnected', { code: event.code, reason: event.reason, wasClean: event.wasClean });
      useReasoningStore.getState().setConnected(false);

      // Clean up optimizer resources
      websocketOptimizer.cleanup();

      if (!event.wasClean) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          toast.warning('Connection lost, attempting to reconnect...', {
            duration: 3000,
          });
        }
        this.attemptReconnect();
      } else {
        // Clean close - user initiated or normal completion
        if (event.code !== 1000) {
          toast.info('Reasoning session ended', {
            description: event.reason || 'Session completed normally',
            duration: 3000,
          });
        }
      }
    };

    this.ws.onerror = (err) => {
      logger.error('websocket', 'WebSocket error', err);
      useReasoningStore.getState().setConnected(false);
    };
  }

  private handleMessage(message: any) {
    // Handle ModelEvent format from backend
    const event: ReasoningEvent = {
      type: message.type,
      session_id: this.sessionId, // Use current session ID
      timestamp: Date.now() / 1000,
      data: {
        content: message.content || '',
        type: message.type,
        conversationId: this.conversationId, // Include conversation ID for session creation
        ...message.data // Include any additional data
      }
    };

    // Handle through store
    useReasoningStore.getState().handleWebSocketEvent(event);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error('websocket', 'Max reconnection attempts reached');
      toast.error('Failed to reconnect to reasoning service', {
        description: 'Please check your connection and try again later.',
        duration: 8000,
      });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    logger.websocket(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.url && this.sessionId) {
        this.connect(this.url, this.sessionId, this.conversationId, this.provider, this.model, this.message, this.webSearch, this.searchProvider);
      }
    }, delay);
  }

  private handleConnectionError() {
    useReasoningStore.getState().setConnected(false);
    this.attemptReconnect();
  }

  public send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      logger.websocket('Sent WebSocket message', { type: message.type, sessionId: message.sessionId });
    } else {
      logger.warn('websocket', 'WebSocket is not connected, cannot send message:', message);
    }
  }

  public disconnect() {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent further reconnections

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    useReasoningStore.getState().setConnected(false);
  }

  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN || false;
  }

  public getConnectionState(): string {
    if (!this.ws) return 'disconnected';

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'closed';
      default:
        return 'unknown';
    }
  }
}

export const reasoningWebSocketService = ReasoningWebSocketService.getInstance();
