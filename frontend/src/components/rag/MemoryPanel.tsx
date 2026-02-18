import React, { useEffect } from 'react';
import { Brain, FileText, MessageSquare, Trash2, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useContextStore } from '@/store/contextStore';
import { useChatStore } from '@/store/chatStore';
import { cn } from '@/lib/utils';

interface MemoryPanelProps {
  className?: string;
}

export function MemoryPanel({ className }: MemoryPanelProps) {
  const {
    activeContext,
    contextLoading,
    memoryDeleting,
    fetchActiveContext,
    forgetMemory,
  } = useContextStore();

  const activeChatId = useChatStore(state => state.activeChatId);

  // Fetch context when conversation changes
  useEffect(() => {
    if (activeChatId) {
      fetchActiveContext(activeChatId);
    }
  }, [activeChatId, fetchActiveContext]);

  const handleForgetMemory = async (memoryId: string) => {
    if (activeChatId) {
      await forgetMemory(activeChatId, memoryId);
    }
  };

  const handleRefresh = () => {
    if (activeChatId) {
      fetchActiveContext(activeChatId);
    }
  };

  if (!activeContext || !activeContext.has_context) {
    return (
      <Card className={cn("w-80 h-fit", className)}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Brain className="h-5 w-5 text-purple-500" />
            Active Memory
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            <Brain className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No active context</p>
            <p className="text-xs mt-1">Summaries and file memories will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-80 h-fit max-h-[600px]", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Brain className="h-5 w-5 text-purple-500" />
            Active Memory
            <Badge variant="secondary" className="text-xs">
              {activeContext.total_items}
            </Badge>
          </CardTitle>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleRefresh}
            disabled={contextLoading}
            className="h-8 w-8 p-0"
          >
            <RefreshCw className={cn("h-4 w-4", contextLoading && "animate-spin")} />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <ScrollArea className="max-h-[500px]">
          <div className="p-4 space-y-4">
            {/* Conversation Summaries */}
            {activeContext.summaries && activeContext.summaries.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-purple-600 mb-2 flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  Summaries
                </h4>
                <div className="space-y-2">
                  {activeContext.summaries.map((summary, index) => (
                    <div
                      key={summary.id || index}
                      className="p-3 bg-purple-50 dark:bg-purple-950/20 rounded-lg border border-purple-200 dark:border-purple-800"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-purple-900 dark:text-purple-100 flex-1">
                          {summary.content}
                        </p>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleForgetMemory(summary.id)}
                          disabled={memoryDeleting}
                          className="h-6 w-6 p-0 text-purple-600 hover:text-purple-800 hover:bg-purple-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                      {summary.similarity && (
                        <div className="mt-2 text-xs text-purple-600">
                          Similarity: {(summary.similarity * 100).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <Separator className="my-4" />
              </div>
            )}

            {/* File Chunks */}
            {activeContext.file_chunks && activeContext.file_chunks.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-blue-600 mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  File Memories
                </h4>
                <div className="space-y-2">
                  {activeContext.file_chunks.map((chunk, index) => (
                    <div
                      key={chunk.id || index}
                      className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText className="h-3 w-3 text-blue-600" />
                            <span className="text-xs font-medium text-blue-900 dark:text-blue-100">
                              {chunk.filename || 'Unknown file'}
                            </span>
                          </div>
                          <p className="text-sm text-blue-900 dark:text-blue-100">
                            {chunk.content}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleForgetMemory(chunk.id)}
                          disabled={memoryDeleting}
                          className="h-6 w-6 p-0 text-blue-600 hover:text-blue-800 hover:bg-blue-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                      {chunk.similarity && (
                        <div className="mt-2 text-xs text-blue-600">
                          Similarity: {(chunk.similarity * 100).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <Separator className="my-4" />
              </div>
            )}

            {/* Recent Messages */}
            {activeContext.recent_messages && activeContext.recent_messages.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-green-600 mb-2 flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Recent Messages
                </h4>
                <div className="space-y-2">
                  {activeContext.recent_messages.slice(0, 3).map((message, index) => (
                    <div
                      key={index}
                      className="p-3 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant={message.role === 'user' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {message.role === 'user' ? 'You' : 'Assistant'}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {message.created_at ? new Date(message.created_at).toLocaleTimeString() : 'Unknown time'}
                        </span>
                      </div>
                      <p className="text-sm text-green-900 dark:text-green-100 line-clamp-2">
                        {message.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {(!activeContext.summaries?.length && !activeContext.file_chunks?.length && !activeContext.recent_messages?.length) && (
              <div className="text-center text-muted-foreground py-8">
                <Brain className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No active context</p>
                <p className="text-xs mt-1">Context will appear as you chat</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default MemoryPanel;
