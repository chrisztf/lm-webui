import { PROVIDER_MAPPING, LOCAL_STORAGE_API_KEY_MAPPING, PROVIDERS_REQUIRING_API_KEY } from './modelProviders';
import { getApiKeyForProvider, getBackendProviderName } from './apiKey';
import { useAuth } from '../hooks/useAuth';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL

// Utility function to handle fetch responses
async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.message || errorData.detail || `HTTP ${response.status}`);
    (error as any).status = response.status;
    (error as any).response = errorData;
    throw error;
  }

  // Handle different response types
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  } else {
    return response.blob(); // For file downloads
  }
}

// Create authenticated fetch wrapper
async function authFetch(url: string, options: RequestInit = {}): Promise<any> {
  const finalOptions = createAuthRequestOptions(options);

  // Debug logging for authentication
  console.log('🔐 Auth check:', {
    url: url.split('?')[0], // Remove query params for cleaner logs
    method: options.method || 'GET',
    credentials: 'include'
  });

  try {
    const response = await fetch(url, finalOptions);
    return await handleResponse(response);
  } catch (error: any) {
    // For 401 errors, try to refresh token
    if (error.status === 401) {
      try {
        // Try to refresh the access token
        const refreshResponse = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (refreshResponse.ok) {
          // Token refreshed successfully, retry the original request
          const retryResponse = await fetch(url, finalOptions);
          return await handleResponse(retryResponse);
        } else {
          // Refresh failed, throw error
          throw new Error('Authentication failed');
        }
      } catch (refreshError) {
        throw new Error('Authentication failed');
      }
    }

    throw error;
  }
}

// Create authenticated streaming fetch wrapper for real-time data
async function authenticatedStreamingFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const finalOptions = createAuthRequestOptions(options);

  try {
    const response = await fetch(url, finalOptions);

    // For 401 errors in streaming, try to refresh token once
    if (response.status === 401) {
      try {
        // Try to refresh the access token
        const refreshResponse = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (refreshResponse.ok) {
          // Token refreshed successfully, retry the original request
          const retryResponse = await fetch(url, finalOptions);
          return retryResponse;
        } else {
          // Refresh failed, throw error
          throw new Error('Authentication failed');
        }
      } catch (refreshError) {
        throw new Error('Authentication failed');
      }
    }

    // Return the response directly for streaming (don't use handleResponse)
    return response;
  } catch (error: any) {
    // For non-401 errors, re-throw
    throw error;
  }
}

interface ChatRequest {
  message: string;
  provider: string;
  model: string;
  api_key?: string;
  endpoint?: string; // For configurable endpoints like LM Studio
  conversation_history?: any[]; // Previous messages for context
  signal?: AbortSignal; // Added for aborting requests
  show_raw_response?: boolean; // Show raw unfiltered model output
  deep_thinking_mode?: boolean; // Enable extended reasoning/deep thinking
  conversation_id?: string; // Conversation ID for backend conversation tracking
  file_references?: any[]; // File references for RAG context
  web_search?: boolean; // Enable web search
  search_provider?: string; // Search provider to use
}

// Validate ChatRequest before sending
function validateChatRequest(req: ChatRequest): void {
  if (!req.message || !req.message.trim()) {
    throw new Error("Message is required");
  }
  if (!req.provider || !req.provider.trim()) {
    throw new Error("Provider is required");
  }
  if (!req.model || !req.model.trim()) {
    throw new Error("Model is required");
  }
}

export async function chatWithModel(req: ChatRequest): Promise<string> {
  validateChatRequest(req);
  return await _chatWithModel(req, false, false);
}

export async function chatWithModelStream(req: ChatRequest, onChunk?: (chunk: string) => void, onStatus?: (status: string) => void): Promise<string> {
  validateChatRequest(req);
  return await _chatWithModel(req, true, false, onChunk, onStatus);
}

export async function chatWithRAG(req: ChatRequest): Promise<string> {
  validateChatRequest(req);
  return await _chatWithModel(req, false, true);
}

