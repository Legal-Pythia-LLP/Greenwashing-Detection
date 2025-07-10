import axios from 'axios';

// const api = axios.create({baseURL: 'https://api.hlt.prototypes.legalpythia.com'});
//const api = axios.create({baseURL: 'https://api.bma.demos.legalpythia.com'});
const api = axios.create({baseURL: 'http://127.0.0.1:8000'});
// const api = axios.create({
//   baseURL: process.env.NEXT_PUBLIC_API_URL,
// });

export class APIService {
  static async uploadFile(file: File, session_id: string) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('session_id', session_id);

    const response = await api.post('/v1/upload', fd, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  static async validateUpload(summary: string, companyName: string, session_id: string) {
    const jsonData = JSON.stringify({
      summary,
      companyName,
      session_id,
    });

    const response = await api.post('/v1/validate', jsonData, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return response.data;
  }

  static async sendChatMessage(message: string, session_id: string) {
    const response = await api.post(
      '/v1/chat',
      {message, session_id},
      {
        adapter: 'fetch',
        headers: {'Content-Type': 'application/json'},
        responseType: 'stream',
      }
    );

    return response.data;
  }
}
