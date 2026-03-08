import AsyncStorage from "@react-native-async-storage/async-storage";

const API_BASE_URL = "http://<EC2_PUBLIC_IP>:8000"; // Replace with your EC2 Elastic IP

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async getHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    // API key auth (disabled by default on backend, but include just in case)
    headers["X-API-Key"] = "krishimandal-dev-key";
    return headers;
  }

  private async getFarmerId(): Promise<string> {
    const farmerId = await AsyncStorage.getItem("farmer_id");
    return farmerId || "F1001";
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }
    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }
    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "GET",
      headers,
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, body?: any): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async put<T>(endpoint: string, body?: any): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "PUT",
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async delete<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "DELETE",
      headers,
    });
    return this.handleResponse<T>(response);
  }

  // Convenience: get farmer ID for building paths
  async farmPath(suffix: string = ""): Promise<string> {
    const fid = await this.getFarmerId();
    return `/farm/${fid}${suffix}`;
  }
}

export const apiClient = new ApiClient();
