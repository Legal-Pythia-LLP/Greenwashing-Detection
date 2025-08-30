// API Configuration
export const API_CONFIG = {
  // Use local backend in development environment
  BASE_URL: 'https://api.gwa.demos.legalpythia.com/v2',

  // API Endpoints
  ENDPOINTS: {
    UPLOAD: '/upload',
    CHAT: '/chat',
    REPORT: '/report',
    WIKIRATE: '/wikirate',
    DASHBOARD: '/dashboard',
  },

  // Timeout setting
  TIMEOUT: 30000,

  // Retry count
  RETRY_COUNT: 3,
};

// Check if in development environment
export const IS_DEV = import.meta.env.DEV;

// Get full API URL
export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