export async function chatWithRAGStream(req: ChatRequest, onChunk?: (chunk: string) => void, onStatus?: (status: string) => void): Promise<string> {
  validateChatRequest(req);
  return await _chatWithModel(req, true, true, onChunk, onStatus);
}

async function _chatWithModel(
  req: ChatRequest, 
  stream: boolean = false, 
  useRAG: boolean = false,
  onChunk?: (chunk: string) => void,
  onStatus?: (status: string) => void
): Promise<string> {
  // Create request - API keys will be retrieved from backend database
  const requestWithKey = {
    ...req,
    api_key: req.api_key,
    use_rag: useRAG,  // Add use_rag parameter for enhanced endpoint
    // Remove endpoint parameter as it's handled by backend now
  };

  // DEBUG: Log the request to see if conversation_id is included
  console.log('🔍 DEBUG _chatWithModel requestWithKey:', {
    hasConversationId: 'conversation_id' in requestWithKey,
    conversationId: requestWithKey.conversation_id,
    keys: Object.keys(requestWithKey),
    messagePreview: requestWithKey.message?.substring(0, 50)
  });

  // Always use the enhanced chat endpoint which handles both regular and RAG
  const endpoint = '/api/chat';

  try {
    // Check if we expect streaming response (when raw/deep modes are enabled)
    const shouldStream = req.show_raw_response || req.deep_thinking_mode;

    if (shouldStream && stream) {
      // Handle streaming response for raw/deep thinking modes
      // Use authenticated streaming approach to maintain token refresh capability
      const response = await authenticatedStreamingFetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestWithKey)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let buffer = '';

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const textChunk = decoder.decode(value, { stream: true });
            buffer += textChunk;
            
            // Split buffer by double newline to handle SSE events
            const lines = buffer.split('\n\n');
            // Keep the last partial line in the buffer
            buffer = lines.pop() || '';
            
            for (const line of lines) {
              const trimmedLine = line.trim();
              if (trimmedLine.startsWith('data: ')) {
                const dataStr = trimmedLine.slice(6);
                try {
                  // Try to parse as JSON first (standard SSE format from our backend)
                  const data = JSON.parse(dataStr);
                  
                  if (data.type === 'status') {
                    // Handle status updates (e.g., "Searching web...", "Reading results...")
                    if (onStatus) onStatus(data.content);
                  } else if (data.chunk) {
                    // Handle content chunks
                    fullResponse += data.chunk;
                    if (onChunk) onChunk(data.chunk);
                  } else if (data.error) {
                    console.error('Stream error:', data.error);
                    throw new Error(data.error);
                  }
                } catch (e) {
                  // Fallback for older format or non-JSON data
                  console.warn('Failed to parse SSE data:', e, dataStr);
                }
              } else if (trimmedLine && !trimmedLine.startsWith('data: ')) {
                 // Handle raw streaming if backend didn't use SSE format (fallback)
                 fullResponse += trimmedLine;
                 if (onChunk) onChunk(trimmedLine);
              }
            }
          }
        } catch (readError: any) {
          // If the connection was closed cleanly or network error
          if (readError.name === 'AbortError') {
            console.log('Stream aborted by user');
          } else {
            console.error("Stream reading error:", readError);
            if (onStatus) onStatus("Connection interrupted");
            throw readError;
          }
        } finally {
          reader.releaseLock();
        }
      }

      return fullResponse;
    } else {
      // Handle regular non-streaming response
      const response = await authFetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestWithKey)
      });

      // Handle errors from the backend
      if (response.error) {
        throw new Error(response.message || response.error);
      }

      return response.response;
    }
  } catch (error: any) {
    // Handle fetch errors (network, HTTP status codes)
    throw error;
  }
}

export async function searchQuery(query: string): Promise<Array<{title: string, link: string, snippet: string}>> {
  const url = new URL(`${API_BASE_URL}/api/search`);
  url.searchParams.set('q', query);
  const response = await authFetch(url.toString());
  return response;
}

