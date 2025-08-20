import axios from "axios";
import { API_CONFIG } from "@/config/api.config";

// Create an axios instance, connecting to the backend API
export const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
});

export class APIService {
  // File upload API
  static async uploadFile(formData: FormData) {
    // Now accepts the complete FormData object, which can include multiple fields

    try {
      console.log(
        "Attempting to upload to:",
        api.defaults.baseURL + "/upload"
      );
      const response = await api.post("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        timeout: 0, // Disable timeout, ESG analysis may take a long time
      });
      console.log("Upload successful:", response.data);
      return response.data; // Return backend data, including session_id
    } catch (error: any) {
      console.error("Upload error details:", {
        message: error.message,
        code: error.code,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
      });

      // Provide a friendlier error message
      if (error.code === "ECONNABORTED") {
        throw new Error("Upload timed out, please check your network connection or try again later");
      } else if (error.response?.status === 404) {
        throw new Error("API endpoint not found, please check backend service configuration");
      } else if (error.response?.status >= 500) {
        throw new Error("Internal server error, please try again later");
      } else {
        throw new Error(`Upload failed: ${error.message}`);
      }
    }
  }

  // Chat API
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

  // Get report API
  static async getReport(session_id: string) {
    try {
      const response = await api.get(`/report/${session_id}`);
      return response.data;
    } catch (error) {
      console.error("Get report error:", error);
      throw error;
    }
  }

  // Get WikiRate data API
  static async getWikiRateData(company_name: string) {
    try {
      const response = await api.get(`/wikirate/${company_name}`);
      return response.data;
    } catch (error) {
      console.error("WikiRate error:", error);
      throw error;
    }
  }

  // Get dashboard data API
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
      // Return empty data instead of throwing an error
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

  // Get risk trends data API
  static async getRiskTrends() {
    try {
      const response = await api.get("/dashboard/trends");
      return response.data;
    } catch (error) {
      console.error("Risk trends error:", error);
      throw error;
    }
  }

  // Get conversation history API
  static async getConversation(session_id: string) {
    try {
      const response = await api.get(`/get_conversation/${session_id}`);
      return response.data;
    } catch (error) {
      console.error("Get conversation error:", error);
      throw error;
    }
  }
}
