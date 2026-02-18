import { useMemo, useState, useRef, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Zap, Database, Wifi,WifiOff, ChevronDown, Bot, Cpu, Brain, Code, Sparkles, HardDrive, Gem, Search, Eye } from "lucide-react";

interface ModelSelectorProps {
  selectedLLM: string;
  selectedModel: string;
  availableModels: string[];
  onModelChange: (model: string) => void;
  onLLMChange: (llm: string) => void;
  connectionStatus?: "connected" | "disconnected" | "testing";
  providerGroups?: Array<{
    provider: string;
    models: string[];
    modelMapping?: Record<string, string>;
  }>;
}

// Provider configuration with icons
const providerConfig = {
  openai: { name: "OpenAI", icon: Zap, color: "text-green-500" },
  google: { name: "Google Gemini", icon: Gem, color: "text-blue-500" },
  xai: { name: "xAI Grok", icon: Brain, color: "text-red-500" },
  anthropic: { name: "Anthropic Claude", icon: Code, color: "text-orange-500" },
  deepseek: { name: "DeepSeek", icon: Sparkles, color: "text-purple-500" },
  zhipu: { name: "Zhipu AI", icon: Cpu, color: "text-indigo-500" },
  ollama: { name: "Ollama", icon: Database, color: "text-cyan-500" },
  lmstudio: { name: "LM Studio", icon: Cpu, color: "text-yellow-500" },
  gguf: { name: "GGUF", icon: HardDrive, color: "text-gray-500" },
};

// Helper function to parse prefixed model names
const parsePrefixedModel = (prefixedModel: string): { provider: string; model: string } => {
  const [provider, ...modelParts] = prefixedModel.split(":");
  return {
    provider: provider || "",
    model: modelParts.join(":") || prefixedModel
  };
};