export async function generateDocx(req: ChatRequest): Promise<string> {
  // Retrieve API key for document generation
  let apiKeyToUse = req.api_key;
  if (!apiKeyToUse && isAuthenticated()) {
    try {
      // For authenticated users, try to get from backend first
      if (req.provider === "openai") {
        const apiKeyData = await authFetch(`${API_BASE_URL}/api/api_keys/openai`);
        apiKeyToUse = apiKeyData.api_key;
      }
    } catch (error) {
      // Fallback to localStorage for authenticated users if backend fails
      apiKeyToUse = localStorage.getItem("openAIKey") || undefined;
    }
  } else if (!apiKeyToUse) {
    // For unauthenticated users, try localStorage
    apiKeyToUse = localStorage.getItem("openAIKey") || undefined;
  }

  const requestWithKey = { ...req, api_key: apiKeyToUse };
  const response = await authFetch(`${API_BASE_URL}/api/generate/docx`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestWithKey)
  });
  return response.file;
}

export async function generateXlsx(req: ChatRequest): Promise<string> {
  // Retrieve API key for spreadsheet generation
  let apiKeyToUse = req.api_key;
  if (!apiKeyToUse && isAuthenticated()) {
    try {
      // For authenticated users, try to get from backend first
      if (req.provider === "openai") {
        const apiKeyData = await authFetch(`${API_BASE_URL}/api/api_keys/openai`);
        apiKeyToUse = apiKeyData.api_key;
      }
    } catch (error) {
      // Fallback to localStorage for authenticated users if backend fails
      apiKeyToUse = localStorage.getItem("openAIKey") || undefined;
    }
  } else if (!apiKeyToUse) {
    // For unauthenticated users, try localStorage
    apiKeyToUse = localStorage.getItem("openAIKey") || undefined;
  }

  const requestWithKey = { ...req, api_key: apiKeyToUse };
  const response = await authFetch(`${API_BASE_URL}/api/generate/xlsx`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestWithKey)
  });
  return response.file;
}

