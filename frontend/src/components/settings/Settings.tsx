import React, { useState, useEffect } from "react";
import { fetchSettings, updateSettings, addApiKey } from "@/utils/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Settings as SettingsIcon } from "lucide-react";
import { SettingsSearch } from "./SettingsSearch";
import { ApiKeysTab } from "./ApiKeysTab";
import { ModelsTab } from "./ModelsTab";

interface SettingsProps {
  selectedLLM: string;
  onLLMChange: (value: string) => void;
  variant?: "icon" | "button";
  trigger?: React.ReactNode;
  selectedSearchEngine?: string;
  onSearchEngineChange?: (value: string) => void;
  availableModels?: string[];
  selectedModel?: string;
  onModelChange?: (value: string) => void;
  showRawResponse?: boolean;
  onRawResponseToggle?: (value: boolean) => void;
}

export function Settings({
  selectedLLM,
  onLLMChange,
  variant = "icon",
  selectedSearchEngine = "duckduckgo",
  onSearchEngineChange = () => {},
  availableModels = [],
  selectedModel = "",
  onModelChange = () => {},
  showRawResponse = false,
  onRawResponseToggle = () => {},
  trigger,
}: SettingsProps) {
  const [openAIKey, setOpenAIKey] = useState("");
  const [ollamaEndpoint, setOllamaEndpoint] = useState(
    "http://localhost:11434",
  );
  const [lmStudioEndpoint, setLmStudioEndpoint] = useState(
    "http://localhost:1234",
  );
  const [deepSeekKey, setDeepSeekKey] = useState("");
  const [xaiKey, setXaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  
  // Local state for search engine to ensure persistence works correctly
  const [localSearchEngine, setLocalSearchEngine] = useState(selectedSearchEngine);

  // Sync local state when prop updates
  useEffect(() => {
    setLocalSearchEngine(selectedSearchEngine);
  }, [selectedSearchEngine]);

  const handleSearchEngineChange = (value: string) => {
    setLocalSearchEngine(value);
    onSearchEngineChange(value);
  };

  // Enhanced settings
  const [temperature, setTemperature] = useState([0.7]);
  const [maxTokens, setMaxTokens] = useState([2048]);
  const [topP, setTopP] = useState([0.9]);
  const [systemPrompt, setSystemPrompt] = useState(
    "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions.",
  );

  const [autoTitleGeneration, setAutoTitleGeneration] = useState(true);
  const [codeFormatting, setCodeFormatting] = useState(true);
  const [markdownRendering, setMarkdownRendering] = useState(true);
  const [clearCacheEnabled, setClearCacheEnabled] = useState(false);



  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await fetchSettings();
        setOpenAIKey(settings.openAIKey || "");
        setOllamaEndpoint(settings.ollamaEndpoint || "http://localhost:11434");
        setLmStudioEndpoint(settings.lmStudioEndpoint || "http://localhost:1234");
        setXaiKey(settings.xaiKey || "");
        setAnthropicKey(settings.anthropicKey || "");
        setGoogleKey(settings.googleKey || "");
        setStreamingEnabled(settings.streamingEnabled !== false);
        setTemperature([settings.temperature || 0.7]);
        setMaxTokens([settings.maxTokens || 2048]);
        setTopP([settings.topP || 0.9]);
        setSystemPrompt(settings.systemPrompt || systemPrompt);
        setAutoTitleGeneration(settings.autoTitleGeneration !== false);
        setCodeFormatting(settings.codeFormatting !== false);
        setMarkdownRendering(settings.markdownRendering !== false);
      } catch (error) {
        console.error("Failed to load settings:", error);
        // No localStorage fallback - rely on database only
      }
    };

    // Only load settings when the dialog is open
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);


  const saveSettings = async () => {
    const settings = {
      selectedLLM,
      openAIKey,
      ollamaEndpoint,
      lmStudioEndpoint,
      xaiKey,
      anthropicKey,
      googleKey,
      streamingEnabled,
      temperature: temperature[0],
      maxTokens: maxTokens[0],
      topP: topP[0],
      systemPrompt,
      selectedSearchEngine: localSearchEngine,
      selectedModel,
      showRawResponse,
      autoTitleGeneration,
      codeFormatting,
      markdownRendering,
    };

    try {
      await updateSettings(settings);

      // Save API keys to encrypted database only
      try {
        if (openAIKey) await addApiKey("openai", openAIKey);
        if (xaiKey) await addApiKey("xai", xaiKey);
        if (anthropicKey) await addApiKey("anthropic", anthropicKey);
        if (deepSeekKey) await addApiKey("deepseek", deepSeekKey);
        if (googleKey) await addApiKey("google", googleKey);
      } catch (apiKeyError) {
        console.warn("Failed to save API keys to encrypted database:", apiKeyError);
        // Continue with settings save even if API key save fails
      }

      setIsOpen(false);
      toast.success("Settings saved successfully!");
    } catch (error) {
      console.error("Failed to save settings:", error);
      toast.error("Failed to save settings");
    }
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          {trigger ? (
            trigger
          ) : variant === "icon" ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <SettingsIcon className="h-4 w-4" />
            </Button>
          ) : (
            <Button variant="ghost" className="w-full justify-start gap-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 px-2 py-2">
              <SettingsIcon className="h-4 w-4" />
              Settings
            </Button>
          )}
        </DialogTrigger>
        <DialogContent className="max-h-[55rem] sm:max-w-2xl overflow-y-auto bg-neutral-100/90 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
          <div className="flex flex-col space-y-1.5 text-center sm:text-left pb-4">
            <DialogTitle className="text-lg font-semibold leading-none tracking-tight mb-2">
              Settings
            </DialogTitle>
            <DialogDescription className="text-sm text-zinc-500 dark:text-zinc-400">
              Configure your AI assistant with advanced options and integrations.
            </DialogDescription>
          </div>

          <Tabs defaultValue="output" className="w-full">
            <TabsList className="grid w-full grid-cols-5 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs sm:text-sm">
              <TabsTrigger value="output" className="rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-700">Output</TabsTrigger>
              <TabsTrigger value="search" className="rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-700">Search</TabsTrigger>
              <TabsTrigger value="inference" className="rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-700">Inference</TabsTrigger>
              <TabsTrigger value="api-keys" className="rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-700">API Keys</TabsTrigger>
              <TabsTrigger value="models" className="rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-700">Models</TabsTrigger>
            </TabsList>

            <div className="min-h-[300px] sm:min-h-[400px] mt-4">
              <TabsContent value="search" className="space-y-4 h-full">
                <SettingsSearch
                  selectedSearchEngine={localSearchEngine}
                  onSearchEngineChange={handleSearchEngineChange}
                />
              </TabsContent>

              <TabsContent value="inference" className="space-y-4 h-full">
                <div className="space-y-4 p-4 ml-1 mr-1">
                  <div className="space-y-2">
                    <Label htmlFor="temperature" className="text-sm sm:text-base">
                      Temperature: {temperature[0]}
                    </Label>
                    <Slider
                      id="temperature"
                      min={0}
                      max={2}
                      step={0.1}
                      value={temperature}
                      onValueChange={setTemperature}
                      className="w-full"
                    />
                    <div className="text-xs sm:text-sm text-muted-foreground">
                      Controls randomness in responses (0 = deterministic, 2 = very creative)
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-tokens" className="text-sm sm:text-base">
                      Max Tokens: {maxTokens[0]}
                    </Label>
                    <Slider
                      id="max-tokens"
                      min={100}
                      max={8000}
                      step={100}
                      value={maxTokens}
                      onValueChange={setMaxTokens}
                      className="w-full"
                    />
                    <div className="text-xs sm:text-sm text-muted-foreground">
                      Maximum length of the response
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="top-p" className="text-sm sm:text-base">
                      Top P: {topP[0]}
                    </Label>
                    <Slider
                      id="top-p"
                      min={0}
                      max={1}
                      step={0.1}
                      value={topP}
                      onValueChange={setTopP}
                      className="w-full"
                    />
                    <div className="text-xs sm:text-sm text-muted-foreground">
                      Controls diversity of responses (nucleus sampling)
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="system-prompt" className="text-sm sm:text-base">System Prompt</Label>
                    <textarea
                      id="system-prompt"
                      className="flex min-h-[80px] sm:min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="You are a helpful AI assistant..."
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="output" className="space-y-4 h-full">
                <div className="space-y-4 p-4 ml-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5 mt-2">
                      <Label htmlFor="code-formatting" className="text-sm sm:text-base">Code Formatting</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Enable syntax highlighting for code blocks
                      </div>
                    </div>
                    <Switch
                      id="code-formatting"
                      checked={codeFormatting}
                      onCheckedChange={setCodeFormatting}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="markdown-rendering" className="text-sm sm:text-base">Markdown Rendering</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Render markdown in assistant responses
                      </div>
                    </div>
                    <Switch
                      id="markdown-rendering"
                      checked={markdownRendering}
                      onCheckedChange={setMarkdownRendering}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="raw-response" className="text-sm sm:text-base">Show Raw Response</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Display the raw API response alongside formatted output
                      </div>
                    </div>
                    <Switch
                      id="raw-response"
                      checked={showRawResponse}
                      onCheckedChange={onRawResponseToggle}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="auto-title" className="text-sm sm:text-base">Auto Title Generation</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Automatically generate titles for conversations
                      </div>
                    </div>
                    <Switch
                      id="auto-title"
                      checked={autoTitleGeneration}
                      onCheckedChange={setAutoTitleGeneration}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="streaming" className="text-sm sm:text-base">Enable Streaming</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Stream responses as they are generated
                      </div>
                    </div>
                    <Switch
                      id="streaming"
                      checked={streamingEnabled}
                      onCheckedChange={setStreamingEnabled}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="clear-cache" className="text-sm sm:text-base">Clear Cache on Exit</Label>
                      <div className="text-xs sm:text-sm text-muted-foreground">
                        Automatically clear browser cache when closing the application
                      </div>
                    </div>
                    <Switch
                      id="clear-cache"
                      checked={clearCacheEnabled}
                      onCheckedChange={setClearCacheEnabled}
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="api-keys" className="space-y-4 h-full">
                <ApiKeysTab />
              </TabsContent>

              <TabsContent value="models" className="space-y-4 h-full">
                <ModelsTab />
              </TabsContent>
            </div>
          </Tabs>

          <div className="flex justify-end items-center pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsOpen(false)} className="border-zinc-200 dark:border-zinc-700">
                Cancel
              </Button>
              <Button onClick={saveSettings}>Save Settings</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
