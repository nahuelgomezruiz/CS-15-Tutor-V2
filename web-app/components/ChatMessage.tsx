import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../hooks/useConversation';
import { LoadingSpinner } from './LoadingSpinner';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === "user";
  const isLoadingState = message.isStreaming && (
    message.text === "Looking at course content..." || 
    message.text === "Thinking..."
  );
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`px-4 py-3 rounded-2xl max-w-[80%] shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : isLoadingState
            ? 'bg-gray-700 text-gray-400 italic rounded-bl-md'
            : 'bg-gray-700 text-gray-100 rounded-bl-md'
        }`}
      >
        {isLoadingState ? (
          <div className="flex items-center space-x-2">
            <LoadingSpinner />
            <span>{message.text}</span>
          </div>
        ) : isUser ? (
          // For user messages, preserve formatting but escape markdown
          <div className="whitespace-pre-wrap break-words text-sm">
            {message.text}
          </div>
        ) : (
          // For assistant messages, render markdown
          <ReactMarkdown 
            className="prose prose-sm max-w-none prose-p:my-2 prose-headings:my-2 text-sm prose-invert"
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0 text-gray-100">{children}</p>,
              pre: ({ children }) => (
                <div className="overflow-x-auto my-2">
                  <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs border border-gray-600">
                    {children}
                  </pre>
                </div>
              ),
              code: ({ className, children }) => {
                const hasLanguage = className && className.includes('language-');
                return hasLanguage ? (
                  <code className="bg-gray-900 text-gray-100">
                    {children}
                  </code>
                ) : (
                  <code className="bg-gray-600 text-gray-100 px-1 py-0.5 rounded text-xs">
                    {children}
                  </code>
                );
              },
              h1: ({ children }) => <h1 className="text-lg font-bold text-gray-100 mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-bold text-gray-100 mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-bold text-gray-100 mb-2">{children}</h3>,
              ul: ({ children }) => <ul className="list-disc list-inside text-gray-100 mb-2">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside text-gray-100 mb-2">{children}</ol>,
              li: ({ children }) => <li className="text-gray-100 mb-1">{children}</li>,
              strong: ({ children }) => <strong className="font-bold text-gray-100">{children}</strong>,
              em: ({ children }) => <em className="italic text-gray-100">{children}</em>
            }}
          >
            {message.text}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}; 