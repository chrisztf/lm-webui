import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { logger, LogLevel } from '@/utils/loggingService';
import { websocketOptimizer, TokenBatch } from '@/utils/websocketOptimizer';
import { isTokenBatchingEnabled, getBatchSize } from '@/store/settingsStore';

export interface ReasoningSession {
  sessionId: string;
  conversationId: string;
  content: string; // Raw CoT text
  isActive: boolean;
  startTime: string;
  endTime?: string;
  metrics: ReasoningMetrics;
  metadata?: any;
}

export interface ReasoningMetrics {
  duration: number; // in seconds
  tokenCount: number;
  updateCount: number;
}

export interface ReasoningEvent {
  type: string;
  session_id: string;
  timestamp: number;
  data: any;
}

interface ReasoningState {
  sessions: Record<string, ReasoningSession>;
  activeSessionId: string | null;
  isConnected: boolean;
  performanceStats: {
    totalTokensProcessed: number;
    averageProcessingTime: number;
    peakMemoryUsage: number;
    batchesProcessed: number;
    averageBatchSize: number;
  };

  // Actions
  createSession: (sessionId: string, conversationId: string, metadata?: any) => void;
  addReasoningChunk: (sessionId: string, chunk: string) => void;
  addReasoningChunkBatch: (sessionId: string, chunks: string[]) => void;
  setActiveSession: (sessionId: string | null) => void;
  completeSession: (sessionId: string) => void;
  handleWebSocketEvent: (event: ReasoningEvent) => void;
  handleTokenEventWithBatching: (sessionId: string, token: string, data: any) => void;
  setConnected: (connected: boolean) => void;
  clearSession: (sessionId: string) => void;
  trimSessionContent: (sessionId: string, maxLength?: number) => void;
  flushPendingTokens: (sessionId: string) => void;

  // Selectors
  getSession: (sessionId: string) => ReasoningSession | undefined;
  getMetrics: (sessionId: string) => ReasoningMetrics | undefined;
  getActiveSession: () => ReasoningSession | undefined;
  getPerformanceStats: () => {
    totalTokensProcessed: number;
    averageProcessingTime: number;
    peakMemoryUsage: number;
    batchesProcessed: number;
    averageBatchSize: number;
  };
}

