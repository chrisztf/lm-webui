import React, { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Search,
  MessageSquare,
  X,
  Clock,
  User,
  Bot
} from "lucide-react";

interface Message {
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
}

interface Conversation {
  id: string;
  title: string;
  lastMessage: Date;
  messageCount: number;
  messages: Message[];
}

interface SearchChatProps {
  conversations: Conversation[];
  onConversationSelect: (conversationId: string) => void;
  onClose: () => void;
}

export function SearchChat({ conversations, onConversationSelect, onClose }: SearchChatProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Get all messages from all conversations for searching
  const allMessages = useMemo(() => {
    return conversations.flatMap(conv =>
      conv.messages.map(msg => ({
        ...msg,
        conversationTitle: conv.title,
        conversationId: conv.id
      }))
    );
  }, [conversations]);

  const filteredMessages = useMemo(() => {
    if (!searchQuery.trim()) return [];

    const query = searchQuery.toLowerCase().trim();
    return allMessages.filter(msg =>
      msg.content.toLowerCase().includes(query) ||
      msg.conversationTitle.toLowerCase().includes(query) ||
      (msg.model && msg.model.toLowerCase().includes(query))
    );
  }, [allMessages, searchQuery]);

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;

    const query = searchQuery.toLowerCase().trim();
    return conversations.filter(conv =>
      conv.title.toLowerCase().includes(query) ||
      conv.messages.some(msg =>
        msg.content.toLowerCase().includes(query) ||
        (msg.model && msg.model.toLowerCase().includes(query))
      )
    );
  }, [conversations, searchQuery]);

  const handleConversationClick = (conversationId: string) => {
    onConversationSelect(conversationId);
    onClose();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search Bar - Always visible */}
      <div className="p-3 border-b border-sidebar-border">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search chats, messages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-8"
              autoFocus
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSearchQuery("")}
                className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Search Stats */}
        {searchQuery && (
          <div className="mt-2 text-xs text-muted-foreground">
            Found {filteredConversations.length} conversations, {filteredMessages.length} messages
          </div>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2">
          {/* Conversations */}
          {filteredConversations.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground px-3 py-1">
                CONVERSATIONS
              </div>
              {filteredConversations.map((conversation) => (
                <Button
                  key={conversation.id}
                  variant="ghost"
                  className="w-full justify-start gap-2 text-left h-auto p-3"
                  onClick={() => handleConversationClick(conversation.id)}
                >
                  <MessageSquare className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{conversation.title}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {conversation.lastMessage.toLocaleDateString()} • {conversation.messageCount} messages
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          )}

          {/* Messages */}
          {filteredMessages.length > 0 && searchQuery && (
            <>
              <div className="text-xs font-medium text-muted-foreground px-3 py-1 mt-4">
                MESSAGES
              </div>
              <div className="space-y-2">
                {filteredMessages.slice(0, 20).map((message) => (
                  <div
                    key={message.id}
                    className="bg-sidebar-accent/50 rounded-md p-3 cursor-pointer hover:bg-sidebar-accent transition-colors"
                    onClick={() => handleConversationClick(message.conversationId)}
                  >
                    <div className="flex items-start gap-2 mb-1">
                      {message.role === "user" ? (
                        <User className="h-4 w-4 mt-0.5 text-blue-500 flex-shrink-0" />
                      ) : (
                        <Bot className="h-4 w-4 mt-0.5 text-green-500 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-muted-foreground mb-1">
                          {message.conversationTitle}
                        </div>
                        <div className="text-sm truncate">
                          {message.content.replace(/[#*`]/g, "").substring(0, 100)}...
                        </div>
                        <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                          {message.model && <span>{message.model}</span>}
                          {message.searchUsed && <span>🔍</span>}
                          {message.deepThinking && <span>🧠</span>}
                          <Clock className="h-3 w-3" />
                          {message.timestamp.toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Empty State */}
          {searchQuery && filteredConversations.length === 0 && filteredMessages.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <div className="text-sm">No results found for "{searchQuery}"</div>
            </div>
          )}

          {/* Initial State */}
          {!searchQuery && (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <div className="text-sm">Search your chat history</div>
              <div className="text-xs">Type to find chats and messages</div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
