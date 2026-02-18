import { create } from 'zustand';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL

interface User {
  id: number;
  email: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  checkAuthStatus: () => Promise<boolean>;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,

  login: async (email, password) => {
    const { data } = await axios.post('/api/auth/login', { email, password }, {
      baseURL: API_BASE_URL,
      withCredentials: true
    });
    set({ user: data.user, isAuthenticated: true });
    startRefreshTimer();
  },

  logout: async () => {
    await axios.post('/api/auth/logout', {}, {
      baseURL: API_BASE_URL,
      withCredentials: true
    });
    set({ user: null, isAuthenticated: false });
    stopRefreshTimer();
  },

  refreshAccessToken: async () => {
    try {
      await axios.post('/api/auth/refresh', {}, {
        baseURL: API_BASE_URL,
        withCredentials: true
      });
      set({ isAuthenticated: true });
      startRefreshTimer();
    } catch {
      get().logout();
    }
  },

  checkAuthStatus: async () => {
    try {
      // First check if any user exists in the system
      const statusResponse = await axios.get('/api/auth/status', {
        baseURL: API_BASE_URL,
        withCredentials: true
      });
      
      if (!statusResponse.data.hasUser) {
        set({ user: null, isAuthenticated: false });
        return false;
      }
      
      // Try silent token refresh first
      try {
        await axios.post('/api/auth/refresh', {}, {
          baseURL: API_BASE_URL,
          withCredentials: true
        });
        
        // If refresh succeeded, get user info
        const { data } = await axios.get('/api/auth/me', {
          baseURL: API_BASE_URL,
          withCredentials: true
        });
        
        set({ user: data, isAuthenticated: true });
        startRefreshTimer();
        return true;
      } catch (refreshError) {
        // Refresh failed, check if we can still get user info
        try {
          const { data } = await axios.get('/api/auth/me', {
            baseURL: API_BASE_URL,
            withCredentials: true
          });
          set({ user: data, isAuthenticated: true });
          startRefreshTimer();
          return true;
        } catch {
          // Both refresh and user info failed
          set({ user: null, isAuthenticated: false });
          return false;
        }
      }
    } catch {
      set({ user: null, isAuthenticated: false });
      return false;
    }
  },
}));

// Auto-refresh at 50 minutes (10 minutes before 60-minute expiry)
let timer: NodeJS.Timeout;
function startRefreshTimer() {
  stopRefreshTimer();
  timer = setTimeout(() => useAuth.getState().refreshAccessToken(), 50 * 60 * 1000);
}
function stopRefreshTimer() {
  if (timer) clearTimeout(timer);
}

// Handle 401 with silent refresh
axios.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      await useAuth.getState().refreshAccessToken();
      return axios(error.config);
    }
    return Promise.reject(error);
  }
);