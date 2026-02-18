import { create } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { getConversationWebSocketService, ConversationUpdate } from '@/services/ConversationWebSocketService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: string;
  created_at: string;
  timestamp?: Date; // For backward compatibility
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  isBackendConfirmed?: boolean;
}

interface ChatStore {
  // Active conversation state
  activeChatId: string | null;
  conversations: Record<string, Conversation>;

  // Loading states
  imageGenerationLoading: boolean;
  conversationCreationLoading: boolean;

  // Error handling
  lastError: Error | null;
  retryableOperations: Map<string, () => Promise<void>>;

  // Background processing
  processingImages: Set<string>;

  // WebSocket state
  websocketConnected: boolean;

  // Actions
  setActiveChat: (chatId: string) => void;
  createNewChat: () => Promise<string>;
  addMessage: (chatId: string, message: Message) => Promise<string>; // Returns the actual conversation ID (may change if backend syncs)
  updateConversationTitle: (chatId: string, title: string) => Promise<void>;
  updateConversation: (chatId: string, updates: Partial<Conversation>) => void;
  streamMessageChunk: (chatId: string, messageId: string, chunk: string) => void;
  deleteConversation: (chatId: string) => Promise<void>;
  ensureConversation: () => Promise<string>;

  // Loading state actions
  startImageGeneration: (conversationId: string) => void;
  completeImageGeneration: (conversationId: string) => void;
  startConversationCreation: () => void;
  completeConversationCreation: () => void;

  // Error handling actions
  setError: (error: Error) => void;
  clearError: () => void;
  addRetryableOperation: (key: string, operation: () => Promise<void>) => void;
  removeRetryableOperation: (key: string) => void;
  retryOperation: (key: string) => Promise<void>;

  // Background processing actions
  addProcessingImage: (imageUrl: string) => void;
  removeProcessingImage: (imageUrl: string) => void;
  isImageProcessing: (imageUrl: string) => boolean;

  // WebSocket actions
  initializeWebSocket: () => Promise<void>;
  disconnectWebSocket: () => void;
  handleConversationUpdate: (update: ConversationUpdate) => void;

  // Recovery actions
  recoverConversation: (chatId: string) => Promise<boolean>;
  validateConversationState: (chatId: string) => boolean;

  // Getters
  getActiveConversation: () => Conversation | null;
  getActiveMessages: () => Message[];
}

