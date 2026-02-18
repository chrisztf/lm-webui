import React, { useState, useMemo } from 'react';
import { useReasoningStore } from '@/store/reasoningStore';
import { logger } from '@/utils/loggingService';

interface ReasoningBubbleMinimalProps {
  sessionId: string;
  mode?: 'minimal' | 'compact' | 'standard';
  defaultExpanded?: boolean;
}

export const ReasoningBubbleMinimal: React.FC<ReasoningBubbleMinimalProps> = ({
  sessionId,
  mode = 'minimal',
  defaultExpanded = false,
}) => {
  const session = useReasoningStore((state) => state.sessions[sessionId]);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isAnimating, setIsAnimating] = useState(false);

  // Performance optimization: Memoize content processing
  const processedContent = useMemo(() => {
    if (!session?.content) return '';
    
    const content = session.content;
    
    // For minimal mode, truncate very long content
    if (mode === 'minimal' && content.length > 2000) {
      return content.slice(0, 2000) + '\n...[content truncated for performance]';
    }
    
    // For compact mode, moderate truncation
    if (mode === 'compact' && content.length > 5000) {
      return content.slice(0, 5000) + '\n...[content truncated]';
    }
    
    return content;
  }, [session?.content, mode]);

  if (!session || !session.content) {
    logger.reasoning(`No session or content for sessionId: ${sessionId}`);
    return null;
  }

  const duration = session.metrics.duration || 0;
  const isThinking = session.isActive;
  const tokenCount = session.metrics.tokenCount || 0;
  const updateCount = session.metrics.updateCount || 0;

  const handleToggle = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setIsExpanded(!isExpanded);
    
    setTimeout(() => setIsAnimating(false), 300);
  };

  // Get mode-specific styling
  const getModeStyles = () => {
    switch (mode) {
      case 'minimal':
        return {
          container: 'border border-gray-200 dark:border-gray-800 rounded bg-gray-50/30 dark:bg-gray-900/20',
          header: 'px-2 py-1.5 cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-800/30',
          text: 'text-xs text-gray-600 dark:text-gray-400 font-mono leading-relaxed',
          icon: 'text-gray-500 dark:text-gray-400',
          duration: 'text-[10px] text-gray-400 dark:text-gray-500',
          content: 'px-2 py-1.5 border-t border-gray-100 dark:border-gray-800/50',
          thinkingIndicator: 'inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse'
        };
      case 'compact':
        return {
          container: 'border border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50/50 dark:bg-gray-900/30',
          header: 'px-3 py-2 cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-800/50',
          text: 'text-sm text-gray-700 dark:text-gray-300 font-sans leading-relaxed',
          icon: 'text-gray-600 dark:text-gray-300',
          duration: 'text-xs text-gray-500 dark:text-gray-400',
          content: 'px-3 py-2 border-t border-gray-200 dark:border-gray-700/50',
          thinkingIndicator: 'inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse'
        };
      default: // standard
        return {
          container: 'border border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900/40',
          header: 'px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800',
          text: 'text-sm text-gray-800 dark:text-gray-200 font-sans leading-relaxed',
          icon: 'text-gray-700 dark:text-gray-200',
          duration: 'text-xs text-gray-600 dark:text-gray-300',
          content: 'px-3 py-2 border-t border-gray-200 dark:border-gray-700',
          thinkingIndicator: 'inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse ml-1'
        };
    }
  };

  const styles = getModeStyles();

  return (
    <div className={`${styles.container} mb-3 transition-all duration-200`}>
      {/* Header - Always visible */}
      <div 
        className={`${styles.header} flex items-center justify-between transition-colors`}
        onClick={handleToggle}
        title={isExpanded ? "Click to collapse" : "Click to expand"}
      >
        <div className="flex items-center gap-1.5">
          {/* Thinking indicator */}
          {isThinking ? (
            <div className={styles.thinkingIndicator} title="Model is thinking" />
          ) : (
            <div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600" title="Thinking complete" />
          )}
          
          <span className={`${styles.text} font-medium`}>
            {isThinking ? 'Thinking...' : 'Thought Process'}
          </span>
          
          {/* Duration and stats */}
          <span className={styles.duration}>
            ({duration}s{tokenCount > 0 ? `, ${tokenCount}t` : ''})
          </span>
        </div>
        
        {/* Expand/collapse indicator */}
        <div className={styles.icon}>
          {isExpanded ? '▲' : '▼'}
        </div>
      </div>

      {/* Content - Animated expand/collapse */}
      <div 
        className={`${styles.content} overflow-hidden transition-all duration-300 ease-in-out`}
        style={{
          maxHeight: isExpanded ? '500px' : '0',
          opacity: isExpanded ? 1 : 0,
          paddingTop: isExpanded ? '0.5rem' : '0',
          paddingBottom: isExpanded ? '0.5rem' : '0'
        }}
      >
        <div 
          className={`${styles.text} whitespace-pre-wrap break-words overflow-y-auto max-h-[400px]`}
          style={{
            fontFamily: mode === 'minimal' ? 'monospace' : 'system-ui, sans-serif',
            fontSize: mode === 'minimal' ? '11px' : mode === 'compact' ? '12px' : '13px',
            lineHeight: mode === 'minimal' ? '1.4' : '1.5'
          }}
        >
          {processedContent}
          
          {/* Show if content was truncated */}
          {mode === 'minimal' && session.content.length > 2000 && (
            <div className="mt-1 text-[10px] text-gray-400 dark:text-gray-500 italic">
              Content truncated for performance. Full length: {session.content.length} chars
            </div>
          )}
          
          {/* Thinking indicator at the end if still active */}
          {isThinking && (
            <div className="mt-1 flex items-center gap-1">
              <div className={styles.thinkingIndicator} />
              <span className="text-[10px] text-gray-500 dark:text-gray-400">
                Model is still thinking...
              </span>
            </div>
          )}
        </div>
        
        {/* Performance stats in minimal mode */}
        {mode === 'minimal' && updateCount > 0 && (
          <div className="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
            Updates: {updateCount} | Tokens: {tokenCount}
          </div>
        )}
      </div>
    </div>
  );
};

// Performance-optimized version with React.memo
export const ReasoningBubbleMinimalMemo = React.memo(ReasoningBubbleMinimal, (prevProps, nextProps) => {
  // Only re-render if sessionId changes or mode changes
  return prevProps.sessionId === nextProps.sessionId && 
         prevProps.mode === nextProps.mode &&
         prevProps.defaultExpanded === nextProps.defaultExpanded;
});

export default ReasoningBubbleMinimal;