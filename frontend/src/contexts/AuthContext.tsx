import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL

interface User {
  id: number;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  requiresRegistration: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [requiresRegistration, setRequiresRegistration] = useState(false);

  // Cookies are handled automatically by the browser/backend
  const isAuthenticated = !!user;

  // Auto-refresh timer
  let refreshTimer: NodeJS.Timeout;

  const startRefreshTimer = () => {
    stopRefreshTimer();
    // Refresh at 12 minutes (access token is 15 minutes)
    refreshTimer = setTimeout(() => {
      refreshAccessToken();
    }, 12 * 60 * 1000);
  };

  const stopRefreshTimer = () => {
    if (refreshTimer) clearTimeout(refreshTimer);
  };

  // Helper to clear temporary local storage data and persisted stores
  const clearTempStorage = () => {
    try {
      // Clear main sessions list
      localStorage.removeItem('tempSessions');
      
      // Clear all temp message keys
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('tempMessages_')) {
          keysToRemove.push(key);
        }
      }
      
      keysToRemove.forEach(key => localStorage.removeItem(key));
      
      // Clear old data exists from previous versions
      localStorage.removeItem('chat-storage');
      localStorage.removeItem('context-storage');
      
      // Clear any other potential persistence keys (except UI preferences)
      localStorage.removeItem('auth-storage'); // If exists
      localStorage.removeItem('reasoning-storage'); // If exists
      
      // Clear sessionStorage for draft messages (temporary storage)
      sessionStorage.clear();
      
      console.log('Cleared all temporary storage data (preserved UI preferences)');
    } catch (e) {
      console.error('Failed to clear temp storage:', e);
    }
  };

  // Check if registration is required (no users exist)
  const checkRegistrationRequired = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/status`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setRequiresRegistration(!data.hasUser);
      }
    } catch (error) {
      console.error('Failed to check registration status:', error);
    }
  };

  const fetchUser = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        credentials: 'include'
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        startRefreshTimer();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const refreshAccessToken = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        // After refresh, ensure we have the latest user data and timers set
        await fetchUser();
      } else {
        throw new Error('Token refresh failed');
      }
    } catch (error: any) {
      setUser(null);
      stopRefreshTimer();
      throw error;
    }
  };

  // Clean up storage on app initialization based on authentication state
  const cleanupStorageOnInit = async () => {
    try {
      // Simple check for authentication without side effects
      const checkAuthWithoutSideEffects = async (): Promise<boolean> => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            credentials: 'include'
          });
          return response.ok;
        } catch {
          return false;
        }
      };
      
      const hasValidAuth = await checkAuthWithoutSideEffects();
      
      if (!hasValidAuth) {
        // User is not authenticated - clear all temporary and persisted storage
        console.log('User not authenticated, clearing all storage data');
        clearTempStorage();
        
        // Also clear any auth-related storage
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
      } else {
        // User is authenticated
        console.log('User authenticated, performing storage cleanup');
        
        clearTempStorage();
        
        console.log('Cleared all storage for authenticated user (backend is source of truth)');
      }
      
      console.log('Storage cleanup completed on app initialization');
    } catch (error) {
      console.error('Storage cleanup failed:', error);
    }
  };

  // Initialize auth state on app load
  useEffect(() => {
    let isMounted = true;

    const initializeAuth = async () => {
      try {
        // Step 1: Clean up storage based on authentication state
        await cleanupStorageOnInit();
        
        // Step 2: Check if registration is required
        await checkRegistrationRequired();

        // Step 3: Try to get user with existing access token
        const success = await fetchUser();
        
        if (!success) {
          // If failed, try to refresh
          try {
             await refreshAccessToken();
          } catch {
             // If refresh fails, we are logged out
             if (isMounted) setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    initializeAuth();

    return () => {
      isMounted = false;
      stopRefreshTimer();
    };
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email,
          password
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        startRefreshTimer();
        clearTempStorage(); // Clear temp storage on successful login
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed');
      }
    } catch (error: any) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      stopRefreshTimer();
      // Clear local storage for chat persistence
      localStorage.removeItem('chat-storage');
      clearTempStorage(); // Ensure temp storage is cleared on logout too
    }
  };

  const register = async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email,
          password
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        startRefreshTimer();
        clearTempStorage(); // Clear temp storage on successful registration
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Registration failed');
      }
    } catch (error: any) {
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    requiresRegistration,
    login,
    register,
    logout,
    refreshAccessToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