export const useChatStore = create<ChatStore>()(
  (set, get) => ({
      // Initial state
      activeChatId: null,
      conversations: {},

      // Loading states
      imageGenerationLoading: false,
      conversationCreationLoading: false,

      // Error handling
      lastError: null,
      retryableOperations: new Map(),

      // Background processing
      processingImages: new Set(),
      
      // WebSocket state
      websocketConnected: false,
      
      // Set active chat
      setActiveChat: (chatId: string) => {
        // Validate it's a string, not a Promise or other object
        if (typeof chatId !== 'string') {
          console.error('setActiveChat: Invalid chatId type:', typeof chatId, chatId);
          return;
        }
        
        // Check for corrupted IDs like [object Promise]
        if (chatId.includes('[object')) {
          console.error('setActiveChat: Corrupted chatId:', chatId);
          return;
        }
        
        set({ activeChatId: chatId });
        
        // Always trigger fetch in background to sync with server (Stale-While-Revalidate)
        // This ensures cross-device consistency and loads messages if missing
        get().recoverConversation(chatId).catch(e => console.error("Background sync failed:", e));
      },
      
      // Create new chat with backend-first creation
      createNewChat: async () => {
        const state = get();
        
        // Find existing empty conversation (title = "New Chat" and no messages)
        const emptyConv = Object.values(state.conversations).find(
          conv => conv.title === 'New Chat' && conv.messages.length === 0
        );
        
        if (emptyConv) {
          // Activate existing empty conversation instead of creating new one
          set({ activeChatId: emptyConv.id });
          return emptyConv.id;
        }
        
        try {
          // Create conversation in backend first
          const { createConversation } = await import('@/utils/api');
          const response = await createConversation('New Chat');
          const backendChatId = response.conversation_id;
          
          // Create frontend conversation with backend ID
          const newConversation: Conversation = {
            id: backendChatId,
            title: 'New Chat',
            messages: [],
            created_at: new Date().toISOString(),
            isBackendConfirmed: true,
          };

          set(state => ({
            activeChatId: backendChatId,
            conversations: {
              ...state.conversations,
              [backendChatId]: newConversation,
            },
          }));

          console.log(`✅ Created new conversation with backend ID: ${backendChatId}`);
          return backendChatId;
        } catch (error) {
          console.error('❌ Failed to create conversation in backend, using frontend fallback:', error);
          
          // Fallback: create frontend-only conversation
          const fallbackChatId = `conv_${Date.now()}`;
          const fallbackConversation: Conversation = {
            id: fallbackChatId,
            title: 'New Chat',
            messages: [],
            created_at: new Date().toISOString(),
          };

          set(state => ({
            activeChatId: fallbackChatId,
            conversations: {
              ...state.conversations,
              [fallbackChatId]: fallbackConversation,
            },
          }));

          return fallbackChatId;
        }
      },
      
      // Add message to conversation with backend creation on first message
      addMessage: async (chatId: string, message: Message) => {
        // Start loading state (will disable chat input)
        get().startConversationCreation();
        
        try {
          const state = get();
          const conversation = state.conversations[chatId];
          // Only create in backend if it's the first message AND not already confirmed
          const isFirstUserMessage = conversation && 
                                     conversation.messages.length === 0 && 
                                     message.role === 'user' &&
                                     !conversation.isBackendConfirmed;
          
          let backendConversationId = chatId;
          
          // Create conversation in backend on first user message
          if (isFirstUserMessage) {
            try {
              const { createConversation } = await import('@/utils/api');
              // Pass the frontend conversation ID to backend
              const response = await createConversation('New Chat', chatId);
              backendConversationId = response.conversation_id;
              
              console.log(`✅ Created conversation in backend: ${chatId} -> ${backendConversationId}`, 
                         response.exists ? '(already existed)' : '(new)');
              
              // Update frontend with backend ID if different
              if (backendConversationId !== chatId) {
                // Replace frontend ID with backend ID
                set(state => {
                  const { [chatId]: oldConv, ...otherConvs } = state.conversations;
                  if (!oldConv) return state;
                  
                  return {
                    activeChatId: backendConversationId,
                    conversations: {
                      ...otherConvs,
                      [backendConversationId]: {
                        id: backendConversationId,
                        title: oldConv.title,
                        messages: oldConv.messages,
                        created_at: oldConv.created_at,
                        isBackendConfirmed: true,
                      },
                    },
                  };
                });
              } else {
                // If IDs match, just mark as confirmed
                set(state => {
                  const currConv = state.conversations[chatId];
                  if (!currConv) return state;
                  return {
                    conversations: {
                      ...state.conversations,
                      [chatId]: {
                        ...currConv,
                        isBackendConfirmed: true,
                      }
                    }
                  };
                });
              }
            } catch (error) {
              console.error('❌ Failed to create conversation in backend:', error);
              // Continue with frontend-only conversation
            }
          }
          
          // Process message for frontend store
          const processedMessage: Message = message.id ? message : {
            ...message,
            id: crypto.randomUUID(),
            created_at: message.created_at || new Date().toISOString(),
          };
          
          // Update frontend store with message
          set(state => {
            const conv = state.conversations[backendConversationId] || 
                        (conversation ? { ...conversation, id: backendConversationId } : null);
            
            if (!conv) {
              // Create conversation if it doesn't exist
              const newConversation: Conversation = {
                id: backendConversationId,
                title: 'New Chat',
                messages: [processedMessage],
                created_at: new Date().toISOString(),
              };
              
              return {
                conversations: {
                  ...state.conversations,
                  [backendConversationId]: newConversation,
                },
              };
            }
            
            // Enhanced duplicate detection
            const isDuplicate = conv.messages.some(msg => {
              if (processedMessage.id && msg.id === processedMessage.id) return true;
              
              const timeDiff = Math.abs(
                new Date(msg.created_at).getTime() - new Date(processedMessage.created_at).getTime()
              );
              
              return (
                msg.role === processedMessage.role &&
                msg.content === processedMessage.content &&
                timeDiff < 2000
              );
            });
            
            if (isDuplicate) {
              console.log(`🔄 Skipping duplicate message: ${processedMessage.content.substring(0, 50)}...`);
              return state;
            }
            
          // Listen for SSE title updates on first user message
          if (conv.title === 'New Chat' && processedMessage.role === 'user') {
            // Start listening for SSE title updates
            import('@/utils/api').then(({ listenForTitleUpdates }) => {
              const cleanup = listenForTitleUpdates(backendConversationId, {
                onTitleUpdate: (title) => {
                  console.log(`📡 SSE title update received for ${backendConversationId}: ${title}`);
                  get().updateConversationTitle(backendConversationId, title);
                },
                onTimeout: () => {
                  console.log(`⏰ SSE timeout for title updates on ${backendConversationId}`);
                  // Fallback: generate title locally
                  import('@/utils/chatUtils').then(({ generateChatTitle }) => {
                    const allMessages = [...conv.messages, processedMessage];
                    const title = generateChatTitle(allMessages.map(msg => ({
                      id: msg.id,
                      role: msg.role,
                      content: msg.content,
                      created_at: msg.created_at,
                      metadata: {}
                    })));
                    
                    if (title !== 'New Chat') {
                      get().updateConversationTitle(backendConversationId, title);
                    }
                  }).catch(err => {
                    console.error('Failed to generate fallback title:', err);
                  });
                },
                onError: (error) => {
                  console.error(`❌ SSE error for title updates on ${backendConversationId}:`, error);
                },
                timeoutMs: 30000 // 30 seconds
              });
              
              // Store cleanup function for later if needed
              setTimeout(() => {
                // Cleanup after timeout or when title is received
                cleanup();
              }, 35000); // Slightly longer than timeout
            }).catch(err => {
              console.error('Failed to import SSE utilities:', err);
            });
          }
            
            return {
              conversations: {
                ...state.conversations,
                [backendConversationId]: {
                  ...conv,
                  messages: [...conv.messages, processedMessage].sort((a, b) =>
                    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
                  ),
                },
              },
            };
          });
          
          return backendConversationId;
          
        } catch (error) {
          console.error('❌ Error in addMessage:', error);
          get().setError(error as Error);
          throw error;
        } finally {
          // Complete loading state (re-enables chat input)
          get().completeConversationCreation();
        }
      },
      
      // Update conversation title with backend API integration
      updateConversation: (chatId: string, updates: Partial<Conversation>) => {
        set(state => {
          const conversation = state.conversations[chatId];
          if (!conversation) return state;
          
          return {
            conversations: {
              ...state.conversations,
              [chatId]: {
                ...conversation,
                ...updates,
              },
            },
          };
        });
      },

      streamMessageChunk: (chatId: string, messageId: string, chunk: string) => {
        set(state => {
          const conversation = state.conversations[chatId];
          if (!conversation) return state;

          const messages = [...conversation.messages];
          const messageIndex = messages.findIndex(m => m.id === messageId);

          if (messageIndex > -1) {
            const message = messages[messageIndex];
            if (message) {
              messages[messageIndex] = {
                ...message,
                content: message.content + chunk,
                timestamp: message.timestamp || new Date(), // Maintain original timestamp if exists
              };
            }
          } else {
            // If message doesn't exist yet, create it
            messages.push({
              id: messageId,
              role: 'assistant',
              content: chunk,
              created_at: new Date().toISOString(),
            });
          }

          return {
            conversations: {
              ...state.conversations,
              [chatId]: {
                ...conversation,
                messages,
              },
            },
          };
        });
      },

      updateConversationTitle: async (chatId: string, title: string) => {
        try {
          // First, try to update in backend
          const { updateConversationTitleInBackend } = await import('@/utils/api');
          await updateConversationTitleInBackend(chatId, title);
          
          // If successful, update frontend store
          set(state => {
            const conversation = state.conversations[chatId];
            if (!conversation) return state;
            
            return {
              conversations: {
                ...state.conversations,
                [chatId]: {
                  ...conversation,
                  title,
                },
              },
            };
          });
          
          console.log(`✅ Conversation title updated in backend: ${chatId} -> "${title}"`);
        } catch (error) {
          console.error(`❌ Failed to update conversation title in backend:`, error);
          
          // Fallback: update frontend only
          set(state => {
            const conversation = state.conversations[chatId];
            if (!conversation) return state;
            
            return {
              conversations: {
                ...state.conversations,
                [chatId]: {
                  ...conversation,
                  title,
                },
              },
            };
          });
          
          throw error; // Re-throw for error handling in UI
        }
      },
      
      // Delete conversation with backend API integration
      deleteConversation: async (chatId: string) => {
        // Validation for corrupted IDs
        const isCorrupted = typeof chatId !== 'string' || chatId === '[object Object]' || chatId.includes('[object');
        
        if (!isCorrupted) {
          try {
            // First, try to delete from backend
            const { deleteConversationFromBackend } = await import('@/utils/api');
            await deleteConversationFromBackend(chatId);
            console.log(`✅ Conversation ${chatId} deleted from backend`);
          } catch (error: any) {
            // If not found (404), treat as success/already deleted and proceed to local cleanup
            const isNotFound = error?.status === 404 || error?.message?.includes('404') || error?.response?.detail === 'Conversation not found';
            
            if (isNotFound) {
               console.warn(`⚠️ Conversation ${chatId} not found in backend, removing locally`);
            } else {
               console.error(`❌ Failed to delete conversation ${chatId} from backend:`, error);
               // We proceed to local delete to ensure UI can recover
            }
          }
        } else {
           console.warn(`⚠️ Detected corrupted conversation ID: ${chatId}, removing locally only`);
        }

        // Always perform local cleanup to unblock UI
        set(state => {
          const newConversations = { ...state.conversations };
          
          // Standard delete
          delete newConversations[chatId];
          
          // Aggressive cleanup for corrupted IDs (key/value mismatch)
          if (isCorrupted) {
            Object.keys(newConversations).forEach(key => {
              const val = newConversations[key];
              // Delete if key is corrupted
              if (key.includes('[object')) {
                delete newConversations[key];
              }
              // Delete if value's ID matches the requested ID but key is different
              else if (val && val.id === chatId) {
                delete newConversations[key];
              }
            });
          }
          
          // If the deleted conversation was active, select another one or set to null
          let newActiveChatId = state.activeChatId;
          const isActiveChat = state.activeChatId && (
            state.activeChatId === chatId || 
            (isCorrupted && (!newConversations[state.activeChatId] || state.activeChatId.includes('[object')))
          );

          if (isActiveChat) {
            const remainingIds = Object.keys(newConversations);
            newActiveChatId = remainingIds.length > 0 ? remainingIds[0]! : null;
          }
          
          return {
            conversations: newConversations,
            activeChatId: newActiveChatId
          };
        });
      },
      
      // Ensure active conversation exists
      ensureConversation: async () => {
        const state = get();
        let chatId = state.activeChatId;
        
        if (!chatId) {
          // Create new conversation if none exists
          const newChatId = `conv_${Date.now()}`;
          const newConversation: Conversation = {
            id: newChatId,
            title: 'New Chat',
            messages: [],
            created_at: new Date().toISOString(),
            isBackendConfirmed: false,
          };

          set((state) => ({
            activeChatId: newChatId,
            conversations: {
              ...state.conversations,
              [newChatId]: newConversation,
            },
          }));
          
          return newChatId;
        }
        
        return chatId;
      },
      
      // Get active conversation
      getActiveConversation: () => {
        const state = get();
        if (!state.activeChatId) return null;
        return state.conversations[state.activeChatId] || null;
      },
      
      // Loading state actions
      startImageGeneration: (_conversationId: string) => {
        set({ imageGenerationLoading: true });
      },

      completeImageGeneration: (_conversationId: string) => {
        set({ imageGenerationLoading: false });
      },

      startConversationCreation: () => {
        set({ conversationCreationLoading: true });
      },

      completeConversationCreation: () => {
        set({ conversationCreationLoading: false });
      },

      // Error handling actions
      setError: (error: Error) => {
        set({ lastError: error });
      },

      clearError: () => {
        set({ lastError: null });
      },

      addRetryableOperation: (key: string, operation: () => Promise<void>) => {
        set(state => ({
          retryableOperations: new Map(state.retryableOperations).set(key, operation)
        }));
      },

      removeRetryableOperation: (key: string) => {
        set(state => {
          const newOperations = new Map(state.retryableOperations);
          newOperations.delete(key);
          return { retryableOperations: newOperations };
        });
      },

      retryOperation: async (key: string) => {
        const state = get();
        const operation = state.retryableOperations.get(key);
        if (operation) {
          try {
            await operation();
            get().removeRetryableOperation(key);
            get().clearError();
          } catch (error) {
            get().setError(error as Error);
            throw error;
          }
        }
      },

      // Background processing actions
      addProcessingImage: (imageUrl: string) => {
        set(state => ({
          processingImages: new Set(state.processingImages).add(imageUrl)
        }));
      },

      removeProcessingImage: (imageUrl: string) => {
        set(state => {
          const newSet = new Set(state.processingImages);
          newSet.delete(imageUrl);
          return { processingImages: newSet };
        });
      },

      isImageProcessing: (imageUrl: string) => {
        return get().processingImages.has(imageUrl);
      },

      // WebSocket actions
      initializeWebSocket: async () => {
        try {
          const wsService = getConversationWebSocketService({
            onConversationUpdate: (update) => {
              get().handleConversationUpdate(update);
            },
            onConnected: () => {
              set({ websocketConnected: true });
              console.log('✅ WebSocket connected for real-time conversation updates');
            },
            onDisconnected: () => {
              set({ websocketConnected: false });
              console.log('🔌 WebSocket disconnected');
            },
            onError: (error) => {
              console.error('❌ WebSocket error:', error);
              set({ websocketConnected: false });
            }
          });

          await wsService.connect();
        } catch (error) {
          console.error('Failed to initialize WebSocket:', error);
          set({ websocketConnected: false });
        }
      },

      disconnectWebSocket: () => {
        const wsService = getConversationWebSocketService();
        wsService.disconnect();
        set({ websocketConnected: false });
      },

      handleConversationUpdate: (update: ConversationUpdate) => {
        if (update.type === 'conversation_updated' && update.title) {
          console.log(`📡 Updating conversation title via WebSocket: ${update.conversation_id} -> ${update.title}`);
          
          // Update the conversation title in the store
          set(state => {
            const conversation = state.conversations[update.conversation_id];
            if (!conversation) return state;
            
            return {
              conversations: {
                ...state.conversations,
                [update.conversation_id]: {
                  ...conversation,
                  title: update.title!,
                },
              },
            };
          });
        }
      },

      // Recovery actions
      recoverConversation: async (chatId: string) => {
        try {
          // Attempt to reload conversation from backend
          const { getConversationHistory } = await import('@/utils/api');
          const response = await getConversationHistory(chatId);

          // Handle potentially nested response structure from backend
          // Backend returns { conversation: { ... } } or flat object depending on endpoint
          const conversationData = response.conversation || response;
          const messages = conversationData.messages;

          if (messages && Array.isArray(messages)) {
            // Update store with recovered data
            set(state => ({
              conversations: {
                ...state.conversations,
                [chatId]: {
                  id: chatId,
                  title: conversationData.title || 'Recovered Chat',
                  messages: messages,
                  created_at: conversationData.created_at || new Date().toISOString(),
                  isBackendConfirmed: true,
                },
              },
            }));
            return true;
          }
          return false;
        } catch (error) {
          console.error('Failed to recover conversation:', error);
          return false;
        }
      },

      validateConversationState: (chatId: string) => {
        const state = get();
        const conversation = state.conversations[chatId];
        return !!(conversation && conversation.id && conversation.messages);
      },

      // Get active messages
      getActiveMessages: () => {
        const state = get();
        if (!state.activeChatId) return [];
        return state.conversations[state.activeChatId]?.messages || [];
      },
    })
  );

