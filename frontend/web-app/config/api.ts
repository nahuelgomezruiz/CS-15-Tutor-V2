// API Configuration
// Update this file to point to your production API endpoint

const API_CONFIG = {
    // For local development
    development: {
      baseUrl: "http://127.0.0.1:5001"
    },
    
    // For production deployment on Tufts servers
    production: {
      // Using Render.com deployment (as shown in the console errors)
      baseUrl: "https://cs-15-tutor.onrender.com"
    }
  };
  
  export const getApiBaseUrl = () => {
    const isDevelopment = process.env.NODE_ENV === 'development';
    return isDevelopment ? API_CONFIG.development.baseUrl : API_CONFIG.production.baseUrl;
  };
  
  export default API_CONFIG;