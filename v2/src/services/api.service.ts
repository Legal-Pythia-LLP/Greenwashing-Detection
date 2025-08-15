import axios from "axios";

// 创建 axios 实例，连接到后端 API
export const api = axios.create({
  baseURL: "http://127.0.0.1:8000/v1",
  timeout: 0, // 禁用超时，让请求一直等待
});

export class APIService {
  // 文件上传接口
  static async uploadFile(formData: FormData) {
    // 现在接受完整的FormData对象，可以包含多个字段

    try {
      console.log(
        "Attempting to upload to:",
        api.defaults.baseURL + "/upload"
      );
      const response = await api.post("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        timeout: 0, // 禁用超时，ESG 分析可能需要很长时间
      });
      console.log("Upload successful:", response.data);
      return response.data; // 返回后端数据，包含 session_id
    } catch (error: any) {
      console.error("Upload error details:", {
        message: error.message,
        code: error.code,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
      });

      // 提供更友好的错误信息
      if (error.code === "ECONNABORTED") {
        throw new Error("上传超时，请检查网络连接或稍后重试");
      } else if (error.response?.status === 404) {
        throw new Error("API 接口不存在，请检查后端服务配置");
      } else if (error.response?.status >= 500) {
        throw new Error("服务器内部错误，请稍后重试");
      } else {
        throw new Error(`上传失败: ${error.message}`);
      }
    }
  }

  // 聊天接口
  static async sendChatMessage(message: string, session_id: string) {
    try {
      const response = await api.post("/chat", {
        message,
        session_id,
      });
      return response.data;
    } catch (error) {
      console.error("Chat error:", error);
      throw error;
    }
  }

  // 获取报告接口
  static async getReport(session_id: string) {
    try {
      const response = await api.get(`/report/${session_id}`);
      return response.data;
    } catch (error) {
      console.error("Get report error:", error);
      throw error;
    }
  }

  // 获取 WikiRate 数据接口
  static async getWikiRateData(company_name: string) {
    try {
      const response = await api.get(`/wikirate/${company_name}`);
      return response.data;
    } catch (error) {
      console.error("WikiRate error:", error);
      throw error;
    }
  }

  // 获取仪表板数据接口
  static async getDashboardData() {
    try {
      const [statsRes, companiesRes] = await Promise.all([
        api.get("/dashboard/stats"),
        api.get("/dashboard/companies")
      ]);
      
      return {
        stats: statsRes.data,
        companies: companiesRes.data
      };
    } catch (error) {
      console.error("Dashboard error:", error);
      // 返回空数据而不是抛出错误
      return {
        stats: {
          high_risk_companies: 0,
          pending_reports: 0,
          high_priority_reports: 0
        },
        companies: []
      };
    }
  }
}
