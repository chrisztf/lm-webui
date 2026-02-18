import React, { useEffect } from "react";
import "./global.css";

import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { TooltipProvider } from "./components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "./components/ui/theme-provider";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { MultimodalProvider } from "./components/multimodal";
import { StartupGuard } from "./components/StartupGuard";

import IndexEnhanced from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import NotFound from "./pages/NotFound";
import ProtectedRoute from "./components/auth/ProtectedRoute";

const queryClient = new QueryClient();

// Wrapper component to handle WebSocket initialization
const AppContent = () => {
  const { isAuthenticated } = useAuth();
  
  // Initialize storage migration on app startup
  useEffect(() => {
    const migrateStorage = async () => {
      try {
        const { migrateToHybridStorage, needsStorageMigration } = await import('./utils/storageUtils');
        
        if (needsStorageMigration()) {
          console.log('🔄 Migrating storage to hybrid approach...');
          migrateToHybridStorage();
          console.log('✅ Storage migration completed');
        } else {
          console.log('✅ Storage already using hybrid approach');
        }
      } catch (error) {
        console.error('Storage migration failed:', error);
      }
    };
    
    migrateStorage();
  }, []);
  
  // Initialize WebSocket for real-time conversation updates
  useEffect(() => {
    if (isAuthenticated) {
      // Initialize WebSocket connection for real-time updates
      const initializeWebSocket = async () => {
        try {
          const { useChatStore } = await import('./store/chatStore');
          await useChatStore.getState().initializeWebSocket();
          console.log('✅ WebSocket initialized for real-time conversation updates');
        } catch (error) {
          console.error('Failed to initialize WebSocket:', error);
        }
      };
      
      initializeWebSocket();
      
      // Cleanup on unmount
      return () => {
        const cleanupWebSocket = async () => {
          try {
            const { useChatStore } = await import('./store/chatStore');
            useChatStore.getState().disconnectWebSocket();
            console.log('🔌 WebSocket disconnected');
          } catch (error) {
            console.error('Failed to disconnect WebSocket:', error);
          }
        };
        
        cleanupWebSocket();
      };
    }
  }, [isAuthenticated]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={
        <ProtectedRoute>
          <IndexEnhanced />
        </ProtectedRoute>
      } />
      {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

const App = () => (
  <ThemeProvider defaultTheme="dark">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
      <BrowserRouter future={{ v7_relativeSplatPath: true }}>
        <AuthProvider>
          <MultimodalProvider>
            <StartupGuard>
              <AppContent />
            </StartupGuard>
          </MultimodalProvider>
        </AuthProvider>
      </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
