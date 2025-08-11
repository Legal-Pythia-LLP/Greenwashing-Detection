import axios from 'axios';
import { mockUploadResponse } from './mockData';

// const api = axios.create({baseURL: 'https://api.hlt.prototypes.legalpythia.com'});
// const api = axios.create({baseURL: 'https://api.bma.demos.legalpythia.com'});
const api = axios.create({baseURL: 'http://127.0.0.1:8000'});

export class APIService {
  static async uploadFile(
    file: File,
    session_id: string, 
    overrided_language?: string,
    forceMock = false
  ) {
    // 开发环境下或强制模拟时返回模拟数据
    if (process.env.NODE_ENV === 'development' || forceMock) {
      console.log('Returning mock data');
      return {
        ...mockUploadResponse,
        session_id: session_id,
        overrided_language: overrided_language || "en"
      };
    }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('session_id', session_id);
    
    // 添加语言参数（如果提供）
    if (overrided_language) {
      fd.append('overrided_language', overrided_language);
    }

    const response = await api.post('/upload', fd, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  static async sendChatMessage(message: string, session_id: string) {
    const response = await api.post(
      '/chat',
      {message, session_id},
      {
        headers: {'Content-Type': 'application/json'},
        responseType: 'stream',
      }
    );

    return response.data;
  }
}
