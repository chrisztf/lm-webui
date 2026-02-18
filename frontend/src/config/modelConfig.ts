import { isReasoningModel } from "@/utils/modelDetection";

export interface ModelCapability {
  id: string;
  name: string;
  type: 'reasoner' | 'standard';
  provider: 'local' | 'api';
  force_reasoning?: boolean; // Cannot turn off (native reasoners)
}

export const getModelCapability = (modelId: string): ModelCapability | undefined => {
  if (!modelId) return undefined;

  // Use centralized detection logic
  if (isReasoningModel(modelId)) {
    return {
      id: modelId,
      name: modelId,
      type: 'reasoner',
      provider: 'local', // Default assumption, but not critical for capability check
      force_reasoning: true
    };
  }

  // Default Fallback (Standard Model)
  return {
    id: modelId,
    name: modelId,
    type: 'standard',
    provider: 'local'
  };
};

// Check if a model is a native reasoner
export const isNativeReasoner = (modelId: string): boolean => {
  const cap = getModelCapability(modelId);
  return cap?.type === 'reasoner';
};
