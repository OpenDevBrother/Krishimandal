import AsyncStorage from "@react-native-async-storage/async-storage";

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

// Demo farmers available for login
export const DEMO_FARMERS = [
  { id: "F1001", name: "Rajesh Kumar", phone: "9876543210" },
  { id: "F1002", name: "Priya Sharma", phone: "9876543211" },
  { id: "F1003", name: "Amit Patel", phone: "9876543212" },
  { id: "F1004", name: "Sunita Devi", phone: "9876543213" },
  { id: "F1005", name: "Vikram Singh", phone: "9876543214" },
];

class AuthService {
  async login(farmerId: string, farmerName: string): Promise<void> {
    await AsyncStorage.setItem(FARMER_ID_KEY, farmerId);
    await AsyncStorage.setItem(
      FARMER_DATA_KEY,
      JSON.stringify({ id: farmerId, name: farmerName })
    );
  }

  async logout(): Promise<void> {
    await AsyncStorage.removeItem(FARMER_ID_KEY);
    await AsyncStorage.removeItem(FARMER_DATA_KEY);
  }

  async isAuthenticated(): Promise<boolean> {
    const farmerId = await AsyncStorage.getItem(FARMER_ID_KEY);
    return !!farmerId;
  }

  async getFarmerId(): Promise<string | null> {
    return AsyncStorage.getItem(FARMER_ID_KEY);
  }

  async getFarmerData(): Promise<FarmerData | null> {
    const data = await AsyncStorage.getItem(FARMER_DATA_KEY);
    return data ? JSON.parse(data) : null;
  }

  async updateFarmerData(updates: Partial<FarmerData>): Promise<void> {
    const current = await this.getFarmerData();
    const updated = { ...current, ...updates };
    await AsyncStorage.setItem(FARMER_DATA_KEY, JSON.stringify(updated));
  }
}

export const authService = new AuthService();
