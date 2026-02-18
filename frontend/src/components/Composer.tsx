import React, { useRef, useState, useEffect } from "react";
import { Send, Loader2, Settings2, Mic, Globe, Brain, Image, Code, Paperclip, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { FileService } from "../features/files/fileService";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip";
import { getModelCapability } from "@/config/modelConfig";

interface ComposerProps {
  onSend: (text: string, files: any[], useReasoning?: boolean) => void;
  busy: boolean;
  conversationId?: string;
  isSearchEnabled: boolean;
  setIsSearchEnabled: (enabled: boolean) => void;
  isImageMode: boolean;
  setIsImageMode: (enabled: boolean) => void;
  isCodingMode: boolean;
  setIsCodingMode: (enabled: boolean) => void;
  selectedModel?: string;
  isReasoningEnabled?: boolean;
  setIsReasoningEnabled?: (enabled: boolean) => void;
}

export default function Composer({
  onSend,
  busy,
  conversationId,
  isSearchEnabled,
  setIsSearchEnabled,
  isImageMode,
  setIsImageMode,
  isCodingMode,
  setIsCodingMode,
  selectedModel = "gpt-4o-mini",
  isReasoningEnabled = false,
  setIsReasoningEnabled,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const capability = getModelCapability(selectedModel);
  const isNativeReasoner = capability?.type === 'reasoner';
  
  // Determine if reasoning should be enabled
  const shouldShowReasoningToggle = setIsReasoningEnabled !== undefined;
  const effectiveReasoningEnabled = isNativeReasoner || isReasoningEnabled;

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [value]);

  const handleSend = () => {
    if (!value.trim() || busy) return;

    // Use explicit reasoning toggle if available, otherwise fall back to native reasoner detection
    const useReasoning = shouldShowReasoningToggle ? isReasoningEnabled : isNativeReasoner;
    
    onSend(value, uploadedFiles, useReasoning || false);
    setValue("");
    setUploadedFiles([]);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setIsUploading(true);
      try {
        const result = await FileService.uploadFiles(e.target.files, conversationId || "");
        if (result.success && result.results) {
           const newFiles = result.results;
           setUploadedFiles(prev => [...prev, ...newFiles]);
        }
      } catch (error) {
        console.error("Upload failed", error);
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="border-none backdrop-blur-sm bg-transparent pt-2">
      <div className="mx-auto flex flex-col rounded-3xl border border-zinc-200 bg-neutral-300 dark:border-zinc-800/50 dark:bg-neutral-900 shadow-inner transition-all duration-200 relative">

        {uploadedFiles.length > 0 && (
          <div className="px-4 pt-3 pb-1 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div key={index} className="flex items-center gap-1 bg-zinc-200 dark:bg-zinc-800 rounded-md px-2 py-1 text-xs text-zinc-700 dark:text-zinc-300 animate-in fade-in zoom-in duration-200">
                <span className="truncate max-w-[150px]">{file.filename}</span>
                <button 
                  onClick={() => removeFile(index)} 
                  className="ml-1 hover:text-red-500 rounded-full p-0.5 hover:bg-zinc-300 dark:hover:bg-zinc-700 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex-1 px-4 pt-4 pb-4">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={isNativeReasoner ? "Ask a complex reasoning question..." : "Ask LM WebUI..."}
            className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-zinc-700/30 dark:placeholder:text-zinc-400/30 min-h-[24px] leading-6"
            rows={1}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
        </div>

        <div className="flex items-center justify-between px-3 pb-3 pl-4">
          <div className="flex items-center gap-2">
            <input
              type="file"
              multiple
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileSelect}
            />
            <Button 
              variant="ghost" 
              size="icon" 
              className="rounded-full text-zinc-500 hover:text-zinc-600 dark:hover:text-zinc-200"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || busy}
            >
              {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
            </Button>

            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full text-zinc-500">
                  <Settings2 className="h-5 w-5" />
                </Button>
              </PopoverTrigger>
              <PopoverContent side="top" align="start" className="w-48 p-2.5 rounded-2xl bg-neutral-200/90 dark:bg-neutral-900 border-zinc-300/50 dark:border-zinc-800/50">
                 <div className="grid gap-2">
                    <Button 
                     variant={isSearchEnabled ? "secondary" : "ghost"} 
                     size="sm" 
                     className="justify-start gap-2 rounded-lg hover:rounded-lg"
                     onClick={() => setIsSearchEnabled(!isSearchEnabled)}
                    >
                      <Globe className="h-4 w-4" /> Search
                    </Button>
                    
                    {/* Explicit reasoning toggle for non-native reasoners */}
                    {shouldShowReasoningToggle && !isNativeReasoner && (
                      <Button 
                       variant={isReasoningEnabled ? "secondary" : "ghost"} 
                       size="sm" 
                       className="justify-start gap-2 rounded-lg hover:rounded-lg"
                       onClick={() => setIsReasoningEnabled && setIsReasoningEnabled(!isReasoningEnabled)}
                      >
                        <Brain className="h-4 w-4" /> Deep Thinking
                      </Button>
                    )}

                    <Button 
                     variant={isImageMode ? "secondary" : "ghost"} 
                     size="sm" 
                     className="justify-start gap-2 rounded-lg hover:rounded-lg"
                     onClick={() => setIsImageMode(!isImageMode)}
                    >
                      <Image className="h-4 w-4" /> Generate Image
                    </Button>
                    <Button 
                     variant={isCodingMode ? "secondary" : "ghost"} 
                     size="sm" 
                     className="justify-start gap-2 rounded-lg hover:rounded-lg"
                     onClick={() => setIsCodingMode(!isCodingMode)}
                    >
                      <Code className="h-4 w-4" /> Coding Mode
                    </Button>
                 </div>
              </PopoverContent>
            </Popover>

          </div>

           <div className="flex items-center gap-2">
              {isSearchEnabled && (
                <span className="flex items-center gap-1 text-[6px] md:text-[8px] bg-cyan-100/50 text-cyan-500/50 px-2 py-0.5 rounded-full font-bold tracking-wider dark:bg-cyan-900/50 dark:text-cyan-200/50">
                 <Globe className="w-3 h-3" />
                  Search On
                </span>
              )}
              {(isNativeReasoner || (shouldShowReasoningToggle && isReasoningEnabled)) && (
                <span className={cn(
                  "flex items-center gap-1 text-[6px] md:text-[8px] px-2 py-0.5 rounded-full font-bold tracking-wider",
                  isNativeReasoner 
                    ? "bg-indigo-100/30 text-indigo-500/50 dark:bg-indigo-900/30 dark:text-indigo-200/50"
                    : "bg-amber-100/30 text-amber-500/50 dark:bg-amber-900/30 dark:text-amber-200/50"
                )}>
                 <Brain className="w-3 h-3" />
                  {isNativeReasoner ? "Reasoning" : "Deep Thinking"}
                </span>
              )}
            <Button
              onClick={handleSend}
              disabled={busy || !value.trim()}
              size="icon"
              className={cn(
                "rounded-full h-10 w-10",
                value.trim() ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800"
              )}
            >
              {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>
        <div className="flex items-center justify-center text-xs text-neutral-500/50 p-1">
            <p>LLM can make mistakes, please double check</p>
        </div>
    </div>
  );
}