export function ModelSelector({
  selectedLLM,
  selectedModel,
  availableModels,
  onModelChange,
  onLLMChange,
  connectionStatus = "connected",
  providerGroups = [],
}: ModelSelectorProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const providerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const providerModelGroupRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const modelsContainerRef = useRef<HTMLDivElement>(null);

  // Group all models by provider and filter out hidden ones
  const groupedModels = useMemo(() => {
    const groups: Record<string, { models: string[]; isConnected: boolean }> = {};
    
    // Initialize all provider groups
    Object.keys(providerConfig).forEach(provider => {
      const group = providerGroups?.find((p: any) => p.provider === provider);
      const isConnected = !!(group && group.models && group.models.length > 0);
      groups[provider] = { models: [], isConnected };
    });

    // Process all available models (which are prefixed with provider:model)
    availableModels.forEach(prefixedModel => {
      const { provider, model } = parsePrefixedModel(prefixedModel);
      
      // Check if model is hidden in localStorage
      const modelId = `${provider}:${model}`;
      const isHidden = localStorage.getItem(`model-visibility-${modelId}`) === 'false';
      
      if (!isHidden && groups[provider]) {
        groups[provider].models.push(model);
      }
    });

    return groups;
  }, [availableModels, providerGroups]);

  // Get total visible models count
  const totalVisibleModels = useMemo(() => {
    return Object.values(groupedModels).reduce((total, group) => total + group.models.length, 0);
  }, [groupedModels]);

  // Filter models based on search query
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return groupedModels;

    const filtered: typeof groupedModels = {};
    Object.entries(groupedModels).forEach(([provider, data]) => {
      const filteredModels = data.models.filter(model =>
        model.toLowerCase().includes(searchQuery.toLowerCase()) ||
        providerConfig[provider as keyof typeof providerConfig]?.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
      if (filteredModels.length > 0) {
        filtered[provider] = { ...data, models: filteredModels };
      }
    });
    return filtered;
  }, [groupedModels, searchQuery]);

  const getProviderIcon = (provider: string) => {
    const config = providerConfig[provider as keyof typeof providerConfig];
    if (config) {
      const Icon = config.icon;
      return <Icon className={`h-4 w-4 ${config.color}`} />;
    }
    return <Bot className="h-4 w-4" />;
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case "connected":
        return <Wifi className="h-3 w-3 text-green-500" />;
      case "testing":
        return <Wifi className="h-3 w-3 text-yellow-500 animate-pulse" />;
      default:
        return <WifiOff className="h-3 w-3 text-red-500" />;
    }
  };

  const formatModelName = (model: string) => {
    if (!model || model === "Select Model") {
      return "Select Model";
    }
    if (model.length > 20) {
      return model.substring(0, 20) + "...";
    }
    return model;
  };

  const handleModelSelect = (provider: string, model: string) => {
    // When selecting a model, we need to update both the provider and model
    if (provider !== selectedLLM) {
      onLLMChange(provider);
    }
    onModelChange(model);
    setIsOpen(false);
  };

  const handleProviderSelect = (provider: string) => {
    onLLMChange(provider);
    // Clear search when changing provider
    setSearchQuery("");
    
    // Scroll to the provider's model group in the models section
    setTimeout(() => {
      if (providerModelGroupRefs.current[provider] && modelsContainerRef.current) {
        const groupElement = providerModelGroupRefs.current[provider];
        const container = modelsContainerRef.current;
        
        if (groupElement && container) {
          const groupTop = groupElement.offsetTop;
          
          // Calculate scroll position to show the group at the top of the container
          const targetScrollTop = groupTop - container.offsetTop - 10; // 10px padding
          
          // Smooth scroll to the calculated position
          container.scrollTo({
            top: targetScrollTop,
            behavior: 'smooth'
          });
        }
      }
    }, 100); // Small delay to ensure DOM is updated
  };

  // Scroll to selected provider when popover opens
  useEffect(() => {
    if (isOpen && scrollContainerRef.current && providerRefs.current[selectedLLM]) {
      const selectedButton = providerRefs.current[selectedLLM];
      const container = scrollContainerRef.current;
      
      if (selectedButton && container) {
        const buttonLeft = selectedButton.offsetLeft;
        const buttonWidth = selectedButton.offsetWidth;
        const containerWidth = container.offsetWidth;
        
        // Calculate scroll position to center the button
        const targetScrollLeft = buttonLeft - (containerWidth / 2) + (buttonWidth / 2);
        
        // Smooth scroll to the calculated position
        container.scrollTo({
          left: targetScrollLeft,
          behavior: 'smooth'
        });
      }
    }
  }, [isOpen, selectedLLM]);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="gap-1 md:gap-2 min-w-[70px] md:min-w-[140px] justify-between bg rounded-3xl 
          bg-neutral-100/90 dark:bg-black/5 border-slate-500/10 hover:bg-neutral-800/50 shadow-inner"
          size="sm"
        >
          <div className="flex items-center gap-1 md:gap-2">
            {getProviderIcon(selectedLLM)}
            <span className="text-[0.7rem] md:text-sm font-medium whitespace-nowrap overflow-hidden">
              {formatModelName(selectedModel)}
            </span>
          </div>
          <div className="flex items-center gap-0.5 md:gap-1">
            {getConnectionIcon()}
            <ChevronDown className="h-1 w-1 md:h-3 md:w-3" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="bg-neutral-300/70 dark:bg-neutral-900/90 backdrop-blur-md w-80 md:w-96 p-0 mt-4 mr-7 rounded-3xl border border-white/10" align="start">
        <div className="p-4 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-black/90 dark:text-gray-400" />
            <Input
              type="text"
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/5 border-white/10 text-black/80 dark:text-white/80 placeholder:text-white/50 rounded-2xl outline-none"
            />
          </div>

          {/* Provider Quick Select - Horizontal Scrollable Carousel */}
          <div className="space-y-2">
            <h4 className="font-medium text-sm text-black/80 dark:text-white/80">Providers</h4>
            <div className="relative">
              {/* Left fade gradient */}
              <div className="absolute left-0 top-0 bottom-0 w-6 bg-gradient-to-r from-white/20 dark:from-neutral-950 to-transparent z-10 pointer-events-none" />
              
              {/* Scrollable container */}
              <div 
                ref={scrollContainerRef}
                className="flex gap-2 overflow-x-auto pb-2 [&::-webkit-scrollbar]:h-0 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-transparent"
              >
                {Object.entries(providerConfig).map(([providerId, config]) => {
                  const group = providerGroups?.find((p: any) => p.provider === providerId);
                  const isConnected = group && group.models && group.models.length > 0;
                  
                  
                  return (
                    <Button
                      key={providerId}
                      ref={(el) => {
                        providerRefs.current[providerId] = el;
                      }}
                      variant={selectedLLM === providerId ? "default" : "outline"}
                      size="sm"
                      onClick={() => handleProviderSelect(providerId)}
                      className={`flex-shrink-0 gap-2 rounded-2xl ${selectedLLM === providerId ? 'bg-white/90 text-black' : 'bg-white/10'}`}
                    >
                      <span className="text-xs whitespace-nowrap">{config.name.split(' ')[0]}</span>
                      {isConnected ? (
                        <Wifi className="h-2 w-2 text-green-500 flex-shrink-0" />
                      ) : (
                        <WifiOff className="h-2 w-2 text-red-500/50 flex-shrink-0" />
                      )}
                    </Button>
                  );
                })}
              </div>
              
              {/* Right fade gradient */}
              <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-l from-white/20 dark:from-neutral-950 to-transparent z-10 pointer-events-none" />
            </div>
          </div>

          {/* Models List */}
          <div ref={modelsContainerRef} className="space-y-3 max-h-60 overflow-y-auto">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm text-black/80 dark:text-white/80">Models</h4>
              <Badge variant="outline" className="text-[0.6rem]">
                {totalVisibleModels} visible
              </Badge>
            </div>

            {Object.entries(filteredGroups).map(([provider, data]) => {
              if (data.models.length === 0) return null;
              
              const config = providerConfig[provider as keyof typeof providerConfig];
              const Icon = config?.icon || Bot;

              return (
                <div 
                  key={provider} 
                  ref={(el) => {
                    providerModelGroupRefs.current[provider] = el;
                  }}
                  className="space-y-2"
                >
                  <div className="flex items-center gap-2 text-xs text-black/80 dark:text-white/60">
                    <Icon className="h-3 w-3" />
                    <span>{config?.name || provider}</span>
                    <Badge variant="outline" className="text-[0.5rem] ml-auto">
                      {data.models.length}
                    </Badge>
                  </div>
                  
                  <div className="space-y-1 pl-4">
                    {data.models.map((model) => (
                      <div
                        key={model}
                        className={`flex items-center justify-between p-2 rounded-xl cursor-pointer transition-colors ${
                          selectedModel === model
                            ? 'bg-white/20 border border-white/20'
                            : 'bg-white/5 hover:bg-white/10 border border-transparent'
                        }`}
                        onClick={() => handleModelSelect(provider, model)}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Cpu className="h-3 w-3 text-black/80 dark:text-white/60" />
                          <span className="text-sm truncate">{model}</span>
                        </div>
                        {selectedModel === model && (
                          <Badge variant="default" className="text-[0.5rem] h-4 rounded-2xl">
                            Active
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {Object.values(filteredGroups).every(group => group.models.length === 0) && (
              <div className="text-center py-4 text-white/50">
                <div className="text-sm">No models found</div>
                {searchQuery && (
                  <div className="text-xs mt-1">Try a different search term</div>
                )}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="pt-4 border-t border-white/10">
            <div className="flex items-center justify-between text-xs text-black/80 dark:text-white/60">
              <span>Current: {selectedModel || "None"}</span>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6 gap-1"
                onClick={() => {
                  // Navigate to models settings
                  window.dispatchEvent(new CustomEvent('open-settings', { detail: 'models' }));
                  setIsOpen(false);
                }}
              >
                <Eye className="h-3 w-3" />
                Manage Models
              </Button>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
