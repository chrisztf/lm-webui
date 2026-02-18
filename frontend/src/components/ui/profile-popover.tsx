import React, { useState } from "react";
import { LogOut } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";
import { useAuth } from "@/contexts/AuthContext";

export function ProfilePopover() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button className="w-full flex items-center gap-2 rounded-3xl bg-zinc-50 p-2 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:bg-zinc-800/60 dark:hover:bg-zinc-700/60 transition-colors">
          <div className="grid h-8 w-8 ml-2 mr-1 place-items-center rounded-full bg-zinc-900/50 shadow-inner text-xs font-bold text-white dark:bg-white dark:text-zinc-900">
            {user?.email?.charAt(0).toUpperCase() || "U"}
          </div>
          <div className="min-w-0 flex-1 text-left">
            <div className="truncate text-sm font-medium">
              {user?.email?.split("@")[0] || "User"}
            </div>
            <div className="truncate text-xs text-zinc-500 dark:text-zinc-400">Pro workspace</div>
          </div>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-48 p-0" align="start" side="top">
        <div className="p-2">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 text-sm text-left hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors text-red-600 dark:text-red-400"
          >
            <LogOut className="h-4 w-4" />
            <span>Log out</span>
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
