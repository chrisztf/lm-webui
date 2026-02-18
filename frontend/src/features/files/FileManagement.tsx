import React from 'react';
import { useFileManagement } from './useFileManagement';

interface FileManagementProps {
  currentConversationId: string;
  isAuthenticated: boolean;
  setInputValue: (value: string) => void;
  loadUserSessions: () => Promise<void>;
  children: (handlers: {
    handleFileUpload: (files: FileList) => Promise<void>;
    handleFileProcessed: (result: any) => void;
    handleContextRetrieved: (context: string) => void;
    isLoading: boolean;
    setIsLoading: (loading: boolean) => void;
    ragContext: string;
    setRagContext: (context: string) => void;
  }) => React.ReactNode;
}

export const FileManagement: React.FC<FileManagementProps> = ({
  currentConversationId,
  isAuthenticated,
  setInputValue,
  loadUserSessions,
  children,
}) => {
  const {
    handleFileUpload: fileHandleFileUpload,
    handleFileProcessed: fileHandleFileProcessed,
    handleContextRetrieved: fileHandleContextRetrieved,
    isLoading,
    setIsLoading,
    ragContext,
    setRagContext,
  } = useFileManagement();

  const handleFileUpload = async (files: FileList) => {
    await fileHandleFileUpload(files);
  };

  const handleFileProcessed = (result: any) => {
    fileHandleFileProcessed(result);
  };

  const handleContextRetrieved = (context: string) => {
    fileHandleContextRetrieved(context);
  };

  return (
    <>
      {children({
        handleFileUpload,
        handleFileProcessed,
        handleContextRetrieved,
        isLoading,
        setIsLoading,
        ragContext,
        setRagContext,
      })}
    </>
  );
};

export default FileManagement;