export const useReasoningStore = create<ReasoningState>()(
  subscribeWithSelector((set, get) => ({
    sessions: {},
    activeSessionId: null,
    isConnected: false,
    performanceStats: {
      totalTokensProcessed: 0,
      averageProcessingTime: 0,
      peakMemoryUsage: 0,
      batchesProcessed: 0,
      averageBatchSize: 0
    },

    createSession: (sessionId, conversationId, metadata) => {
      logger.reasoning(`Creating session: ${sessionId} with conversation: ${conversationId}`, metadata);
      
      set((state) => ({
        sessions: {
          ...state.sessions,
          [sessionId]: {
            sessionId,
            conversationId,
            content: "",
            isActive: true,
            startTime: new Date().toISOString(),
            metrics: {
              duration: 0,
              tokenCount: 0,
              updateCount: 0
            },
            metadata: metadata || {},
          },
        },
        activeSessionId: sessionId,
      }));
    },

    addReasoningChunk: (sessionId, chunk) => {
      const startTime = performance.now();
      
      set((state) => {
        const session = state.sessions[sessionId];
        if (!session) return state;

        const sessionStartTime = new Date(session.startTime).getTime();
        const currentTime = Date.now();
        const duration = Math.floor((currentTime - sessionStartTime) / 1000);
        
        // Calculate token count (approximate)
        const tokenCount = chunk.split(/\s+/).length;
        
        // Check if content is getting too long
        const newContent = session.content + chunk;
        const shouldTrim = newContent.length > 10000; // 10KB limit
        
        const finalContent = shouldTrim 
          ? newContent.slice(-8000) + "\n...[content trimmed for performance]..." 
          : newContent;

        return {
          sessions: {
            ...state.sessions,
            [sessionId]: {
              ...session,
              content: finalContent,
              metrics: {
                ...session.metrics,
                duration: duration > 0 ? duration : session.metrics.duration,
                tokenCount: session.metrics.tokenCount + tokenCount,
                updateCount: session.metrics.updateCount + 1
              },
            },
          },
          performanceStats: {
            ...state.performanceStats,
            totalTokensProcessed: state.performanceStats.totalTokensProcessed + tokenCount,
            averageProcessingTime: state.performanceStats.averageProcessingTime > 0 
              ? (state.performanceStats.averageProcessingTime + (performance.now() - startTime)) / 2
              : performance.now() - startTime
          }
        };
      });
      
      if (logger.getLevel() <= LogLevel.DEBUG) {
        logger.performance(`Added reasoning chunk to session ${sessionId}`, {
          chunkLength: chunk.length,
          processingTime: performance.now() - startTime
        });
      }
    },

    setActiveSession: (sessionId) => {
      set({ activeSessionId: sessionId });
    },

    completeSession: (sessionId) => {
      logger.reasoning(`Completing session: ${sessionId}`);
      
      set((state) => {
        const session = state.sessions[sessionId];
        if (!session) return state;

        return {
          sessions: {
            ...state.sessions,
            [sessionId]: {
              ...session,
              isActive: false,
              endTime: new Date().toISOString(),
            },
          },
        };
      });
    },

    handleWebSocketEvent: (event) => {
      const { type, session_id, data } = event;
      logger.reasoning(`Received event: ${type} for session: ${session_id}`, data);

      switch (type) {
        case 'connection_established':
          logger.info('reasoning', 'Reasoning connection established for user:', data.user_id);
          break;

        case 'reasoning_start':
        case 'session_started':
          logger.reasoning(`Creating session: ${session_id} with conversation: ${data.conversation_id || session_id}`);
          if (!get().sessions[session_id]) {
            get().createSession(session_id, data.conversation_id || session_id, data);
          } else {
            logger.reasoning(`Session ${session_id} already exists`);
          }
          break;

        case 'stream_chunk':
          const delta = data.delta || {};
          
          // Handle Reasoning Content
          if (delta.reasoning_content) {
            logger.reasoning(`Found reasoning_content: ${delta.reasoning_content.substring(0, 50)}...`);
            if (!get().sessions[session_id]) {
              logger.reasoning(`Creating session for reasoning chunk: ${session_id}`);
              get().createSession(session_id, session_id);
            }
            get().addReasoningChunk(session_id, delta.reasoning_content);
          }
          
          // Handle Final Answer Content
          const content = delta.content || data.chunk;
          if (content) {
            logger.reasoning(`Found regular content: ${content.substring(0, 50)}...`);
            window.dispatchEvent(new CustomEvent('chat_stream_chunk', { 
              detail: { sessionId: session_id, chunk: content } 
            }));
          }
          break;

        case 'token':
          const tokenContent = data.content || '';
          
          if (tokenContent) {
            // Check if token batching is enabled
            const shouldBatch = isTokenBatchingEnabled();
            
            if (shouldBatch) {
              // Use batched token processing
              get().handleTokenEventWithBatching(session_id, tokenContent, data);
            } else {
              // Use immediate processing (legacy behavior)
              if (!get().sessions[session_id]) {
                logger.reasoning(`Creating session for token stream: ${session_id}`);
                const conversationId = data.conversationId || session_id;
                get().createSession(session_id, conversationId, {
                  isTokenStream: true,
                  model: data.model,
                  provider: data.provider
                });
              }
              
              window.dispatchEvent(new CustomEvent('chat_stream_chunk', { 
                detail: { sessionId: session_id, chunk: tokenContent } 
              }));
              
              const session = get().sessions[session_id];
              if (session && session.isActive) {
                get().addReasoningChunk(session_id, tokenContent);
              }
            }
          }
          break;

        case 'stream_complete':
        case 'reasoning_end':
        case 'session_end':
        case 'complete':
          logger.reasoning(`Completing session: ${session_id}`);
          
          // Flush any pending tokens before completing
          if (isTokenBatchingEnabled()) {
            get().flushPendingTokens(session_id);
          }
          
          window.dispatchEvent(new CustomEvent('chat_stream_complete', { 
            detail: { sessionId: session_id } 
          }));
          get().completeSession(session_id);
          break;

        case 'typing':
          logger.reasoning(`Model is typing/thinking for session: ${session_id}`);
          if (!get().sessions[session_id]) {
            logger.reasoning(`Creating session for typing event: ${session_id}`);
            const conversationId = data.conversationId || session_id;
            get().createSession(session_id, conversationId, {
              isTyping: true,
              model: data.model,
              provider: data.provider
            });
          }
          break;

        case 'error':
          logger.error('reasoning', 'Reasoning error:', data);
          break;

        default:
          logger.warn('reasoning', `Unhandled reasoning event: ${type}`, data);
          break;
      }
    },

    setConnected: (connected) => {
      set({ isConnected: connected });
    },

    clearSession: (sessionId) => {
      set((state) => {
        const newSessions = { ...state.sessions };
        delete newSessions[sessionId];

        return {
          sessions: newSessions,
          activeSessionId: state.activeSessionId === sessionId ? null : state.activeSessionId,
        };
      });
    },

    trimSessionContent: (sessionId, maxLength = 10000) => {
      set((state) => {
        const session = state.sessions[sessionId];
        if (!session || session.content.length <= maxLength) return state;

        logger.performance(`Trimming session ${sessionId} content from ${session.content.length} to ${maxLength} characters`);
        
        return {
          sessions: {
            ...state.sessions,
            [sessionId]: {
              ...session,
              content: session.content.length > maxLength 
                ? session.content.slice(-maxLength) + "\n...[content trimmed]..."
                : session.content
            }
          }
        };
      });
    },

    addReasoningChunkBatch: (sessionId, chunks) => {
      const startTime = performance.now();
      const combinedChunk = chunks.join('');
      
      set((state) => {
        const session = state.sessions[sessionId];
        if (!session) return state;

        const sessionStartTime = new Date(session.startTime).getTime();
        const currentTime = Date.now();
        const duration = Math.floor((currentTime - sessionStartTime) / 1000);
        
        // Calculate token count (approximate)
        const tokenCount = combinedChunk.split(/\s+/).length;
        
        // Check if content is getting too long
        const newContent = session.content + combinedChunk;
        const shouldTrim = newContent.length > 10000;
        
        const finalContent = shouldTrim 
          ? newContent.slice(-8000) + "\n...[content trimmed for performance]..." 
          : newContent;

        return {
          sessions: {
            ...state.sessions,
            [sessionId]: {
              ...session,
              content: finalContent,
              metrics: {
                ...session.metrics,
                duration: duration > 0 ? duration : session.metrics.duration,
                tokenCount: session.metrics.tokenCount + tokenCount,
                updateCount: session.metrics.updateCount + 1
              },
            },
          },
          performanceStats: {
            ...state.performanceStats,
            totalTokensProcessed: state.performanceStats.totalTokensProcessed + tokenCount,
            batchesProcessed: state.performanceStats.batchesProcessed + 1,
            averageBatchSize: state.performanceStats.averageBatchSize > 0 
              ? (state.performanceStats.averageBatchSize + chunks.length) / 2
              : chunks.length,
            averageProcessingTime: state.performanceStats.averageProcessingTime > 0 
              ? (state.performanceStats.averageProcessingTime + (performance.now() - startTime)) / 2
              : performance.now() - startTime
          }
        };
      });
      
      if (logger.getLevel() <= LogLevel.DEBUG) {
        logger.performance(`Added reasoning batch to session ${sessionId}`, {
          batchSize: chunks.length,
          totalLength: combinedChunk.length,
          processingTime: performance.now() - startTime
        });
      }
    },

    handleTokenEventWithBatching: (sessionId, token, data) => {
      // Use WebSocket optimizer for token processing
      websocketOptimizer.processToken(sessionId, token, (batch: TokenBatch) => {
        // Ensure session exists
        if (!get().sessions[sessionId]) {
          logger.reasoning(`Creating session for batched token stream: ${sessionId}`);
          const conversationId = data.conversationId || sessionId;
          get().createSession(sessionId, conversationId, {
            isTokenStream: true,
            isBatched: true,
            model: data.model,
            provider: data.provider
          });
        }
        
        // Dispatch tokens to chat UI
        batch.tokens.forEach(tokenChunk => {
          window.dispatchEvent(new CustomEvent('chat_stream_chunk', { 
            detail: { sessionId, chunk: tokenChunk } 
          }));
        });
        
        // Add batched tokens to reasoning content
        const session = get().sessions[sessionId];
        if (session && session.isActive) {
          get().addReasoningChunkBatch(sessionId, batch.tokens);
        }
      });
    },

    flushPendingTokens: (sessionId) => {
      websocketOptimizer.flush(sessionId, (batch: TokenBatch) => {
        // Process any remaining tokens
        const session = get().sessions[sessionId];
        if (session && session.isActive && batch.tokens.length > 0) {
          get().addReasoningChunkBatch(sessionId, batch.tokens);
          
          // Dispatch to chat UI
          batch.tokens.forEach(tokenChunk => {
            window.dispatchEvent(new CustomEvent('chat_stream_chunk', { 
              detail: { sessionId, chunk: tokenChunk } 
            }));
          });
        }
      });
    },

    getSession: (sessionId) => get().sessions[sessionId],
    getMetrics: (sessionId) => get().sessions[sessionId]?.metrics,
    getActiveSession: () => {
      const state = get();
      return state.activeSessionId ? state.sessions[state.activeSessionId] : undefined;
    },
    getPerformanceStats: () => get().performanceStats,
  }))
);
