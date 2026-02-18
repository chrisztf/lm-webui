import React from 'react';
import { useDocumentGeneration } from './useDocumentGeneration';

interface DocumentGenerationProps {
  isAuthenticated: boolean;
  selectedLLM: string;
  selectedModel: string;
  modelMapping: Record<string, string>;
  setIsLoading: (loading: boolean) => void;
  children: (handlers: {
    handleDocumentGeneration: (action: string, prompt: string) => Promise<void>;
  }) => React.ReactNode;
}

export const DocumentGeneration: React.FC<DocumentGenerationProps> = ({
  isAuthenticated,
  selectedLLM,
  selectedModel,
  modelMapping,
  setIsLoading,
  children,
}) => {
  const { handleDocumentGeneration: docHandleDocumentGeneration } = useDocumentGeneration();

  const handleDocumentGeneration = async (action: string, prompt: string) => {
    const options = {
      isAuthenticated,
      selectedLLM,
      selectedModel,
      modelMapping,
      setIsLoading,
    };

    await docHandleDocumentGeneration(action, prompt, options);
  };

  return (
    <>
      {children({
        handleDocumentGeneration,
      })}
    </>
  );
};

export default DocumentGeneration;
