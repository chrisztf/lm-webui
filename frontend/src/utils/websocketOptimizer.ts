import { logger } from './loggingService';
import { isTokenBatchingEnabled, getBatchSize, isDebouncedUpdatesEnabled, getDebounceDelay } from '@/store/settingsStore';

export interface TokenBatch {
  sessionId: string;
  tokens: string[];
  timestamp: number;
}

export interface ProcessingMetrics {
  totalTokensProcessed: number;
  batchesProcessed: number;
  averageBatchSize: number;
  averageProcessingTime: number;
  peakQueueSize: number;
}

class WebSocketOptimizer {
  private tokenQueue: Map<string, string[]> = new Map();
  private batchTimers: Map<string, NodeJS.Timeout> = new Map();
  private processingQueue: TokenBatch[] = [];
  private isProcessing = false;
  private animationFrameId: number | null = null;
  
  private metrics: ProcessingMetrics = {
    totalTokensProcessed: 0,
    batchesProcessed: 0,
    averageBatchSize: 0,
    averageProcessingTime: 0,
    peakQueueSize: 0
  };
  
  private processingTimes: number[] = [];
  
  constructor() {
    // Start metrics collection
    this.startMetricsCollection();
  }
  
  processToken(sessionId: string, token: string, callback: (batch: TokenBatch) => void): void {
    const startTime = performance.now();
    
    // Get current settings
    const shouldBatch = isTokenBatchingEnabled();
    const batchSize = getBatchSize();
    const shouldDebounce = isDebouncedUpdatesEnabled();
    const debounceDelay = getDebounceDelay();
    
    if (!shouldBatch || batchSize <= 1) {
      // No batching, process immediately
      const batch: TokenBatch = {
        sessionId,
        tokens: [token],
        timestamp: Date.now()
      };
      
      if (shouldDebounce) {
        this.scheduleDebouncedUpdate(() => callback(batch), debounceDelay);
      } else {
        callback(batch);
      }
      
      this.updateMetrics(1, performance.now() - startTime);
      return;
    }
    
    // Add token to queue
    if (!this.tokenQueue.has(sessionId)) {
      this.tokenQueue.set(sessionId, []);
    }
    
    const queue = this.tokenQueue.get(sessionId)!;
    queue.push(token);
    
    // Update peak queue size
    this.metrics.peakQueueSize = Math.max(this.metrics.peakQueueSize, queue.length);
    
    // Check if we should process the batch
    if (queue.length >= batchSize) {
      this.processBatch(sessionId, callback);
      return;
    }
    
    // Schedule batch processing if not already scheduled
    if (!this.batchTimers.has(sessionId)) {
      const timer = setTimeout(() => {
        this.processBatch(sessionId, callback);
        this.batchTimers.delete(sessionId);
      }, 100); // Maximum wait time for batching
      
      this.batchTimers.set(sessionId, timer);
    }
    
    this.updateMetrics(0, performance.now() - startTime);
  }
  
  private processBatch(sessionId: string, callback: (batch: TokenBatch) => void): void {
    const queue = this.tokenQueue.get(sessionId);
    if (!queue || queue.length === 0) {
      return;
    }
    
    // Clear any pending timer
    const timer = this.batchTimers.get(sessionId);
    if (timer) {
      clearTimeout(timer);
      this.batchTimers.delete(sessionId);
    }
    
    // Create batch
    const batch: TokenBatch = {
      sessionId,
      tokens: [...queue],
      timestamp: Date.now()
    };
    
    // Clear queue
    this.tokenQueue.set(sessionId, []);
    
    // Add to processing queue
    this.processingQueue.push(batch);
    
    // Start processing if not already processing
    if (!this.isProcessing) {
      this.processQueue(callback);
    }
  }
  
