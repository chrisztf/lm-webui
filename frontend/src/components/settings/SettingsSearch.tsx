import React, { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Globe } from "lucide-react";
import { addApiKey } from "@/utils/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface SettingsSearchProps {
  selectedSearchEngine: string;
  onSearchEngineChange: (value: string) => void;
}

export function SettingsSearch({
  selectedSearchEngine,
  onSearchEngineChange,
}: SettingsSearchProps) {
  // Local state to ensure immediate UI updates while parent persists change
  const [localEngine, setLocalEngine] = useState(selectedSearchEngine);
  
  const [googleKey, setGoogleKey] = useState("");
  const [googleCx, setGoogleCx] = useState("");
  const [bingKey, setBingKey] = useState("");
  const [perplexityKey, setPerplexityKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const searchEngines = [
    { value: "duckduckgo", label: "DuckDuckGo", icon: Globe },
    { value: "google", label: "Google", icon: Globe },
    { value: "bing", label: "Bing", icon: Globe },
    { value: "perplexity", label: "Perplexity", icon: Globe },
  ];

  // Sync local state when prop updates (e.g. initial load)
  useEffect(() => {
    setLocalEngine(selectedSearchEngine);
  }, [selectedSearchEngine]);

  const handleEngineChange = (value: string) => {
    setLocalEngine(value);
    onSearchEngineChange(value);
  };

  useEffect(() => {
  }, []);

  const handleSaveKey = async (provider: string, key: string, label: string) => {
    if (!key) return;
    setIsLoading(true);
    try {
      await addApiKey(provider, key);
      toast.success(`${label} saved successfully`);
    } catch (error) {
      toast.error(`Failed to save ${label}`);
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Search Provider</CardTitle>
          <CardDescription>
            Select your preferred search engine for web research
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="search-engine">Default Search Engine</Label>
            <Select
              value={localEngine}
              onValueChange={handleEngineChange}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {searchEngines.map((engine) => (
                  <SelectItem key={engine.value} value={engine.value}>
                    <div className="flex items-center gap-2">
                      <engine.icon className="h-4 w-4" />
                      {engine.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {localEngine === "google" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Google Search Configuration</CardTitle>
            <CardDescription>
              Configure Google Custom Search JSON API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="google-key">API Key</Label>
              <div className="flex gap-2">
                <Input 
                  id="google-key" 
                  type="password" 
                  placeholder="Enter Google API Key" 
                  value={googleKey}
                  onChange={(e) => setGoogleKey(e.target.value)}
                />
                <Button 
                  size="sm" 
                  onClick={() => handleSaveKey("google_search", googleKey, "Google API Key")}
                  disabled={isLoading || !googleKey}
                >
                  Save
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="google-cx">Search Engine ID (CX)</Label>
              <div className="flex gap-2">
                <Input 
                  id="google-cx" 
                  placeholder="Enter Search Engine ID" 
                  value={googleCx}
                  onChange={(e) => setGoogleCx(e.target.value)}
                />
                <Button 
                  size="sm" 
                  onClick={() => handleSaveKey("google_cx", googleCx, "Google CX")}
                  disabled={isLoading || !googleCx}
                >
                  Save
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {localEngine === "bing" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Bing Search Configuration</CardTitle>
            <CardDescription>
              Configure Bing Web Search API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="bing-key">Subscription Key</Label>
              <div className="flex gap-2">
                <Input 
                  id="bing-key" 
                  type="password" 
                  placeholder="Enter Bing Subscription Key" 
                  value={bingKey}
                  onChange={(e) => setBingKey(e.target.value)}
                />
                <Button 
                  size="sm" 
                  onClick={() => handleSaveKey("bing_search", bingKey, "Bing Key")}
                  disabled={isLoading || !bingKey}
                >
                  Save
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {localEngine === "perplexity" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Perplexity Configuration</CardTitle>
            <CardDescription>
              Configure Perplexity API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="perplexity-key">API Key</Label>
              <div className="flex gap-2">
                <Input 
                  id="perplexity-key" 
                  type="password" 
                  placeholder="Enter Perplexity API Key" 
                  value={perplexityKey}
                  onChange={(e) => setPerplexityKey(e.target.value)}
                />
                <Button 
                  size="sm" 
                  onClick={() => handleSaveKey("perplexity", perplexityKey, "Perplexity Key")}
                  disabled={isLoading || !perplexityKey}
                >
                  Save
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
