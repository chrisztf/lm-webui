import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIStore {
  // Theme & Appearance
  theme: 'dark' | 'light' | 'system';
  fontSize: 'small' | 'medium' | 'large';
  colorScheme: 'default' | 'high-contrast';
  reduceMotion: boolean;
  animationEnabled: boolean;
  
  // Layout
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  chatLayout: 'single' | 'split' | 'wide';
  messageDensity: 'comfortable' | 'compact';
  
  // Chat Display
  showTimestamps: boolean;
  showAvatars: boolean;
  chatBubbleStyle: 'rounded' | 'square';
  codeBlockTheme: string;
  markdownRenderer: 'default' | 'enhanced';
  
  // Editor & Input
  editorMode: 'rich' | 'plain';
  autoComplete: boolean;
  spellCheck: boolean;
  tabSize: number;
  wordWrap: boolean;
  emojiShortcuts: boolean;
  
  // Notifications
  notificationSound: boolean;
  notificationVolume: number;
  desktopNotifications: boolean;
  typingIndicator: boolean;
  readReceipts: boolean;
  
  // Accessibility
  screenReaderOptimized: boolean;
  keyboardShortcuts: Record<string, string>;
  focusMode: boolean;
  highlightCurrentLine: boolean;
  
  // Actions
  setTheme: (theme: UIStore['theme']) => void;
  setFontSize: (fontSize: UIStore['fontSize']) => void;
  toggleSidebar: () => void;
  setSidebarWidth: (width: number) => void;
  setChatLayout: (layout: UIStore['chatLayout']) => void;
  setMessageDensity: (density: UIStore['messageDensity']) => void;
  setEditorMode: (mode: UIStore['editorMode']) => void;
  setNotificationSound: (enabled: boolean) => void;
  setNotificationVolume: (volume: number) => void;
  toggleReduceMotion: () => void;
  resetToDefaults: () => void;
}

const defaultState = {
  // Theme & Appearance
  theme: 'system' as const,
  fontSize: 'medium' as const,
  colorScheme: 'default' as const,
  reduceMotion: false,
  animationEnabled: true,
  
  // Layout
  sidebarCollapsed: false,
  sidebarWidth: 240,
  chatLayout: 'single' as const,
  messageDensity: 'comfortable' as const,
  
  // Chat Display
  showTimestamps: true,
  showAvatars: true,
  chatBubbleStyle: 'rounded' as const,
  codeBlockTheme: 'github-dark',
  markdownRenderer: 'default' as const,
  
  // Editor & Input
  editorMode: 'rich' as const,
  autoComplete: true,
  spellCheck: true,
  tabSize: 2,
  wordWrap: true,
  emojiShortcuts: true,
  
  // Notifications
  notificationSound: true,
  notificationVolume: 0.7,
  desktopNotifications: false,
  typingIndicator: true,
  readReceipts: false,
  
  // Accessibility
  screenReaderOptimized: false,
  keyboardShortcuts: {},
  focusMode: false,
  highlightCurrentLine: true,
};

export const useUIStore = create<UIStore>()(
  persist(
    (set, _get) => ({
      ...defaultState,
      
      // Actions
      setTheme: (theme) => set({ theme }),
      setFontSize: (fontSize) => set({ fontSize }),
      toggleSidebar: () => set(state => ({ 
        sidebarCollapsed: !state.sidebarCollapsed 
      })),
      setSidebarWidth: (width) => set({ sidebarWidth: Math.max(200, Math.min(400, width)) }),
      setChatLayout: (layout) => set({ chatLayout: layout }),
      setMessageDensity: (density) => set({ messageDensity: density }),
      setEditorMode: (mode) => set({ editorMode: mode }),
      setNotificationSound: (enabled) => set({ notificationSound: enabled }),
      setNotificationVolume: (volume) => set({ 
        notificationVolume: Math.max(0, Math.min(1, volume)) 
      }),
      toggleReduceMotion: () => set(state => ({ reduceMotion: !state.reduceMotion })),
      resetToDefaults: () => set(defaultState),
    }),
    {
      name: 'ui-preferences',
      // Safe to share across users on same device
      partialize: (state) => ({
        // Only persist UI preferences, nothing user-specific
        theme: state.theme,
        fontSize: state.fontSize,
        colorScheme: state.colorScheme,
        reduceMotion: state.reduceMotion,
        animationEnabled: state.animationEnabled,
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth,
        chatLayout: state.chatLayout,
        messageDensity: state.messageDensity,
        showTimestamps: state.showTimestamps,
        showAvatars: state.showAvatars,
        chatBubbleStyle: state.chatBubbleStyle,
        codeBlockTheme: state.codeBlockTheme,
        markdownRenderer: state.markdownRenderer,
        editorMode: state.editorMode,
        autoComplete: state.autoComplete,
        spellCheck: state.spellCheck,
        tabSize: state.tabSize,
        wordWrap: state.wordWrap,
        emojiShortcuts: state.emojiShortcuts,
        notificationSound: state.notificationSound,
        notificationVolume: state.notificationVolume,
        desktopNotifications: state.desktopNotifications,
        typingIndicator: state.typingIndicator,
        readReceipts: state.readReceipts,
        screenReaderOptimized: state.screenReaderOptimized,
        keyboardShortcuts: state.keyboardShortcuts,
        focusMode: state.focusMode,
        highlightCurrentLine: state.highlightCurrentLine,
      }),
    }
  )
);

// Export hooks for common use cases
export const useTheme = () => useUIStore(state => state.theme);
export const useSetTheme = () => useUIStore(state => state.setTheme);
export const useFontSize = () => useUIStore(state => state.fontSize);
export const useSetFontSize = () => useUIStore(state => state.setFontSize);
export const useSidebarCollapsed = () => useUIStore(state => state.sidebarCollapsed);
export const useToggleSidebar = () => useUIStore(state => state.toggleSidebar);
export const useSidebarWidth = () => useUIStore(state => state.sidebarWidth);
export const useSetSidebarWidth = () => useUIStore(state => state.setSidebarWidth);
export const useChatLayout = () => useUIStore(state => state.chatLayout);
export const useSetChatLayout = () => useUIStore(state => state.setChatLayout);
export const useMessageDensity = () => useUIStore(state => state.messageDensity);
export const useSetMessageDensity = () => useUIStore(state => state.setMessageDensity);
export const useEditorMode = () => useUIStore(state => state.editorMode);
export const useSetEditorMode = () => useUIStore(state => state.setEditorMode);
export const useNotificationSound = () => useUIStore(state => state.notificationSound);
export const useSetNotificationSound = () => useUIStore(state => state.setNotificationSound);
export const useNotificationVolume = () => useUIStore(state => state.notificationVolume);
export const useSetNotificationVolume = () => useUIStore(state => state.setNotificationVolume);
export const useReduceMotion = () => useUIStore(state => state.reduceMotion);
export const useToggleReduceMotion = () => useUIStore(state => state.toggleReduceMotion);
export const useResetToDefaults = () => useUIStore(state => state.resetToDefaults);