  private processQueue(callback: (batch: TokenBatch) => void): void {
    if (this.processingQueue.length === 0) {
      this.isProcessing = false;
      return;
    }
    
    this.isProcessing = true;
    
    // Use requestAnimationFrame for smooth rendering
    this.animationFrameId = requestAnimationFrame(() => {
      const startTime = performance.now();
      
      // Process one batch per frame for smoothness
      const batch = this.processingQueue.shift();
      if (batch) {
        callback(batch);
        this.updateMetrics(batch.tokens.length, performance.now() - startTime);
      }
      
      // Continue processing if there are more batches
      if (this.processingQueue.length > 0) {
        this.processQueue(callback);
      } else {
        this.isProcessing = false;
        this.animationFrameId = null;
      }
    });
  }
  
  private scheduleDebouncedUpdate(callback: () => void, delay: number): void {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    
    this.animationFrameId = requestAnimationFrame(() => {
      setTimeout(callback, delay);
      this.animationFrameId = null;
    });
  }
  
  private updateMetrics(tokensProcessed: number, processingTime: number): void {
    this.metrics.totalTokensProcessed += tokensProcessed;
    
    if (tokensProcessed > 0) {
      this.metrics.batchesProcessed++;
      this.processingTimes.push(processingTime);
      
      // Update average batch size
      this.metrics.averageBatchSize = 
        (this.metrics.averageBatchSize * (this.metrics.batchesProcessed - 1) + tokensProcessed) / 
        this.metrics.batchesProcessed;
      
      // Update average processing time
      const totalTime = this.processingTimes.reduce((a, b) => a + b, 0);
      this.metrics.averageProcessingTime = totalTime / this.processingTimes.length;
    }
  }
  
  private startMetricsCollection(): void {
    setInterval(() => {
      if (this.metrics.totalTokensProcessed > 0) {
        logger.performance('WebSocket Optimizer Metrics', {
          ...this.metrics,
          currentQueueSize: Array.from(this.tokenQueue.values()).reduce((sum, queue) => sum + queue.length, 0),
          processingQueueSize: this.processingQueue.length,
          isProcessing: this.isProcessing
        });
      }
    }, 10000); // Log every 10 seconds
  }
  
  getMetrics(): ProcessingMetrics {
    return { ...this.metrics };
  }
  
  resetMetrics(): void {
    this.metrics = {
      totalTokensProcessed: 0,
      batchesProcessed: 0,
      averageBatchSize: 0,
      averageProcessingTime: 0,
      peakQueueSize: 0
    };
    this.processingTimes = [];
  }
  
  cleanup(): void {
    // Clear all timers
    for (const timer of this.batchTimers.values()) {
      clearTimeout(timer);
    }
    this.batchTimers.clear();
    
    // Cancel animation frame
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    // Clear queues
    this.tokenQueue.clear();
    this.processingQueue = [];
    this.isProcessing = false;
    
    logger.performance('WebSocket Optimizer cleaned up');
  }
  
  flush(sessionId: string, callback: (batch: TokenBatch) => void): void {
    const queue = this.tokenQueue.get(sessionId);
    if (queue && queue.length > 0) {
      this.processBatch(sessionId, callback);
    }
    
    // Clear timer
    const timer = this.batchTimers.get(sessionId);
    if (timer) {
      clearTimeout(timer);
      this.batchTimers.delete(sessionId);
    }
  }
  
  getQueueSize(sessionId: string): number {
    return this.tokenQueue.get(sessionId)?.length || 0;
  }
  
  getTotalQueueSize(): number {
    return Array.from(this.tokenQueue.values()).reduce((sum, queue) => sum + queue.length, 0);
  }
}

// Export singleton instance
export const websocketOptimizer = new WebSocketOptimizer();

// Helper functions for common use cases
export const optimizeTokenProcessing = (
  sessionId: string,
  token: string,
  onBatchProcessed: (batch: TokenBatch) => void
): void => {
  websocketOptimizer.processToken(sessionId, token, onBatchProcessed);
};

export const flushPendingTokens = (
  sessionId: string,
  onBatchProcessed: (batch: TokenBatch) => void
): void => {
  websocketOptimizer.flush(sessionId, onBatchProcessed);
};

export const getOptimizerMetrics = (): ProcessingMetrics => {
  return websocketOptimizer.getMetrics();
};

export const cleanupOptimizer = (): void => {
  websocketOptimizer.cleanup();
};