// Stable selector functions to prevent infinite loops
const selectActiveChatId = (state: ChatStore) => state.activeChatId;
const selectSetActiveChat = (state: ChatStore) => state.setActiveChat;
const selectCreateNewChat = (state: ChatStore) => state.createNewChat;
const selectAddMessage = (state: ChatStore) => state.addMessage;
const selectImageGenerationLoading = (state: ChatStore) => state.imageGenerationLoading;
const selectConversationCreationLoading = (state: ChatStore) => state.conversationCreationLoading;
const selectLastError = (state: ChatStore) => state.lastError;
const selectProcessingImages = (state: ChatStore) => state.processingImages;
const selectStartImageGeneration = (state: ChatStore) => state.startImageGeneration;
const selectCompleteImageGeneration = (state: ChatStore) => state.completeImageGeneration;
const selectStartConversationCreation = (state: ChatStore) => state.startConversationCreation;
const selectCompleteConversationCreation = (state: ChatStore) => state.completeConversationCreation;
const selectSetError = (state: ChatStore) => state.setError;
const selectClearError = (state: ChatStore) => state.clearError;
const selectAddProcessingImage = (state: ChatStore) => state.addProcessingImage;
const selectRemoveProcessingImage = (state: ChatStore) => state.removeProcessingImage;
const selectIsImageProcessing = (state: ChatStore) => state.isImageProcessing;
const selectRecoverConversation = (state: ChatStore) => state.recoverConversation;
const selectValidateConversationState = (state: ChatStore) => state.validateConversationState;
export const selectConversations = (state: ChatStore) => state.conversations;