export async function generateImage(req: ChatRequest, conversationId?: string): Promise<string> {
  // Retrieve API key based on provider for image generation
  let apiKeyToUse = req.api_key;
  if (!apiKeyToUse && isAuthenticated()) {
    try {
      // Use centralized provider mapping
      const backendProvider = (PROVIDER_MAPPING as any)[req.provider] || req.provider;

      const apiKeyData = await authFetch(`${API_BASE_URL}/api/api_keys/${backendProvider}`);
      apiKeyToUse = apiKeyData.api_key;
    } catch (error) {
      // Fallback mappings for localStorage
      const localStorageMapping: Record<string, string> = {
        'openai': 'openAIKey',
        'grok': 'xaiKey',
        'claude': 'anthropicKey',
        'google': 'googleKey'  // Frontend uses 'google', localStorage uses 'googleKey'
      };
      const localStorageKey = localStorageMapping[req.provider] || `${req.provider}Key`;
      apiKeyToUse = localStorage.getItem(localStorageKey) || undefined;
    }
  } else if (!apiKeyToUse) {
    // Fallback for unauthenticated users
    const localStorageMapping: Record<string, string> = {
      'openai': 'openAIKey',
      'grok': 'xaiKey',
      'claude': 'anthropicKey',
      'google': 'googleKey'  // Frontend uses 'google', localStorage uses 'googleKey'
    };
    const localStorageKey = localStorageMapping[req.provider] || `${req.provider}Key`;
    apiKeyToUse = localStorage.getItem(localStorageKey) || undefined;
  }

  // Create the correct request format for image generation
  // Backend expects: { prompt, model, api_key, size, quality, style, conversation_id }
  const imageRequest: any = {
    prompt: req.message, // Convert 'message' to 'prompt'
    model: req.model,
    api_key: apiKeyToUse,
    size: "1024x1024", // Default size
    quality: "standard", // Default quality
    style: "vivid" // Default style
  };

  // Add conversation_id if provided
  if (conversationId) {
    imageRequest.conversation_id = conversationId;
  }

  const response = await authFetch(`${API_BASE_URL}/api/images/generate/${req.provider}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(imageRequest)
  });

  // Handle errors from the backend
  if (response.error) {
    throw new Error(response.message || response.error);
  }

  return response.image_url;
}

export async function downloadFile(filename: string): Promise<Blob> {
  const response = await authFetch(`${API_BASE_URL}/api/download/${filename}`);
  return response;
}

export async function fetchSettings(): Promise<Record<string, any>> {
  const response = await authFetch(`${API_BASE_URL}/api/settings`);
  return response;
}

export async function updateSettings(settings: Record<string, any>): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/settings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(settings)
  });
}

export interface FetchModelsOptions {
  /** Whether to use dynamic model fetching (default: true) */
  dynamic?: boolean;
  /** Whether to fetch all providers at once (default: false) */
  allProviders?: boolean;
  /** API key to use (for unauthenticated requests) */
  apiKey?: string | undefined;
  /** Whether to force a refresh (bypass cache) */
  forceRefresh?: boolean;
}

// Cache for model fetching to prevent redundant requests
const modelsCache: Record<string, { timestamp: number, data: string[] | Record<string, string[]> }> = {};
const activeFetchPromises: Record<string, Promise<string[] | Record<string, string[]>>> = {};
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes cache

/**
 * Unified model fetching function
 * 
 * @param provider - Provider name (e.g., 'openai', 'google', 'gguf'). If not provided, fetches all providers.
 * @param options - Fetch options
 * @returns Array of model names or record of provider->models
 */
export async function fetchModels(
  provider?: string, 
  options: FetchModelsOptions = {}
): Promise<string[] | Record<string, string[]>> {
  const { dynamic = true, allProviders = false, apiKey, forceRefresh = false } = options;
  
  // Create a unique cache key based on params
  const cacheKey = `models_${provider || 'all'}_${dynamic ? 'dynamic' : 'static'}_${allProviders ? 'all' : 'single'}_${apiKey ? 'with_key' : 'no_key'}`;
  
  // Return cached result if valid and not forcing refresh
  if (!forceRefresh && modelsCache[cacheKey]) {
    const cached = modelsCache[cacheKey];
    if (Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return cached.data;
    }
  }
  
  // Return active promise if already fetching
  if (activeFetchPromises[cacheKey]) {
    return activeFetchPromises[cacheKey];
  }
  
  // Create new fetch promise
  const fetchPromise = (async () => {
    try {
      // Handle GGUF models
      if (provider === 'gguf') {
        const response = await authFetch(`${API_BASE_URL}/api/models/local`);
        
        if (Array.isArray(response.models)) {
          const models = response.models.map((model: any) => 
            typeof model === 'string' ? model : model.name || model.id || 'Unknown Model'
          );
          return models;
        }
        
        return [];
      }
      
      // Use centralized provider mapping
      const providerMapping = PROVIDER_MAPPING;
      
      // Fetch all providers if requested or no provider specified
      if (allProviders || !provider) {
        const [localModels, apiModels] = await Promise.all([
          authFetch(`${API_BASE_URL}/api/models/local`).catch(() => ({ models: [] })),
          authFetch(`${API_BASE_URL}/api/models/api/all`).catch(() => ({ models: [] }))
        ]);
        
        const transformedModels: Record<string, string[]> = {};
        
        // Add GGUF models
        if (Array.isArray(localModels.models)) {
          transformedModels['gguf'] = localModels.models.map((model: any) => 
            model.name || model.id || 'Unknown Model'
          );
        }
        
        // Add API models
        if (Array.isArray(apiModels.models)) {
          for (const model of apiModels.models) {
            const modelProvider = model.provider || 'unknown';
            if (!transformedModels[modelProvider]) {
              transformedModels[modelProvider] = [];
            }
            transformedModels[modelProvider].push(model.name || model.id || 'Unknown Model');
          }
        }
        
        return transformedModels;
      }
      
      // Single provider fetch
      const backendProvider = (providerMapping as any)[provider!] || provider;
      
      // Try dynamic endpoint first if enabled
      if (dynamic) {
        try {
          const dynamicUrl = new URL(`${API_BASE_URL}/api/models/api/dynamic`);
          dynamicUrl.searchParams.set('provider', provider);
          
          console.log(`🔄 Fetching dynamic models for ${provider} (backend: ${backendProvider})`);
          const response = await authFetch(dynamicUrl.toString());
          
          if (Array.isArray(response.models)) {
            const models = response.models.map((model: any) => 
              typeof model === 'string' ? model : model.name || model.id || 'Unknown Model'
            );
            console.log(`✅ Dynamic models fetched for ${provider}: (${models.length})`, models);
            return models;
          }
        } catch (error) {
          console.warn(`⚠️ Dynamic model fetch failed for ${provider}, falling back to static models:`, error);
        }
      }
      
      // Fallback to static endpoint
      const staticUrl = new URL(`${API_BASE_URL}/api/models/api`);
      staticUrl.searchParams.set('provider', backendProvider);

      const response = await authFetch(staticUrl.toString());
      
      if (Array.isArray(response.models)) {
        const models = response.models.map((model: any) => 
          typeof model === 'string' ? model : model.name || model.id || 'Unknown Model'
        );
        console.log(`📋 Static models fetched for ${provider}: (${models.length})`, models);
        return models;
      }
      
      return [];
    } finally {
      // Clean up active promise
      delete activeFetchPromises[cacheKey];
    }
  })();
  
  // Store promise
  activeFetchPromises[cacheKey] = fetchPromise;
  
  // Wait for result and update cache
  try {
    const result = await fetchPromise;
    modelsCache[cacheKey] = {
      timestamp: Date.now(),
      data: result
    };
    return result;
  } catch (error) {
    throw error;
  }
}

/**
 * Refresh model cache for a provider
 * 
 * @param provider - Provider name (optional, refreshes all if not provided)
 */
export async function refreshModelsCache(provider?: string): Promise<void> {
  // For GGUF models, no refresh needed as they're local files
  if (provider === 'gguf') {
    return;
  }
  
  // For API providers, use the refresh endpoint
  const url = new URL(`${API_BASE_URL}/api/models/api/refresh`);
  if (provider) {
    url.searchParams.set('provider', provider);
  }
  await authFetch(url.toString(), {
    method: 'POST',
  });
}

// Backward compatibility aliases
export const fetchModelsByProvider = (provider: string) => fetchModels(provider, { dynamic: true }) as Promise<string[]>;
export const fetchAllModels = () => fetchModels(undefined, { allProviders: true }) as Promise<Record<string, string[]>>;
export const fetchModelsForProvider = (provider: string, apiKey?: string) => {
  console.warn('fetchModelsForProvider is deprecated, use fetchModels with apiKey option instead');
  return fetchModels(provider, { apiKey }) as Promise<string[]>;
};

export async function fetchImageModels(): Promise<string[]> {
  const response = await authFetch(`${API_BASE_URL}/api/images/models`);
  return response.models;
}


// History and Session Management APIs
export interface HistoryMessage {
  role: string;
  content: string;
  model?: string;
}

export interface Session {
  session_id: string;
  title: string;
  last_activity: string;
  message_count: number;
}

export interface SessionHistory {
  messages: Array<{
    id: number;
    session_id: string;
    role: string;
    content: string;
    model?: string;
    timestamp: string;
  }>;
  images: Array<{
    id: number;
    session_id: string;
    prompt: string;
    seed?: number;
    file_path: string;
    timestamp: string;
  }>;
}

export async function getConversationHistory(conversationId: string): Promise<any> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}`);
  return response;
}

