import React from 'react';
import { motion } from 'framer-motion';
import { Search, Brain, Zap, CheckCircle, Clock, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ReasoningStatusType = 
  | 'searching' 
  | 'analyzing' 
  | 'enhancing' 
  | 'thinking' 
  | 'complete'
  | 'loading';

export interface ReasoningStatusProps {
  status: ReasoningStatusType;
  duration?: number; // in seconds
  message?: string;
  isSearchEnabled?: boolean;
  isDeepThinkingMode?: boolean;
  className?: string;
}

export const ReasoningStatus: React.FC<ReasoningStatusProps> = ({
  status,
  duration = 0,
  message,
  isSearchEnabled = false,
  isDeepThinkingMode = false,
  className
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'searching':
        return {
          icon: Search,
          label: 'Searching...',
          color: 'text-blue-500',
          bgColor: 'bg-blue-100 dark:bg-blue-900/30',
          description: isSearchEnabled 
            ? 'Searching the web for relevant information'
            : 'Gathering information from knowledge base'
        };
      case 'analyzing':
        return {
          icon: Brain,
          label: 'Analyzing...',
          color: 'text-purple-500',
          bgColor: 'bg-purple-100 dark:bg-purple-900/30',
          description: 'Processing information and identifying key insights'
        };
      case 'enhancing':
        return {
          icon: Zap,
          label: 'Enhancing answer...',
          color: 'text-amber-500',
          bgColor: 'bg-amber-100 dark:bg-amber-900/30',
          description: 'Refining response with additional context and clarity'
        };
      case 'thinking':
        return {
          icon: Brain,
          label: `Thinking${duration > 0 ? ` for ${duration}s` : '...'}`,
          color: 'text-indigo-500',
          bgColor: 'bg-indigo-100 dark:bg-indigo-900/30',
          description: isDeepThinkingMode
            ? 'Engaging in deep reasoning process'
            : 'Processing your request'
        };
      case 'loading':
        return {
          icon: Loader2,
          label: 'Loading...',
          color: 'text-gray-500',
          bgColor: 'bg-gray-100 dark:bg-gray-900/30',
          description: 'Preparing response'
        };
      case 'complete':
        return {
          icon: CheckCircle,
          label: 'Complete',
          color: 'text-green-500',
          bgColor: 'bg-green-100 dark:bg-green-900/30',
          description: 'Response ready'
        };
      default:
        return {
          icon: Brain,
          label: 'Processing...',
          color: 'text-gray-500',
          bgColor: 'bg-gray-100 dark:bg-gray-900/30',
          description: 'Processing your request'
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all",
      config.bgColor,
      "border-transparent",
      className
    )}>
      <motion.div
        animate={status === 'loading' || status === 'thinking' ? { rotate: 360 } : {}}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className={cn("flex-shrink-0", config.color)}
      >
        <Icon className="w-4 h-4" />
      </motion.div>
      
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-medium", config.color)}>
            {config.label}
          </span>
          {duration > 0 && status === 'thinking' && (
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>{duration}s</span>
            </div>
          )}
        </div>
        
        {(message || config.description) && (
          <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
            {message || config.description}
          </p>
        )}
      </div>
    </div>
  );
};

// Status indicator with progress steps (like DeepSeek/Gemini)
export interface ReasoningProgressProps {
  currentStep: number;
  totalSteps: number;
  steps: Array<{
    label: string;
    status: 'pending' | 'active' | 'complete';
    icon?: React.ReactNode;
  }>;
  className?: string;
}

export const ReasoningProgress: React.FC<ReasoningProgressProps> = ({
  currentStep,
  totalSteps,
  steps,
  className
}) => {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Reasoning Process
          </span>
        </div>
        <span className="text-xs text-gray-500">
          Step {currentStep} of {totalSteps}
        </span>
      </div>
      
      <div className="flex items-center gap-1">
        {steps.map((step, index) => (
          <React.Fragment key={index}>
            <div className={cn(
              "flex-1 h-1.5 rounded-full transition-all",
              step.status === 'complete' && "bg-green-500",
              step.status === 'active' && "bg-indigo-500 animate-pulse",
              step.status === 'pending' && "bg-gray-200 dark:bg-gray-800"
            )} />
            {index < steps.length - 1 && (
              <div className="w-2 h-0.5 bg-gray-300 dark:bg-gray-700" />
            )}
          </React.Fragment>
        ))}
      </div>
      
      <div className="flex justify-between">
        {steps.map((step, index) => (
          <div
            key={index}
            className={cn(
              "flex flex-col items-center text-center",
              "transition-all",
              step.status === 'active' && "scale-105"
            )}
            style={{ width: `${100 / steps.length}%` }}
          >
            <div className={cn(
              "w-6 h-6 rounded-full flex items-center justify-center mb-1",
              "transition-all",
              step.status === 'complete' && "bg-green-100 dark:bg-green-900/30 text-green-600",
              step.status === 'active' && "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 animate-pulse",
              step.status === 'pending' && "bg-gray-100 dark:bg-gray-800 text-gray-400"
            )}>
              {step.icon || (
                <span className="text-xs font-medium">
                  {index + 1}
                </span>
              )}
            </div>
            <span className={cn(
              "text-xs truncate max-w-full",
              step.status === 'complete' && "text-green-600 font-medium",
              step.status === 'active' && "text-indigo-600 font-medium",
              step.status === 'pending' && "text-gray-500"
            )}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};