import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PanelLeftClose,
  PanelLeftOpen,
  SearchIcon,
  Plus,
  Star,
  Clock,
  Settings,
  Asterisk,
  Edit2,
  Trash2,
  Check,
  X,
  LayoutGrid,
  Briefcase,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatConversation } from "@/types/chat-ui";
import { Button } from "./ui/button";
import { ThemeToggle } from "./ui/theme-toggle";
import { ProfilePopover } from "./ui/profile-popover";
import { Settings as SettingsModal } from "./settings/Settings";
import { Input } from "./ui/input";
import { toast } from "sonner";
import { useChatStore } from "@/store/chatStore";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  conversations: ChatConversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  createNewChat: () => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

// Conversation item component with edit and delete functionality
function ConversationItem({ 
  conversation, 
  isSelected, 
  onSelect, 
  onEditTitle,
  onDelete 
}: { 
  conversation: ChatConversation;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onEditTitle: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(conversation.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = () => {
    const trimmedTitle = editTitle.trim();
    if (trimmedTitle && trimmedTitle !== conversation.title) {
      onEditTitle(conversation.id, trimmedTitle);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditTitle(conversation.title);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="group relative">
      <button
        onClick={() => onSelect(conversation.id)}
        className={cn(
          "w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors flex items-center justify-between",
          isSelected ? "bg-zinc-100 dark:bg-zinc-800 font-medium" : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
        )}
      >
        {isEditing ? (
          <Input
            ref={inputRef}
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSave}
            className="h-6 text-sm px-1 py-0"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className={cn("truncate flex-1", conversation.isTitleGenerating && "text-zinc-400 italic animate-pulse")}>
            {conversation.isTitleGenerating ? "Generating title..." : conversation.title}
          </span>
        )}
        
        {!isEditing && !conversation.isTitleGenerating && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0 hover:bg-zinc-200 dark:hover:bg-zinc-700"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
            >
              <Edit2 className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conversation.id);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        )}
        
        {isEditing && (
          <div className="flex items-center gap-1 ml-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0 hover:bg-green-100 dark:hover:bg-green-900/30 hover:text-green-600 dark:hover:text-green-400"
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
            >
              <Check className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0 hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400"
              onClick={(e) => {
                e.stopPropagation();
                handleCancel();
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </button>
    </div>
  );
}

export default function Sidebar({
  open,
  onClose,
  conversations,
  selectedId,
  onSelect,
  createNewChat,
  sidebarCollapsed,
  setSidebarCollapsed,
}: SidebarProps) {
  const pinned = conversations.filter(c => c.pinned);
  const recent = conversations.filter(c => !c.pinned).slice(0, 20);
  const updateConversationTitle = useChatStore(state => state.updateConversationTitle);
  const deleteConversation = useChatStore(state => state.deleteConversation);

  const handleEditTitle = (chatId: string, title: string) => {
    updateConversationTitle(chatId, title);
    toast.success("Conversation title updated");
  };

  const handleDeleteConversation = (chatId: string) => {
    if (window.confirm("Are you sure you want to delete this conversation? This action cannot be undone.")) {
      deleteConversation(chatId);
      toast.success("Conversation deleted");
      
      // If we deleted the selected conversation, select another one
      if (selectedId === chatId) {
        const remaining = conversations.filter(c => c.id !== chatId);
        if (remaining.length > 0 && remaining[0]) {
          onSelect(remaining[0].id);
        }
      }
    }
  };

  if (sidebarCollapsed) {
    return (
      <motion.aside
        initial={{ width: 320 }}
        animate={{ width: 64 }}
        className="z-50 flex h-full shrink-0 flex-col border-r border-zinc-300/60 bg-neutral-300/50 dark:border-zinc-800 dark:bg-neutral-900"
      >
        <div className="flex items-center justify-center border-b border-zinc-200/60 px-3 py-[15px] dark:border-zinc-800">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarCollapsed(false)}
          >
            <PanelLeftOpen className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex flex-1 flex-col items-center gap-2 pt-4">
          <Button variant="ghost" size="icon" onClick={createNewChat} title="New chat">
            <Plus className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" title="Gallery">
            <LayoutGrid className="h-5 w-5 text-zinc-500" />
          </Button>
          <Button variant="ghost" size="icon" title="Workspace">
            <Briefcase className="h-5 w-5 text-zinc-500" />
          </Button>
        </div>
      </motion.aside>
    );
  }

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 md:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={{ x: -340 }}
        animate={{ x: 0 }}
        className={cn(
          "z-50 flex h-full w-80 shrink-0 flex-col border-r border-stone-500/50 bg-neutral-300/50 dark:border-zinc-800 dark:bg-neutral-900",
          "fixed inset-y-0 left-0 md:static md:translate-x-0"
        )}
      >
        <div className="flex items-center justify-between px-3 py-6 ml-2 pb-8">
          <div className="flex items-center gap-28">
            <div className="flex items-center gap-3 ml-1">
              <img src="/logo1.png" alt="Logo" className="h-8 w-8 object-contain" />
              <img src="/text41.png" alt="AI Assistant" className="h-5 object-contain hidden dark:block" />
              <img src="/text49.png" alt="AI Assistant" className="h-5 object-contain block dark:hidden" />
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="-ml-2"
              onClick={() => setSidebarCollapsed(true)}
            >
              <PanelLeftClose className="h-5 w-5 text-zinc-500" />
            </Button>
          </div>
        </div>

        <div className="px-6 mb-4">
          <div className="relative group">
            <SearchIcon className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400 group-focus-within:text-zinc-600 dark:group-focus-within:text-zinc-300 transition-colors" />
            <Input 
              placeholder="Search for chats" 
              className="pl-9 h-10 rounded-full bg-stone-100/80 dark:bg-zinc-800/50 border-none shadow-none focus-visible:ring-1 focus-visible:ring-zinc-200 dark:focus-visible:ring-zinc-700 transition-all outline-none" 
            />
          </div>
        </div>

        <div className="px-4 mb-6">
          <Button
            onClick={createNewChat}
            variant="ghost"
            className="w-full flex items-center justify-start gap-3 rounded-full h-12 px-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-stone-100/80 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <Plus className="h-4 w-4" />
            </div>
            <span className="font-medium">New chat</span>
          </Button>
        </div>

        <div className="px-3 mb-6">
          <div className="px-4 text-xs font-medium text-zinc-500 mb-2">My stuff</div>
          <div className="space-y-1">
            <Button variant="ghost" className="w-full justify-start gap-3 px-4 h-10 rounded-full font-normal text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800">
              <LayoutGrid className="h-4 w-4" />
              <span>Gallery</span>
            </Button>
            <Button variant="ghost" className="w-full justify-start gap-3 px-4 h-10 rounded-full font-normal text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800">
              <Briefcase className="h-4 w-4" />
              <span>Workspace</span>
            </Button>
          </div>
        </div>

        <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-2 pb-4 scrollbar-hide">
          <div className="px-4 text-xs font-medium text-zinc-500 mb-[-10px]">Chats</div>
          {pinned.length > 0 && (
            <div className="space-y-1">
              <h3 className="px-4 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Pinned</h3>
              {pinned.map(c => (
                <ConversationItem
                  key={c.id}
                  conversation={c}
                  isSelected={selectedId === c.id}
                  onSelect={onSelect}
                  onEditTitle={handleEditTitle}
                  onDelete={handleDeleteConversation}
                />
              ))}
            </div>
          )}

          <div className="space-y-1">
            <h3 className="px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Recent</h3>
            {recent.length === 0 ? (
              <p className="px-3 text-xs text-zinc-400">No conversations yet.</p>
            ) : (
              recent.map(c => (
                <ConversationItem
                  key={c.id}
                  conversation={c}
                  isSelected={selectedId === c.id}
                  onSelect={onSelect}
                  onEditTitle={handleEditTitle}
                  onDelete={handleDeleteConversation}
                />
              ))
            )}
          </div>
        </nav>

        <div className="mt-auto border-t border-zinc-200/60 px-4 py-4 mb-2 dark:border-zinc-800">
          <div className="flex items-center justify-between mb-4">
            <SettingsModal
              selectedLLM="openai"
              onLLMChange={() => {}}
              variant="button"
              availableModels={[]}
              selectedModel=""
              onModelChange={() => {}}
              showRawResponse={false}
              onRawResponseToggle={() => {}}
            />
            <ThemeToggle />
          </div>
          <ProfilePopover />
        </div>
      </motion.aside>
    </>
  );
}
