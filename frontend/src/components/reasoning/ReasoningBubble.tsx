import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Brain } from 'lucide-react';
import { useReasoningStore } from '@/store/reasoningStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReasoningBubbleProps {
  sessionId: string;
}

export const ReasoningBubble: React.FC<ReasoningBubbleProps> = ({
  sessionId,
}) => {
  const session = useReasoningStore((state) => state.sessions[sessionId]);
  const [isExpanded, setIsExpanded] = useState(false);

  if (!session || !session.content) return null;

  const duration = session.metrics.duration || 0;
  const isThinking = session.isActive;

  return (
    <div className="mb-4 border border-zinc-200 dark:border-zinc-800/50 rounded-lg overflow-hidden bg-zinc-50/50 dark:bg-zinc-900/30 w-full max-w-full">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-zinc-100/50 dark:hover:bg-zinc-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 text-sm">
          <Brain className={`w-4 h-4 ${isThinking ? 'text-indigo-500 animate-pulse' : 'text-zinc-500'}`} />
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            {isThinking ? 'Thinking...' : 'Thought Process'}
          </span>
          <span className="text-zinc-400 text-xs ml-1">
            ({duration}s)
          </span>
        </div>
        
        <div className="flex items-center">
          {isExpanded ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pb-4 pt-2 border-t border-zinc-100 dark:border-zinc-800/50"
          >
            <div className="prose prose-sm dark:prose-invert max-w-none text-zinc-600 dark:text-zinc-400 leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {session.content}
              </ReactMarkdown>
              {isThinking && (
                 <span className="inline-block w-2 h-4 ml-1 bg-indigo-500 animate-pulse align-middle" />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
