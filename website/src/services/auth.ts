const FARMER_ID_KEY = "farmer_id";
const FARMER_DATA_KEY = "farmer_data";

export interface FarmerData {
  id: string;
  name: string;
  phone_number: string;
  email?: string;
  village?: string;
  district?: string;
  state?: string;
  land_size?: number;
  crop_type?: string;
  farm_income?: number;
}

export const DEMO_FARMERS = [
  { id: "F1001", name: "Rajesh Kumar", phone: "9876543210" },
  { id: "F1002", name: "Priya Sharma", phone: "9876543211" },
  { id: "F1003", name: "Amit Patel", phone: "9876543212" },
  { id: "F1004", name: "Sunita Devi", phone: "9876543213" },
  { id: "F1005", name: "Vikram Singh", phone: "9876543214" },
];

class AuthService {
  login(farmerId: string, farmerName: string): void {
    localStorage.setItem(FARMER_ID_KEY, farmerId);
    localStorage.setItem(
      FARMER_DATA_KEY,
      JSON.stringify({ id: farmerId, name: farmerName })
    );
  }

  logout(): void {
    localStorage.removeItem(FARMER_ID_KEY);
    localStorage.removeItem(FARMER_DATA_KEY);
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem(FARMER_ID_KEY);
  }

  getFarmerId(): string | null {
    return localStorage.getItem(FARMER_ID_KEY);
  }

  getFarmerData(): FarmerData | null {
    const data = localStorage.getItem(FARMER_DATA_KEY);
    return data ? JSON.parse(data) : null;
  }

  updateFarmerData(updates: Partial<FarmerData>): void {
    const current = this.getFarmerData();
    const updated = { ...current, ...updates };
    localStorage.setItem(FARMER_DATA_KEY, JSON.stringify(updated));
  }
}

export const authService = new AuthService();
