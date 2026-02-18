import { useState } from "react";
import { ModelService } from "./modelService";
import { UseModelManagementOptions, ConnectionStatus } from "./types";
import { getFilteredModels } from "./modalityFilter";
import { ActiveModes } from "./types/modelModality";

export function useModelManagement(options: UseModelManagementOptions) {
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  const loadModels = async () => {
    options.onConnectionStatusUpdate("testing");

    const result = await ModelService.loadModels(
      options.selectedLLM,
      options.isAuthenticated,
      options.storedApiKeys
    );

    // Filter models based on deep thinking mode if enabled
    let filteredModels = result.modelNames;
    if (options.deepThinkingEnabled) {
      try {
        filteredModels = await ModelService.filterModelsForDeepThinking(
          result.modelNames,
          options.deepThinkingEnabled
        );
        console.log(`Filtered ${result.modelNames.length} models to ${filteredModels.length} reasoning-capable models for deep thinking`);
      } catch (error) {
        console.error("Failed to filter models for deep thinking:", error);
        // Fallback to all models if filtering fails
        filteredModels = result.modelNames;
      }
    }

    options.onModelsUpdate(filteredModels);
    options.onModelMappingUpdate(result.modelMapping);
    options.onConnectionStatusUpdate(result.connectionStatus);

    if (!filteredModels.includes(options.selectedModel)) {
      options.onSelectedModelUpdate(filteredModels[0] || "");
    }
  };

  const loadImageModels = async () => {
    const imageModels = await ModelService.loadImageModels();
    options.onSupportedImageModelsUpdate(imageModels);
  };

  const refreshModels = async () => {
    setIsLoadingModels(true);
    try {
      await loadModels();
    } finally {
      setIsLoadingModels(false);
    }
  };

  const validateModelSupport = (modelId: string, supportedModels: string[]): boolean => {
    return supportedModels.some(model => model.toLowerCase() === modelId.toLowerCase());
  };

  return {
    isLoadingModels,
    setIsLoadingModels,
    loadModels,
    loadImageModels,
    refreshModels,
    validateModelSupport,
  };
}
