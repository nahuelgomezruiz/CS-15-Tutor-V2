// Authentication service for frontend
// Handles authentication when frontend is on Tufts servers and backend is on Render

class FrontendAuthService {
    private authenticatedUser: string | null = null;
  
    async getAuthenticatedUser(): Promise<string | null> {
      // In production (Tufts servers), the user is already authenticated via .htaccess
      // We need to extract this information somehow
      
      // Since this is a static site, we can't access server environment directly
      // But we can use the fact that the user made it past .htaccess authentication
      
      // For now, we'll try to extract from any available sources
      try {
        // Method 1: Check if running on Tufts domain
        const isTuftsDeployment = window.location.hostname.includes('.tufts.edu');
        
        if (isTuftsDeployment) {
          // Extract username from URL path if possible
          const pathMatch = window.location.pathname.match(/\/~([^\/]+)\//);
          if (pathMatch) {
            this.authenticatedUser = pathMatch[1];
            return this.authenticatedUser;
          }
        }
        
        // Method 2: Check localStorage for cached user (from previous sessions)
        const cachedUser = localStorage.getItem('tufts_authenticated_user');
        if (cachedUser) {
          this.authenticatedUser = cachedUser;
          return this.authenticatedUser;
        }
        
        // Method 3: Prompt user for their username (they're already authenticated)
        if (isTuftsDeployment && !this.authenticatedUser) {
          const username = prompt('Please enter your Tufts username (you are already authenticated):');
          if (username && username.trim()) {
            this.authenticatedUser = username.trim().toLowerCase();
            localStorage.setItem('tufts_authenticated_user', this.authenticatedUser);
            return this.authenticatedUser;
          }
        }
        
        return null;
      } catch (error) {
        console.error('Error getting authenticated user:', error);
        return null;
      }
    }
  
    async getAuthHeaders(): Promise<Record<string, string>> {
      const user = await this.getAuthenticatedUser();
      
      const headers: Record<string, string> = {};
      
      if (user) {
        // Send user information to backend
        headers['X-Remote-User'] = user;
        headers['X-Tufts-Authenticated'] = 'true';
        headers['X-Frontend-Domain'] = window.location.hostname;
      }
      
      return headers;
    }
  
    clearAuthentication(): void {
      this.authenticatedUser = null;
      localStorage.removeItem('tufts_authenticated_user');
    }
  }
  
  export const frontendAuthService = new FrontendAuthService();