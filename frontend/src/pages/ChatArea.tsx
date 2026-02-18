import React, { useEffect, useMemo, useState } from "react";
import { useIsMobile } from "@/hooks/use-mobile";
import { useChatStore, useActiveMessages, useActiveChatId, useSetActiveChat, useCreateNewChat } from "@/store/chatStore";
import { useReasoningStore } from "@/store/reasoningStore";
import { mapToConversation } from "@/utils/chatUtils";
import { reasoningWebSocketService } from "@/services/reasoningWebSocketService";
import { useUIStateManagement } from "@/features/ui/useUIStateManagement";
import { useChatCreation } from "@/features/chat/useChatCreation";
import { useAllModels } from "@/features/models/useAllModels";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { generateChatTitle, detectMessageIntent } from "@/utils/chatUtils";

import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import ChatPane from "../components/chat/ChatPane";

export default function ChatArea({
  isAuthenticated,
  messages,
  activeChatId,
  setActiveChat,
  createNewChat,
  conversations,
  allModels,
  providerGroups,
  isLoading,
  setIsLoading,
  chatHandleSendMessage,
  chatHandleStopMessage,
  selectedLLM,
  setSelectedLLM,
  selectedModel,
  setSelectedModel,
  isSearchEnabled,
  setIsSearchEnabled,
  isImageMode,
  setIsImageMode,
  isCodingMode,
  setIsCodingMode,
  selectedSearchEngine,
  onSearchEngineChange,
}: any) {
  const isMobile = useIsMobile();

  const activeConversation = activeChatId ? conversations[activeChatId] : null;
  const modernConversation = useMemo(() => activeConversation ? mapToConversation(activeConversation) : null, [activeConversation, messages]);

  const { activeSessionId } = useReasoningStore();
  const streamMessageChunk = useChatStore(state => state.streamMessageChunk);

  // Listen for WebSocket stream events
  useEffect(() => {
    const handleStreamChunk = (e: any) => {
      const { chunk, sessionId } = e.detail;
      if (activeChatId) {
        // Since we now use messageId as sessionId, we can target the message directly
        streamMessageChunk(activeChatId, sessionId, chunk);
      }
    };

    const handleStreamComplete = (e: any) => {
      const { sessionId } = e.detail;
      if (activeChatId) {
        // Mark the specific message as done loading
        const convo = useChatStore.getState().conversations[activeChatId];
        if (convo) {
          useChatStore.getState().updateConversation(activeChatId, {
            messages: convo.messages.map((m: any) => 
              m.id === sessionId ? { ...m, isLoading: false } : m
            )
          });
        }
      }
    };

    window.addEventListener('chat_stream_chunk', handleStreamChunk);
    window.addEventListener('chat_stream_complete', handleStreamComplete);
    return () => {
      window.removeEventListener('chat_stream_chunk', handleStreamChunk);
      window.removeEventListener('chat_stream_complete', handleStreamComplete);
    };
  }, [activeChatId, activeConversation, streamMessageChunk]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const {
    messages: chatMessages, // unused but returned
    conversations: chatConversations, // unused but returned
    currentConversationId,
    currentSessionId,
    isLoading: chatIsLoading, // rename to avoid conflict if needed, or just use prop
    setIsLoading: setChatIsLoading,
    searchStatus,
    handleSendMessage: chatCreationHandleSendMessage,
    handleStopMessage: chatCreationHandleStopMessage,
    handleNewChat: chatCreationHandleNewChat
  } = useChatCreation({
    isAuthenticated,
    currentSessionId: activeChatId,
    currentConversationId: activeChatId,
    selectedLLM,
    selectedModel,
    modelMapping: {}, // Add proper mapping if available
    showRawResponse: false,
    isImageMode,
    isCodingMode,
    isSearchEnabled,
    selectedSearchEngine,
    autoTitleGeneration: true,
    onLoadingUpdate: setIsLoading,
    onReasoningStart: (message, config) => {
       // Handle deep thinking start if needed
    },
    setIsImageMode
  });

  const handleSendMessage = async (content: string, files: any[] = [], useReasoning: boolean = false) => {
    if (!content.trim()) return;

    // Auto-detect intent (optional: could auto-enable modes)
    const intent = detectMessageIntent(content);
    if (intent.isCode && !isCodingMode) {
      toast.info("Switching to coding mode", { duration: 1000 });
      setIsCodingMode(true);
    }
    
    // Deep thinking logic bridge - use WebSocket for the whole flow in deep thinking mode
    // Also trigger for "native reasoners" which might be handled by standard streaming but need reasoning store tracking
    if (useReasoning && activeChatId) {
      // Generate unique ID for this assistant message which will be the session ID
      const assistantId = `asst_${Date.now()}`;
      // Use this ID for reasoning session so we can map it back to the message
      const sessionId = assistantId;
      
      const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8008/ws/chat';

      // First add user message to chat store so it shows in UI
      const userMessage = {
        id: `user_${Date.now()}`,
        role: "user" as const,
        content: content,
        timestamp: new Date(),
        created_at: new Date().toISOString()
      };
      useChatStore.getState().addMessage(activeChatId, userMessage);

      // Create assistant message placeholder immediately so we can show reasoning status
      const assistantMessage = {
        id: assistantId,
        role: "assistant" as const,
        content: "", // Start empty, ReasoningBubble will show progress
        timestamp: new Date(),
        created_at: new Date().toISOString(),
        isLoading: true,
        deepThinking: true
      };
      useChatStore.getState().addMessage(activeChatId, assistantMessage);

      // Connect WebSocket for reasoning and answer streaming
      reasoningWebSocketService.connect(
        WS_BASE_URL, 
        sessionId, 
        activeChatId, 
        selectedLLM, 
        selectedModel, 
        content,
        isSearchEnabled,
        selectedSearchEngine || "duckduckgo",
        useReasoning
      );
      return;
    }

    await chatCreationHandleSendMessage(content, files, useReasoning);
  };

  const handleNewChat = async () => {
    try {
      const id = await createNewChat(); // Fix: await the Promise
      setActiveChat(id);
      if (isMobile) setSidebarOpen(false);
    } catch (error) {
      console.error("Failed to create new chat:", error);
      toast.error("Failed to create new chat. Please refresh the page and try again.");
    }
  };

  return (
    <div className="h-screen w-full bg-stone-100/50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 flex overflow-hidden">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={Object.values(conversations).map(mapToConversation)}
        selectedId={activeChatId}
        onSelect={setActiveChat}
        createNewChat={handleNewChat}
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
      />

      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-neutral-100/50 dark:bg-zinc-950">
        <Header
          createNewChat={handleNewChat}
          sidebarCollapsed={sidebarCollapsed}
          setSidebarOpen={setSidebarOpen}
          selectedLLM={selectedLLM}
          onLLMChange={setSelectedLLM}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          availableModels={allModels}
          providerGroups={providerGroups}
          connectionStatus="connected"
          selectedSearchEngine={selectedSearchEngine}
          onSearchEngineChange={onSearchEngineChange}
        />

        <ChatPane
          conversation={modernConversation}
          onSend={handleSendMessage}
          isLoading={isLoading}
          searchStatus={searchStatus}
          isThinking={false} 
          onPauseThinking={() => reasoningWebSocketService.disconnect()}
          isSearchEnabled={isSearchEnabled}
          setIsSearchEnabled={setIsSearchEnabled}
      isImageMode={isImageMode}
          setIsImageMode={setIsImageMode}
          isCodingMode={isCodingMode}
          setIsCodingMode={setIsCodingMode}
          selectedModel={selectedModel}
        />
      </main>
    </div>
  );
}
