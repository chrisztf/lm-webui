// Standardized to match backend provider names
export const PROVIDER_MAPPING = {
  'openai': 'openai',
  'google': 'google',
  'anthropic': 'anthropic',
  'xai': 'xai',
  'deepseek': 'deepseek',
  'zhipu': 'zhipu',
  'ollama': 'ollama',
  'lmstudio': 'lmstudio',
  'gguf': 'gguf',
} as const;

// Maps standardized provider IDs to their localStorage keys
export const LOCAL_STORAGE_API_KEY_MAPPING = {
  'openai': 'openAIKey',
  'google': 'googleKey',
  'anthropic': 'anthropicKey',
  'xai': 'xaiKey',
  'deepseek': 'deepseekKey',
  'zhipu': 'zhipuKey',
} as const;

// Providers that require API keys for cloud access
export const PROVIDERS_REQUIRING_API_KEY = [
  'openai',
  'google',
  'anthropic',
  'xai',
  'deepseek',
  'zhipu',
] as const;

export type ProviderId = keyof typeof PROVIDER_MAPPING;
