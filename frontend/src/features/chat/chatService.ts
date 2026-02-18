import { 
  chatWithModel, 
  chatWithModelStream, 
  updateConversationTitle, 
  createConversation,
  generateConversationTitle,
  listenForTitleUpdates,
  generateImage
} from "@/utils/api";

export interface ChatRequest {
  message: string;
  provider: string;
  model: string;
  api_key?: string;
  conversation_history?: any[];
  signal?: AbortSignal | undefined;
  show_raw_response?: boolean;
  deep_thinking_mode?: boolean;
  file_references?: any[]; // File references for RAG
  web_search?: boolean; // Enable web search
  search_provider?: string; // Search provider to use
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  model?: string;
  searchUsed?: boolean;
  deepThinking?: boolean;
  rawResponse?: string;
  generatedImageUrl?: string;
  fileAttachments?: Array<{
    id: number;
    file_path: string;
    file_type: string;
    metadata?: any;
  }> | undefined;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage: Date;
  messageCount: number;
  messages?: any[];
}

export class ChatService {
  static async sendMessage(
    request: ChatRequest,
    options: {
      isAuthenticated: boolean;
      currentSessionId: string;
      currentConversationId: string;
      messages: Message[];
      selectedModel: string;
      modelMapping: Record<string, string>;
      showRawResponse: boolean;
      isDeepThinkingMode: boolean;
      isSearchEnabled?: boolean;
      selectedSearchEngine?: string;
      autoTitleGeneration: boolean;
      setCurrentSessionId: (id: string) => void;
      setCurrentConversationId: (id: string) => void;
      setConversations: (updater: (prev: Conversation[]) => Conversation[]) => void;
      updateConversation: (id: string, updates: any) => void;
      setMessages: (messages: Message[]) => void;
      setIsLoading: (loading: boolean) => void;
      onChunk?: (chunk: string) => void;
      onStatus?: (status: string) => void;
    }
  ): Promise<{
    userMessage: Message;
    assistantMessage: Message;
    sessionId: string;
  }> {
    const {
      isAuthenticated,
      currentSessionId,
      currentConversationId,
      messages,
      selectedModel,
      modelMapping,
      showRawResponse,
      isDeepThinkingMode,
      isSearchEnabled,
      selectedSearchEngine,
      autoTitleGeneration,
      setCurrentSessionId,
      setCurrentConversationId,
      setConversations,
      updateConversation,
      setMessages,
      setIsLoading
    } = options;

    // Create session only when first message is sent (not on app load)
    let sessionId = currentSessionId;
    if (!sessionId) {
      if (isAuthenticated) {
        // For authenticated users, use backend-generated conversation ID
        const newConversation = await createConversation("New Chat");
        sessionId = newConversation.conversation_id;
        setCurrentSessionId(sessionId);
        setCurrentConversationId(sessionId);
        
        // Add to conversations list
        const conversation: Conversation = {
          id: sessionId,
          title: newConversation.title,
          lastMessage: new Date(),
          messageCount: 0,
          messages: []
        };
        setConversations(prev => [conversation, ...prev]);
      } else {
        // Create temporary session for unauthenticated users
        sessionId = `temp_${Date.now()}`;
        setCurrentSessionId(sessionId);
        setCurrentConversationId(sessionId);
        
        const newConversation: Conversation = {
          id: sessionId,
          title: "New Chat",
          lastMessage: new Date(),
          messageCount: 0,
          messages: []
        };
        setConversations(prev => [newConversation, ...prev]);
      }
    }

    // Note: User message will be persisted by the chat API (/api/chat)
    // when it processes the request, so we don't need to save it separately here.

    // Include conversation history for context
    const conversationHistory = messages.map(msg => {
      // Handle timestamp safely - fallback to created_at or current time if timestamp is missing/invalid
      // Cast to any to access created_at which might exist from chatStore
      const timeValue = msg.timestamp || (msg as any).created_at || new Date();
      let isoTime;
      try {
        isoTime = new Date(timeValue).toISOString();
      } catch (e) {
        isoTime = new Date().toISOString();
      }

      return {
        role: msg.role,
        content: msg.content,
        timestamp: isoTime,
        model: msg.model
      };
    });

    // Get the actual model ID from the mapping for API calls
    // Try both prefixed and non-prefixed keys to be robust
    const providerPrefixedKey = request.provider ? `${request.provider}:${selectedModel}` : selectedModel;
    const modelIdForAPI = modelMapping[providerPrefixedKey] || modelMapping[selectedModel] || selectedModel;
    
    console.log(`🤖 Model resolution: '${selectedModel}' -> '${modelIdForAPI}' (using mapping: ${!!(modelMapping[providerPrefixedKey] || modelMapping[selectedModel])})`);

    // Use streaming for raw/deep thinking modes to show real-time reasoning
    const shouldUseStreaming = showRawResponse || isDeepThinkingMode;

    // Create a signal for the request - either use the provided one or create a new one
    const signal = request.signal || new AbortController().signal;

    // Check if the message is an image generation request
    const lowerMsg = request.message.toLowerCase();
    const isImageGenerationRequest = 
      (lowerMsg.startsWith("generate image") || 
       lowerMsg.startsWith("create image") || 
       lowerMsg.startsWith("draw ") ||
       lowerMsg.includes("generate an image") ||
       lowerMsg.includes("create an image")) &&
      (selectedModel.includes("dall-e") || 
       selectedModel.includes("image") || 
       selectedModel.includes("flux") ||
       selectedModel.toLowerCase().includes("nano banana") ||
       selectedModel.toLowerCase().includes("imagen"));

    let response: string;

    if (isImageGenerationRequest) {
      console.log("🎨 Image generation intent detected in ChatService");
      try {
        // Use the generateImage API instead of chat
        const imageUrl = await generateImage({
          message: request.message,
          provider: request.provider,
          model: modelIdForAPI,
          api_key: request.api_key || "" 
        }, sessionId);
        
        // The generateImage API returns the URL, but we need to return a markdown string
        // The backend generate_image endpoints already return a markdown string with the image!
        // Wait, looking at api.ts generateImage returns response.image_url
        // But backend endpoints return a JSON with image_url AND message_id.
        // Let's check api.ts again.
        
        // Re-reading api.ts: generateImage returns response.image_url.
        // But the backend (gemini_image.py/openai_image.py) saves a message to the DB with markdown.
        // So we might just need to fetch the last message or construct a fake one?
        // Actually, if we look at api.ts generateImage implementation:
        // return response.image_url;
        
        // We need to return a string response that will be displayed in the chat.
        response = `![Generated Image](${imageUrl})`;
        
      } catch (error: any) {
        console.error("Image generation failed:", error);
        response = `Failed to generate image: ${error.message || "Unknown error"}`;
      }
    } else if (shouldUseStreaming) {
      response = await chatWithModelStream({
        message: request.message,
        provider: request.provider,
        model: modelIdForAPI,
        api_key: "",
        conversation_history: conversationHistory,
        show_raw_response: showRawResponse,
        deep_thinking_mode: isDeepThinkingMode,
        signal: signal,
        conversation_id: sessionId, // Pass conversation ID to backend
        file_references: request.file_references || [],
        web_search: isSearchEnabled ?? false,
        search_provider: selectedSearchEngine ?? "duckduckgo",
      }, options.onChunk, options.onStatus);
    } else {
      response = await chatWithModel({
        message: request.message,
        provider: request.provider,
        model: modelIdForAPI,
        api_key: "",
        conversation_history: conversationHistory,
        signal: signal,
        conversation_id: sessionId, // Pass conversation ID to backend
        file_references: request.file_references || [],
        web_search: isSearchEnabled ?? false,
        search_provider: selectedSearchEngine ?? "duckduckgo",
      });
    }

    // Extract content from JSON response if needed (for reasoning/deep thinking modes)
    let processedResponse = response;
    if (isDeepThinkingMode || showRawResponse) {
      try {
        // Try to parse as JSON and extract content
        const parsedResponse = JSON.parse(response);
        if (parsedResponse.response || parsedResponse.content) {
          processedResponse = parsedResponse.response || parsedResponse.content;
        }
      } catch (error) {
        // If parsing fails, use the original response
        console.log("Response is not JSON, using as-is");
      }
    }

    // Note: Assistant message is already persisted by the chat API (/api/chat)
    // when it returns the response, so we don't need to save it separately here.

    // Debug logging for title generation
    console.log(`🎯 Frontend Title Check: sessionId=${sessionId}, messages.length=${messages.length}, autoTitleGeneration=${autoTitleGeneration}, isAuthenticated=${isAuthenticated}`);
    console.log(`   Message preview: '${request.message.substring(0,100)}${request.message.length > 100 ? '...' : ''}'`);

    // Auto-generate title after first user message
    // Check if this is the first user message in the conversation
    const userMessagesCount = messages.filter(m => m.role === "user").length;
    const isFirstUserMessage = userMessagesCount === 0;
    
    if (autoTitleGeneration && isFirstUserMessage && isAuthenticated) {
      try {
        console.log(`✅ Frontend: Triggering backend title generation for first user message (total messages: ${messages.length}, user messages: ${userMessagesCount})`);
        
        // Mark conversation as generating title
        if (updateConversation) {
          updateConversation(sessionId, { isTitleGenerating: true });
        }

        // Trigger backend title generation (non-blocking)
        generateConversationTitle(sessionId).then(result => {
          console.log(`   Backend title generation started: ${result.message}`);
          
          // Listen for updates via SSE
          const cleanup = listenForTitleUpdates(sessionId, {
            onTitleUpdate: (newTitle) => {
               console.log(`   Title updated via SSE: ${newTitle}`);
               if (updateConversation) {
                 updateConversation(sessionId, { title: newTitle, isTitleGenerating: false });
               }
            },
            onTimeout: () => {
               console.log(`   Title update timed out`);
               if (updateConversation) {
                 updateConversation(sessionId, { isTitleGenerating: false });
               }
            },
            onError: (err) => {
               console.error(`   Title update error:`, err);
               if (updateConversation) {
                 updateConversation(sessionId, { isTitleGenerating: false });
               }
            },
            timeoutMs: 30000 // 30s timeout
          });
          
        }).catch(error => {
          console.error("Failed to trigger backend title generation:", error);
          if (updateConversation) {
            updateConversation(sessionId, { isTitleGenerating: false });
          }
        });
        
      } catch (error) {
        console.error("Failed to trigger title generation:", error);
      }
    } else {
      console.log(`❌ Frontend: Skipping title generation (not first user message or not authenticated: total=${messages.length}, user=${userMessagesCount}, authenticated=${isAuthenticated})`);
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: request.message,
      timestamp: new Date(),
    };

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: processedResponse,
      timestamp: new Date(),
      model: selectedModel,
      deepThinking: isDeepThinkingMode,
    };

    return {
      userMessage,
      assistantMessage,
      sessionId
    };
  }

  static async stopMessage(abortController: AbortController | null, setIsLoading: (loading: boolean) => void) {
    if (abortController) {
      abortController.abort(); // Abort the ongoing request
      setIsLoading(false); // Immediately stop loading state
    }
  }
}
