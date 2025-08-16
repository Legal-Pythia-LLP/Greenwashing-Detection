// API Configuration
export const API_CONFIG = {
  // Use local backend in development environment
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/v1',
  
  // API endpoints
  ENDPOINTS: {
    UPLOAD: '/upload',
    CHAT: '/chat',
    REPORT: '/report',
    WIKIRATE: '/wikirate',
    DASHBOARD: '/dashboard',
  },
  
  // Timeout settings
  TIMEOUT: 30000,
  
  // Retry attempts
  RETRY_COUNT: 3,
};

// Check if it's development environment
export const IS_DEV = import.meta.env.DEV;

// Get full API URL
export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