const selectActiveConversation = (state: ChatStore): Conversation | null => {
  if (!state.activeChatId) return null;
  return state.conversations[state.activeChatId] || null;
};

const selectActiveMessages = (state: ChatStore): Message[] => {
  if (!state.activeChatId) return [];
  return state.conversations[state.activeChatId]?.messages || [];
};

// Export hooks for common use cases - with proper memoization to avoid infinite loops
export const useActiveChatId = () => useChatStore(selectActiveChatId);
export const useSetActiveChat = () => useChatStore(selectSetActiveChat);
export const useCreateNewChat = () => useChatStore(selectCreateNewChat);
export const useAddMessage = () => useChatStore(selectAddMessage);
export const useUpdateConversation = () => useChatStore(state => state.updateConversation);

export const useActiveConversation = (): Conversation | null => {
  return useChatStore(useShallow(selectActiveConversation));
};

export const useActiveMessages = (): Message[] => {
  return useChatStore(useShallow(selectActiveMessages));
};

// Export new hooks for enhanced functionality
export const useImageGenerationLoading = () => useChatStore(selectImageGenerationLoading);
export const useConversationCreationLoading = () => useChatStore(selectConversationCreationLoading);
export const useLastError = () => useChatStore(selectLastError);
export const useProcessingImages = () => useChatStore(selectProcessingImages);
export const useStartImageGeneration = () => useChatStore(selectStartImageGeneration);
export const useCompleteImageGeneration = () => useChatStore(selectCompleteImageGeneration);
export const useStartConversationCreation = () => useChatStore(selectStartConversationCreation);
export const useCompleteConversationCreation = () => useChatStore(selectCompleteConversationCreation);
export const useSetError = () => useChatStore(selectSetError);
export const useClearError = () => useChatStore(selectClearError);
export const useAddProcessingImage = () => useChatStore(selectAddProcessingImage);
export const useRemoveProcessingImage = () => useChatStore(selectRemoveProcessingImage);
export const useIsImageProcessing = () => useChatStore(selectIsImageProcessing);
export const useRecoverConversation = () => useChatStore(selectRecoverConversation);
export const useValidateConversationState = () => useChatStore(selectValidateConversationState);
