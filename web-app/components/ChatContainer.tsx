import { useChat } from "../hooks/useChat";
import { useAutoScroll } from "../hooks/useAutoScroll";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { HealthBar } from "./HealthBar";

export const ChatContainer: React.FC = () => {
  const { messages, isTyping, sendMessage, healthStatus } = useChat();
  const { chatRef, handleScroll } = useAutoScroll([messages]);

  return (
    <div className="flex items-center justify-center min-h-screen w-full bg-gray-900">
      <div className="flex flex-col h-[90vh] w-full max-w-4xl p-4 bg-gray-800 rounded-lg shadow-2xl border border-gray-700">
        {healthStatus && (
          <HealthBar 
            currentPoints={healthStatus.current_points}
            maxPoints={healthStatus.max_points}
            timeUntilNextRegen={healthStatus.time_until_next_regen}
          />
        )}
        
        <div 
          ref={chatRef} 
          onScroll={handleScroll} 
          className="flex-1 overflow-y-auto px-2 flex flex-col"
        >
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
        </div>

        <ChatInput 
          onSendMessage={sendMessage} 
          isDisabled={isTyping || (healthStatus ? !healthStatus.can_query : false)} 
        />
      </div>
    </div>
  );
}; 