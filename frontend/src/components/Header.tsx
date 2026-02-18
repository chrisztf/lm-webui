import { useState } from "react";
import { PanelLeftOpen, Settings as SettingsIcon, HardDrive } from "lucide-react";
import { Button } from "./ui/button";
import { ModelSelector } from "./models/ModelSelector";
import { Settings } from "./settings/Settings";
import GGUFModelLoader from "./models/GGUFModelLoader";

interface HeaderProps {
  createNewChat: () => void;
  sidebarCollapsed: boolean;
  setSidebarOpen: (open: boolean) => void;
  // Model selector props
  selectedLLM: string;
  onLLMChange: (llm: string) => void;
  selectedModel: string;
  onModelChange: (model: string) => void;
  availableModels: string[];
  providerGroups?: any[];
  connectionStatus: string;
  // Search props
  selectedSearchEngine?: string;
  onSearchEngineChange?: (value: string) => void;
}

export default function Header({
  createNewChat,
  sidebarCollapsed,
  setSidebarOpen,
  selectedLLM,
  onLLMChange,
  selectedModel,
  onModelChange,
  availableModels,
  providerGroups,
  connectionStatus,
  selectedSearchEngine,
  onSearchEngineChange,
}: HeaderProps) {
  const [isGGUFLoaderOpen, setIsGGUFLoaderOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 px-4 py-[29px] flex h-14 shrink-0 items-center justify-between border-b border-stone-500/50 bg-neutral-300/50 backdrop-blur-sm dark:border-zinc-800 dark:bg-neutral-900/25">
      <div className="flex items-center gap-2">
        {sidebarCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
            className="md:hidden"
          >
            <PanelLeftOpen className="h-5 w-5" />
          </Button>
        )}
        
        <div className="flex items-center gap-4">
          <ModelSelector
            selectedLLM={selectedLLM}
            onLLMChange={onLLMChange}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            availableModels={availableModels}
            providerGroups={providerGroups || []}
            connectionStatus={connectionStatus as any}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsGGUFLoaderOpen(true)}
          className="hidden sm:flex gap-2 py-5 px-3 rounded-full border-zinc-200 dark:border-zinc-800"
          title="GGUF Loader"
        >
          <HardDrive className="h-5 w-5" />
        </Button>
        <GGUFModelLoader
          open={isGGUFLoaderOpen}
          onOpenChange={setIsGGUFLoaderOpen}
          onModelLoad={onModelChange}
        />
        <Settings
          selectedLLM={selectedLLM}
          onLLMChange={onLLMChange}
          availableModels={availableModels}
          selectedModel={selectedModel}
          onModelChange={onModelChange}
          selectedSearchEngine={selectedSearchEngine ?? "duckduckgo"}
          onSearchEngineChange={onSearchEngineChange ?? (() => {})}
          trigger={
            <Button
              variant="outline"
              size="sm"
              className="hidden sm:flex gap-2 py-5 px-3 rounded-full border-zinc-200 dark:border-zinc-800"
            >
              <SettingsIcon className="h-5 w-5" /> 
            </Button>
          }
        />
      </div>
    </header>
  );
}
