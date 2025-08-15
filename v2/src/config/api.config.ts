// API 配置
export const API_CONFIG = {
  // 开发环境使用本地后端
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/v1',
  
  // API 端点
  ENDPOINTS: {
    UPLOAD: '/upload',
    CHAT: '/chat',
    REPORT: '/report',
    WIKIRATE: '/wikirate',
    DASHBOARD: '/dashboard',
  },
  
  // 超时设置
  TIMEOUT: 30000,
  
  // 重试次数
  RETRY_COUNT: 3,
};

// 检查是否为开发环境
export const IS_DEV = import.meta.env.DEV;

// 获取完整的 API URL
export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
