interface ChatResponse {
  response?: string;
  error?: string;
  rag_context?: string;
  conversation_id?: string;
  health_status?: HealthStatus;
}

interface StreamEvent {
  status: 'loading' | 'thinking' | 'complete' | 'error';
  message?: string;
  response?: string;
  error?: string;
  rag_context?: string;
  conversation_id?: string;
  health_status?: HealthStatus;
}

interface HealthStatus {
  current_points: number;
  max_points: number;
  can_query: boolean;
  time_until_next_regen: number;
}

import { getApiBaseUrl } from '../config/api';
import { frontendAuthService } from './authService';

class ChatApiService {
  private baseUrl = getApiBaseUrl();

  async sendMessage(
    message: string, 
    conversationId: string,
    onStatusUpdate?: (status: string) => void
  ): Promise<ChatResponse> {
    try {
      // Get authentication headers
      const authHeaders = await frontendAuthService.getAuthHeaders();
      
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...authHeaders
      };
      
      // Check if we're in development mode
      const isDevelopmentMode = process.env.NODE_ENV === 'development' || 
                               process.env.DEVELOPMENT_MODE === 'true';
      
      // Add development headers if in development mode and no auth headers
      if (isDevelopmentMode && !authHeaders['X-Remote-User']) {
        headers["X-Development-Mode"] = "true";
        headers["X-Remote-User"] = "testuser"; // Default test user for development
      }
      
      const response = await fetch(`${this.baseUrl}/api/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({ 
          message,
          conversationId 
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) {
        throw new Error("No response body");
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            if (jsonStr.trim()) {
              try {
                const event: StreamEvent = JSON.parse(jsonStr);
                
                // Handle status updates
                if (event.status === 'loading' && onStatusUpdate) {
                  onStatusUpdate('Looking at course content...');
                } else if (event.status === 'thinking' && onStatusUpdate) {
                  onStatusUpdate('Thinking...');
                } else if (event.status === 'complete') {
                  return {
                    response: event.response,
                    rag_context: event.rag_context,
                    conversation_id: event.conversation_id,
                    health_status: event.health_status
                  };
                } else if (event.status === 'error') {
                  throw new Error(event.error || 'Unknown error');
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      }

      throw new Error("Stream ended without complete status");
    } catch (error) {
      console.error("Error sending message:", error);
      throw new Error("Error generating answer.");
    }
  }

  async checkHealth(): Promise<{ status: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return await response.json();
    } catch (error) {
      console.error("Health check failed:", error);
      throw error;
    }
  }

  async getHealthStatus(): Promise<HealthStatus> {
    try {
      // Get authentication headers
      const authHeaders = await frontendAuthService.getAuthHeaders();
      const headers: Record<string, string> = { ...authHeaders };
      
      // Add development headers if in development mode and no auth headers
      const isDevelopmentMode = process.env.NODE_ENV === 'development' || 
                               process.env.DEVELOPMENT_MODE === 'true';
      if (isDevelopmentMode && !authHeaders['X-Remote-User']) {
        headers["X-Development-Mode"] = "true";
        headers["X-Remote-User"] = "testuser";
      }
      
      const response = await fetch(`${this.baseUrl}/health-status`, { headers });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Health status check failed:", error);
      throw error;
    }
  }
}

export const chatApiService = new ChatApiService();
export type { ChatResponse, StreamEvent, HealthStatus };