export async function listConversations(): Promise<any[]> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversations`);
  return response.conversations;
}

export async function updateConversationTitle(conversationId: string, title: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}/title`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title })
  });
}

export async function generateConversationTitle(conversationId: string): Promise<{ message: string; conversation_id: string; status: string }> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}/generate-title`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  return response;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}`, {
    method: 'DELETE',
  });
}

export async function saveMessage(conversationId: string, role: string, content: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      role: role,
      message: content
    })
  });
}

export async function getConversation(conversationId: string): Promise<any> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}`);
  return response.messages;
}

// File References API
export interface FileReference {
  id: number;
  conversation_id: string;
  user_id: number;
  message_id: number;
  file_type: string;
  file_path: string;
  metadata: any;
  created_at: string;
}

export async function getFileReferences(conversationId: string): Promise<FileReference[]> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}/files`);
  return response.files || [];
}

export async function getConversationWithFiles(conversationId: string): Promise<{
  messages: any[];
  files: FileReference[];
}> {
  const [messages, files] = await Promise.all([
    getConversation(conversationId),
    getFileReferences(conversationId)
  ]);
  
  return { messages, files };
}

export async function createConversation(
  title: string = "New Chat", 
  conversationId?: string
): Promise<{ conversation_id: string; title: string; created_at: string; exists?: boolean }> {
  const body: any = { title };
  if (conversationId) {
    body.conversation_id = conversationId;
  }
  
  const response = await authFetch(`${API_BASE_URL}/api/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body)
  });
  return response;
}

export async function getUserSessions(): Promise<Session[]> {
  const response = await authFetch(`${API_BASE_URL}/api/sessions`);
  return response.sessions;
}

export async function getCurrentSession(): Promise<any> {
  const response = await authFetch(`${API_BASE_URL}/api/sessions/current`);
  return response.session;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

// Standardized Authentication Utilities

/**
 * Check if user is authenticated
 * Uses consistent pattern across the application
 */
export function isAuthenticated(): boolean {
  // Use the auth store to check authentication status
  // This will be updated by the useAuth hook
  const { isAuthenticated } = useAuth.getState();
  return isAuthenticated;
}

/**
 * Get authentication headers for API requests
 * Provides consistent header format across all authenticated requests
 */
export function getAuthHeaders(): Record<string, string> {
  // For cookie-based authentication, we don't need to add headers
  // The browser will automatically include cookies with credentials: 'include'
  return {
    'Content-Type': 'application/json',
  };
}

/**
 * Create authenticated request options
 * Standardized way to create authenticated fetch options
 */
export function createAuthRequestOptions(options: RequestInit = {}): RequestInit {
  return {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
    credentials: 'include', // Include cookies for both tokens
  };
}

/**
 * Check if authentication is required for a route
 * Standardized route categorization helper
 */
export function requiresAuth(route: string): boolean {
  const publicRoutes = [
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/status',
    '/api/auth/refresh'
  ];
  
  return !publicRoutes.some(publicRoute => route.startsWith(publicRoute));
}

export async function getSessionImages(sessionId: string): Promise<any[]> {
  const url = new URL(`${API_BASE_URL}/api/images`);
  url.searchParams.set('session_id', sessionId);
  const response = await authFetch(url.toString());
  return response.images;
}

// API Key Management Functions
export interface ApiKey {
  provider: string;
  created_at: string;
}

export async function addApiKey(provider: string, apiKey: string): Promise<void> {
  // For local providers (lmstudio, ollama), the apiKey is actually a URL
  const localProviders = ["lmstudio", "ollama"];
  const requestBody: any = {
    provider,
    api_key: apiKey
  };
  
  if (localProviders.includes(provider)) {
    // For local providers, we should send the URL as the api_key
    // The backend will handle it appropriately
    requestBody.api_key = apiKey;
  }
  
  await authFetch(`${API_BASE_URL}/api/api_keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody)
  });
}

