import React from 'react';
import { Settings, Zap, Gauge, Bug, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useUISettings, ReasoningUIMode } from '@/store/settingsStore';
import { logger } from '@/utils/loggingService';

export const ReasoningModeSelector: React.FC = () => {
  const settings = useUISettings();
  
  const handleModeChange = (mode: ReasoningUIMode) => {
    settings.setReasoningUIMode(mode);
    logger.ui(`Switched reasoning UI mode to: ${mode}`);
    
    // Apply additional optimizations for minimal mode
    if (mode === 'minimal') {
      settings.setReasoningDefaultExpanded(false);
      settings.setReasoningShowMetrics(false);
      settings.setEnableTokenBatching(true);
      settings.setBatchSize(5);
    }
    
    // Apply debug settings for detailed mode
    if (mode === 'detailed') {
      settings.setReasoningDefaultExpanded(true);
      settings.setReasoningShowMetrics(true);
      settings.setEnableTokenBatching(false);
    }
  };
  
  const getModeIcon = (mode: ReasoningUIMode) => {
    switch (mode) {
      case 'minimal': return <Zap className="h-4 w-4" />;
      case 'compact': return <Gauge className="h-4 w-4" />;
      case 'standard': return <Settings className="h-4 w-4" />;
      case 'detailed': return <Bug className="h-4 w-4" />;
      default: return <Settings className="h-4 w-4" />;
    }
  };
  
  const getModeDescription = (mode: ReasoningUIMode) => {
    switch (mode) {
      case 'minimal': return 'Maximum performance, minimal UI';
      case 'compact': return 'Balanced performance and features';
      case 'standard': return 'Default experience';
      case 'detailed': return 'Full features for debugging';
      default: return '';
    }
  };
  
  const getModeColor = (mode: ReasoningUIMode) => {
    switch (mode) {
      case 'minimal': return 'text-blue-500';
      case 'compact': return 'text-green-500';
      case 'standard': return 'text-gray-500';
      case 'detailed': return 'text-purple-500';
      default: return 'text-gray-500';
    }
  };
  
  const toggleDefaultExpanded = () => {
    settings.setReasoningDefaultExpanded(!settings.reasoningDefaultExpanded);
  };
  
  const toggleShowMetrics = () => {
    settings.setReasoningShowMetrics(!settings.reasoningShowMetrics);
  };
  
  const toggleLogging = () => {
    const currentLevel = settings.loggingLevel;
    const nextLevel = currentLevel === 'debug' ? 'warn' : 'debug';
    settings.setLoggingLevel(nextLevel);
    logger.ui(`Switched logging level to: ${nextLevel}`);
  };
  
  return (
    <div className="flex flex-col gap-3 p-4 border rounded-lg bg-background">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Reasoning UI Mode</h3>
        <span className={`text-xs font-medium ${getModeColor(settings.reasoningUIMode)}`}>
          {settings.reasoningUIMode.toUpperCase()}
        </span>
      </div>
      
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            {getModeIcon(settings.reasoningUIMode)}
            <span className="capitalize">{settings.reasoningUIMode} Mode</span>
            <span className="ml-auto text-xs text-muted-foreground">
              {settings.isPerformanceMode ? '⚡ Performance' : '⚙️ Standard'}
            </span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Select UI Mode</DropdownMenuLabel>
          <DropdownMenuSeparator />
          
          {(['minimal', 'compact', 'standard', 'detailed'] as ReasoningUIMode[]).map((mode) => (
            <DropdownMenuItem
              key={mode}
              onClick={() => handleModeChange(mode)}
              className="flex items-center gap-2 cursor-pointer"
            >
              {getModeIcon(mode)}
              <div className="flex flex-col">
                <span className="font-medium capitalize">{mode} Mode</span>
                <span className="text-xs text-muted-foreground">
                  {getModeDescription(mode)}
                </span>
              </div>
              {settings.reasoningUIMode === mode && (
                <span className="ml-auto text-xs text-primary">✓</span>
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-sm">Quick Actions</span>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleDefaultExpanded}
            className="flex items-center gap-2"
          >
            {settings.reasoningDefaultExpanded ? (
              <EyeOff className="h-3 w-3" />
            ) : (
              <Eye className="h-3 w-3" />
            )}
            <span className="text-xs">
              {settings.reasoningDefaultExpanded ? 'Collapsed' : 'Expanded'}
            </span>
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={toggleShowMetrics}
            className="flex items-center gap-2"
          >
            <Gauge className="h-3 w-3" />
            <span className="text-xs">
              {settings.reasoningShowMetrics ? 'Hide Stats' : 'Show Stats'}
            </span>
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={toggleLogging}
            className="flex items-center gap-2"
          >
            <Bug className="h-3 w-3" />
            <span className="text-xs">
              {settings.loggingLevel === 'debug' ? 'Less Logs' : 'More Logs'}
            </span>
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={settings.togglePerformanceMode}
            className="flex items-center gap-2"
          >
            <Zap className="h-3 w-3" />
            <span className="text-xs">
              {settings.isPerformanceMode ? 'Standard' : 'Performance'}
            </span>
          </Button>
        </div>
      </div>
      
      <div className="text-xs text-muted-foreground mt-2">
        <p>
          <strong>Minimal mode</strong> reduces UI complexity for better performance during token streaming.
        </p>
        <p className="mt-1">
          Current settings: {settings.batchSize}x batching, {settings.debounceDelay}ms debounce
        </p>
      </div>
    </div>
  );
};

export default ReasoningModeSelector;