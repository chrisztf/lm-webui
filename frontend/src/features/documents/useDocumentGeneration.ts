import { useState } from "react";
import { toast } from "sonner";
import { DocumentService, DocumentRequest } from "./documentService";

export function useDocumentGeneration() {
  const [isLoading, setIsLoading] = useState(false);

  const handleDocumentGeneration = async (
    action: string,
    prompt: string,
    options: {
      isAuthenticated: boolean;
      selectedLLM: string;
      selectedModel: string;
      modelMapping: Record<string, string>;
      setIsLoading: (loading: boolean) => void;
    }
  ) => {
    try {
      const {
        isAuthenticated,
        selectedLLM,
        selectedModel,
        modelMapping,
        setIsLoading: parentSetIsLoading,
      } = options;

      setIsLoading(true);
      parentSetIsLoading(true);

      const modelIdForAPI = modelMapping[selectedModel] || selectedModel;
      const request: DocumentRequest = {
        message: prompt,
        provider: selectedLLM,
        model: modelIdForAPI,
        api_key: "",
      };

      const result = await DocumentService.generateDocument(action, request);

      if (result.filename && result.blob) {
        DocumentService.downloadFile(result.blob, result.filename);
        toast.success(`✅ ${action.toUpperCase()} document generated and downloaded!`);
      } else {
        toast.error(`Failed to generate ${action} document`);
      }
    } catch (error: any) {
      const errorMessage = error?.message || `Failed to generate ${action} document`;
      toast.error(`Document Generation Error: ${errorMessage}`);
      console.error(`Error generating ${action} document:`, error);
    } finally {
      setIsLoading(false);
      options.setIsLoading(false);
    }
  };

  return {
    handleDocumentGeneration,
    isLoading,
  };
}