export async function testApiKey(provider: string): Promise<{ valid: boolean; message: string }> {
  const response = await authFetch(`${API_BASE_URL}/api/api_keys/${provider}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  return response;
}

export async function getApiKey(provider: string): Promise<string> {
  const response = await authFetch(`${API_BASE_URL}/api/api_keys/${provider}`);
  return response.api_key;
}

export async function deleteApiKey(provider: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/api_keys/${provider}`, {
    method: 'DELETE',
  });
}

export async function listApiKeys(): Promise<ApiKey[]> {
  const response = await authFetch(`${API_BASE_URL}/api/api_keys`);
  return response.keys || [];
}

// Conversation management functions
export async function deleteConversationFromBackend(conversationId: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}`, {
    method: 'DELETE',
  });
}

export async function updateConversationTitleInBackend(conversationId: string, title: string): Promise<void> {
  await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}/title`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title })
  });
}

export async function generateConversationTitleInBackend(conversationId: string): Promise<{ message: string; conversation_id: string; status: string }> {
  const response = await authFetch(`${API_BASE_URL}/api/history/conversation/${conversationId}/generate-title`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  return response;
}

// Intent verification function
export async function verifyIntent(prompt: string, type: string): Promise<{ verified: boolean; prompt: string; type: string }> {
  const response = await authFetch(`${API_BASE_URL}/api/intents/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt, type })
  });
  return response;
}

// SSE (Server-Sent Events) for real-time title updates
export interface TitleUpdateEvent {
  title: string;
  type: 'title_update' | 'timeout' | 'error';
  message?: string;
  timestamp?: string;
}

export interface TitleUpdateOptions {
  onTitleUpdate: (title: string) => void;
  onTimeout?: () => void;
  onError?: (error: Error) => void;
  timeoutMs?: number;
}

/**
 * Listen for real-time title updates via SSE
 * Returns a cleanup function to close the connection
 */
export function listenForTitleUpdates(
  conversationId: string,
  options: TitleUpdateOptions
): () => void {
  const { onTitleUpdate, onTimeout, onError, timeoutMs = 30000 } = options;
  
  const url = `${API_BASE_URL}/api/conversations/${conversationId}/title-updates`;
  const eventSource = new EventSource(url, { withCredentials: true });
  
  let timeoutId: NodeJS.Timeout | null = null;
  
  // Set timeout
  if (timeoutMs > 0) {
    timeoutId = setTimeout(() => {
      eventSource.close();
      if (onTimeout) onTimeout();
    }, timeoutMs);
  }
  
  eventSource.onmessage = (event) => {
    try {
      const data: TitleUpdateEvent = JSON.parse(event.data);
      
      if (data.type === 'title_update' && data.title) {
        onTitleUpdate(data.title);
        eventSource.close();
        if (timeoutId) clearTimeout(timeoutId);
      } else if (data.type === 'timeout') {
        if (onTimeout) onTimeout();
        eventSource.close();
        if (timeoutId) clearTimeout(timeoutId);
      } else if (data.type === 'error') {
        throw new Error(data.message || 'SSE error');
      }
    } catch (error) {
      console.error('Error parsing SSE event:', error);
      if (onError) onError(error as Error);
      eventSource.close();
      if (timeoutId) clearTimeout(timeoutId);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    if (onError) onError(new Error('SSE connection failed'));
    eventSource.close();
    if (timeoutId) clearTimeout(timeoutId);
  };
  
  // Return cleanup function
  return () => {
    eventSource.close();
    if (timeoutId) clearTimeout(timeoutId);
  };
}

/**
 * Health check for title updates SSE endpoint
 */
export async function checkTitleUpdatesHealth(conversationId: string): Promise<{
  conversation_id: string;
  active_connections: number;
  status: string;
  timestamp: string;
}> {
  const response = await authFetch(`${API_BASE_URL}/api/conversations/${conversationId}/title-updates/health`);
  return response;
}
