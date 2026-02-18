import React from "react";
import { ChatConversation } from "@/types/chat-ui";
import { Message as LegacyMessage } from "./Message";
import { LoadingMessage } from "./LoadingMessage";
import { useReasoningStore } from "@/store/reasoningStore";
import Composer from "../Composer";
import { useAuth } from "@/contexts/AuthContext";
import { Welcome } from "../Welcome";

interface ChatPaneProps {
  conversation: ChatConversation | null;
  onSend: (content: string, files?: any[], useReasoning?: boolean) => Promise<void>;
  isLoading: boolean;
  searchStatus?: string;
  isThinking: boolean;
  onPauseThinking: () => void;
  isSearchEnabled: boolean;
  setIsSearchEnabled: (enabled: boolean) => void;
  isImageMode: boolean;
  setIsImageMode: (enabled: boolean) => void;
  isCodingMode: boolean;
  setIsCodingMode: (enabled: boolean) => void;
  selectedModel?: string;
}

export default function ChatPane({
  conversation,
  onSend,
  isLoading,
  searchStatus,
  isThinking,
  onPauseThinking,
  isSearchEnabled,
  setIsSearchEnabled,
  isImageMode,
  setIsImageMode,
  isCodingMode,
  setIsCodingMode,
  selectedModel,
}: ChatPaneProps) {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const { activeSessionId } = useReasoningStore();
  const { user } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages.length, isThinking]);

  const composer = (
    <Composer
      onSend={onSend}
      busy={isLoading}
      conversationId={conversation?.id || ""}
      isSearchEnabled={isSearchEnabled}
      setIsSearchEnabled={setIsSearchEnabled}
      isImageMode={isImageMode}
      setIsImageMode={setIsImageMode}
      isCodingMode={isCodingMode}
      setIsCodingMode={setIsCodingMode}
      selectedModel={selectedModel || "gpt-4o-mini"}
    />
  );

  if (!conversation || (conversation.messages.length === 0 && !activeSessionId)) {
    return <Welcome user={user}>{composer}</Welcome>;
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col relative bg-neutral-200/70 dark:bg-neutral-900/50">
      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-8 scrollbar-hide">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-dark">
              {conversation.title}
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              {conversation.messages.length} messages · Updated recently
            </p>
          </div>

          {conversation.messages.map((m) => (
            <div key={m.id} className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <LegacyMessage
                message={{
                  id: m.id,
                  role: m.role as any,
                  content: m.content,
                  timestamp: new Date(m.created_at),
                  isLoading: !!m.isLoading // Pass isLoading status
                }}
              />
            </div>
          ))}

          {/* Loading indicator when LLM is generating response (standard mode) */}
          {isLoading && !activeSessionId && (
            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
              <LoadingMessage 
                showRawResponse={false}
                isStreaming={false}
                searchStatus={searchStatus || ""}
                isSearchEnabled={isSearchEnabled}
              />
            </div>
          )}

          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      <div className="px-4 pb-4">
        <div className="max-w-3xl mx-auto">
          {composer}
        </div>
      </div>
    </div>
  );
}
