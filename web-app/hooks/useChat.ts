import { useState, useEffect } from "react";
import { useConversation, Message } from "./useConversation";
import { chatApiService, HealthStatus } from "../services/chatApi";

export const useChat = () => {
  const {
    messages,
    conversationId,
    isTyping,
    setIsTyping,
    addMessage,
    updateLastMessage,
  } = useConversation();
  
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  
  // Fetch initial health status
  useEffect(() => {
    const fetchHealthStatus = async () => {
      try {
        const status = await chatApiService.getHealthStatus();
        setHealthStatus(status);
      } catch (error) {
        console.error("Failed to fetch health status:", error);
      }
    };
    
    fetchHealthStatus();
    
    // Refresh health status every 30 seconds
    const interval = setInterval(fetchHealthStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim()) return;
    
    // Check if user can query
    if (healthStatus && !healthStatus.can_query) {
      const errorMessage: Message = { 
        text: "You've run out of queries. Please wait for your health points to regenerate.", 
        sender: "bot" 
      };
      addMessage(errorMessage);
      return;
    }

    const userMessage: Message = { text: messageText, sender: "user" };
    addMessage(userMessage);
    setIsTyping(true);
    
    // Add an empty bot message that will be updated with the response
    const botMessage: Message = { text: "Looking at course content...", sender: "bot", isStreaming: true };
    addMessage(botMessage);

    try {
      const data = await chatApiService.sendMessage(
        messageText, 
        conversationId,
        (status: string) => {
          // Update the bot message with the current status
          updateLastMessage(status, true);
        }
      );
      
      if (data.response) {
        updateLastMessage(data.response, false);
        // console.log("RAG Context:", data.rag_context);
        
        // Update health status from response
        if (data.health_status) {
          setHealthStatus(data.health_status);
        }
      } else if (data.error) {
        updateLastMessage(`Error: ${data.error}`, false);
        
        // Update health status from error response if available
        if (data.health_status) {
          setHealthStatus(data.health_status);
        }
      }

    } catch (error) {
      console.error("Error sending message:", error);
      updateLastMessage(
        error instanceof Error 
          ? `Error: ${error.message}` 
          : "Error: An unexpected error occurred",
        false
      );
    } finally {
      setIsTyping(false);
    }
  };

  return {
    messages,
    isTyping,
    sendMessage,
    healthStatus,
  };
}; 