import React from 'react';
import { useImageGeneration } from './useImageGeneration';
import { Message, Conversation } from '../chat/chatService';

interface ImageGenerationProps {
  isAuthenticated: boolean;
  currentConversationId: string;
  currentSessionId: string;
  conversations: Conversation[];
  selectedLLM: string;
  selectedModel: string;
  modelMapping: Record<string, string>;
  supportedImageModels: string[];
  setCurrentSessionId: (sessionId: string) => void;
  setCurrentConversationId: (conversationId: string) => void;
  setConversations: (updater: (prev: Conversation[]) => Conversation[]) => void;
  setMessages: (updater: (prev: Message[]) => Message[]) => void;
  setIsLoading: (loading: boolean) => void;
  loadUserSessions: () => Promise<void>;
  children: (handlers: {
    handleAutoAction: (action: string, prompt: string) => Promise<void>;
  }) => React.ReactNode;
}

export const ImageGeneration: React.FC<ImageGenerationProps> = ({
  isAuthenticated,
  currentConversationId,
  currentSessionId,
  conversations,
  selectedLLM,
  selectedModel,
  modelMapping,
  supportedImageModels,
  setCurrentSessionId,
  setCurrentConversationId,
  setConversations,
  setMessages,
  setIsLoading,
  loadUserSessions,
  children,
}) => {
  const { handleAutoAction: imageHandleAutoAction } = useImageGeneration();

  const handleAutoAction = async (action: string, prompt: string) => {
    await imageHandleAutoAction(action, prompt);
  };

  return (
    <>
      {children({
        handleAutoAction,
      })}
    </>
  );
};

export default ImageGeneration;
