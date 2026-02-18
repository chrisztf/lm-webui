import React from 'react';
import { Brain, FileText, MessageSquare, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useContextStore } from '@/store/contextStore';
import { useChatStore } from '@/store/chatStore';
import { cn } from '@/lib/utils';

interface ContextSummaryBarProps {
  className?: string;
  onExpand?: () => void;
  showExpandButton?: boolean;
}

export function ContextSummaryBar({
  className,
  onExpand,
  showExpandButton = true
}: ContextSummaryBarProps) {
  const { activeContext, contextLoading } = useContextStore();
  const activeChatId = useChatStore(state => state.activeChatId);

  if (!activeContext || !activeContext.has_context) {
    return null;
  }

  const summaryItems = [];

  // Memory indicator
  if (activeContext.summaries && activeContext.summaries.length > 0) {
    summaryItems.push({
      icon: Brain,
      label: `${activeContext.summaries.length} memory`,
      color: 'text-purple-400',
    });
  }

  // File sources
  if (activeContext.file_chunks && activeContext.file_chunks.length > 0) {
    summaryItems.push({
      icon: FileText,
      label: `${activeContext.file_chunks.length} document`,
      color: 'text-blue-400',
    });
  }

  // Recent messages
  if (activeContext.recent_messages && activeContext.recent_messages.length > 0) {
    summaryItems.push({
      icon: MessageSquare,
      label: `${activeContext.recent_messages.length} message`,
      color: 'text-green-400',
    });
  }

  // Search indicator (if we add search functionality later)
  // if (hasSearchResults) {
  //   summaryItems.push({
  //     icon: Search,
  //     label: 'web search',
  //     color: 'text-orange-400',
  //   });
  // }

  if (summaryItems.length === 0) {
    return null;
  }

  return (
    <div className={cn(
      "flex items-center justify-center gap-2 px-3 py-2 bg-zinc-800/50 backdrop-blur-sm border border-zinc-700/50 rounded-full mx-4 mb-2",
      className
    )}>
      {/* Context Icon */}
      <Brain className="h-4 w-4 text-purple-400" />

      {/* Summary Items */}
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        {summaryItems.map((item, index) => (
          <div key={index} className="flex items-center gap-1">
            <item.icon className={cn("h-3 w-3", item.color)} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Total Items Badge */}
      <Badge variant="secondary" className="text-xs px-2 py-0">
        {activeContext.total_items}
      </Badge>

      {/* Expand Button */}
      {showExpandButton && onExpand && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onExpand}
          className="h-6 w-6 p-0 ml-2 text-muted-foreground hover:text-foreground"
          title="View full context"
        >
          <Search className="h-3 w-3" />
        </Button>
      )}

      {/* Loading Indicator */}
      {contextLoading && (
        <div className="ml-2 w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      )}
    </div>
  );
}

export default ContextSummaryBar;
