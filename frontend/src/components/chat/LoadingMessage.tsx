import React from "react";
import { Brain, Zap, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { MessageBubble } from "@/components/chat/MessageBubble";
import loadingIcon from "/loading.ico";

interface LoadingMessageProps {
  showRawResponse?: boolean;
  isStreaming?: boolean;
  searchStatus?: string;
  isSearchEnabled?: boolean;
}

export function LoadingMessage({
  showRawResponse = false,
  isStreaming = false,
  searchStatus,
  isSearchEnabled = false
}: LoadingMessageProps = {}) {
  const isMobile = useIsMobile();

  return (
    <div
      className={cn(
        "group animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
        "-ml-2 -mr-2 md:-ml-2 md:mr-20",
        isMobile ? "max-w-full" : "max-w-4xl"
      )}
    >
      <div
        className={cn(
          "min-w-20",
          isMobile ? "text-[.9rem]" : "text-md"
        )}
      >
        {/* Context indicators for search state */}
        {isSearchEnabled && (
          <div className="mb-3">
            <div className="flex gap-1 flex-wrap">
              <div className="flex items-center gap-1 text-[.6rem] text-cyan-500 bg-cyan-900/5 px-2 py-1 rounded-3xl animate-pulse">
                <Search className="h-3 w-3" />
                Web Search
              </div>
            </div>
          </div>
        )}

        {/* Message bubble with typing indicator */}
        <MessageBubble
          role="assistant"
          isMobile={isMobile}
          contentLength={50} // Short content for consistent bubble size
        >
          <div className="flex items-center gap-3">
            {/* Avatar with circular loading animation */}
            <div
              className={cn(
                "flex-shrink-0 rounded-full flex items-center justify-center relative",
                isMobile ? "w-6 h-6" : "w-7 h-7",
                "bg-primary/5"
              )}
            >
              {/* Custom Loading Icon - Static */}
              <img
                src={loadingIcon}
                alt="Loading"
                className={cn(
                  "object-contain z-10",
                  isMobile ? "h-2.5 w-2.5" : "h-3 w-3"
                )}
              />

              {/* Circular Rotating Arc */}
              <div className="absolute inset-0 flex items-center justify-center">
                <svg className="w-full h-full animate-circular-rotate" viewBox="0 0 24 24">
                  <defs>
                    <linearGradient id="circular-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="hsl(214.3 31.8% 91.4%)" stopOpacity="0.3" />
                      <stop offset="50%" stopColor="hsl(214.3 31.8% 91.4%)" stopOpacity="0.6" />
                      <stop offset="100%" stopColor="hsl(214.3 31.8% 91.4%)" stopOpacity="0.3" />
                    </linearGradient>
                  </defs>
                  <circle
                    cx="12" cy="12" r="10"
                    stroke="url(#circular-gradient)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    fill="none"
                    strokeDasharray="20 10"
                  />
                </svg>
              </div>
            </div>

            {/* Loading content */}
            <div className="flex-1">
              {isSearchEnabled && searchStatus ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Search className="h-4 w-4 text-cyan-400 animate-pulse" />
                    <span className="text-muted-foreground">
                      {searchStatus}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground an">
                  {isSearchEnabled ? "Initializing search..." : "Generating response..."}
                </div>
              )}

              {/* Raw response indicator */}
              {showRawResponse && (
                <div className="text-xs text-muted-foreground mt-2 opacity-70">
                  Raw Response Mode Active
                </div>
              )}
            </div>
          </div>
        </MessageBubble>


      </div>
    </div>
  );
}
