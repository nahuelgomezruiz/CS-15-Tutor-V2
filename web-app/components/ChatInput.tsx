import { useState, useRef, useEffect } from "react";
import { Button } from "./button";
import { LuSendHorizontal } from "react-icons/lu";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isDisabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isDisabled = false }) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = 'auto';
      
      // Set new height based on scrollHeight, with max height
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 200; // Max height in pixels (about 8-10 lines)
      
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isDisabled) return;
    
    onSendMessage(input);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter, but allow Shift+Enter for new lines
    if (e.key === "Enter" && !e.shiftKey && !isDisabled) {
      e.preventDefault(); // Prevent new line
      handleSend();
    }
  };

  return (
    <div className="mt-2 flex gap-2 p-3 bg-gray-700 rounded-lg items-end border border-gray-600">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question"
        className="flex-1 bg-gray-600 text-gray-100 placeholder-gray-400 rounded-md border border-gray-500 px-3 py-2 text-sm 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   resize-none overflow-y-auto min-h-[40px]"
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        rows={1}
      />
      <Button 
        onClick={handleSend} 
        className="bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:bg-gray-600 disabled:text-gray-400"
        disabled={isDisabled || !input.trim()}
      >
        <LuSendHorizontal size="24px" />
      </Button>
    </div>
  );
}; 