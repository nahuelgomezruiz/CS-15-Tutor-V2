import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";

interface Message {
  text: string;
  sender: "user" | "bot";
  isStreaming?: boolean;
}

const WELCOME_MESSAGE: Message = {
  text: "Hi! I'm an experimental AI tutor for CS15. Queries are logged to help improve the tool. Responses may be inaccurate, so please think critically. Feel free to send feedback to nahuel.gomez_ruiz@tufts.edu.",
  sender: "bot",
  isStreaming: false
};

export const useConversation = () => {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [conversationId, setConversationId] = useState<string>("");
  const [isTyping, setIsTyping] = useState(false);

  // Initialize conversation ID
  useEffect(() => {
    const storedConversationId = localStorage.getItem("conversationId");
    if (storedConversationId) {
      setConversationId(storedConversationId);
    } else {
      const newConversationId = uuidv4();
      localStorage.setItem("conversationId", newConversationId);
      setConversationId(newConversationId);
    }
  }, []);

  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const updateLastMessage = (text: string, isStreaming = false) => {
    setMessages((prev) => {
      const newMessages = [...prev];
      const lastMessage = newMessages[newMessages.length - 1];
      if (lastMessage && lastMessage.sender === "bot") {
        lastMessage.text = text;
        lastMessage.isStreaming = isStreaming;
      }
      return newMessages;
    });
  };

  return {
    messages,
    conversationId,
    isTyping,
    setIsTyping,
    addMessage,
    updateLastMessage,
  };
};

export type { Message }; 