import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { authService, FarmerData } from "./auth";

interface AuthContextType {
  isAuthenticated: boolean;
  farmer: FarmerData | null;
  loading: boolean;
  login: (farmerId: string, farmerName: string) => Promise<void>;
  logout: () => Promise<void>;
  updateFarmer: (updates: Partial<FarmerData>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [farmer, setFarmer] = useState<FarmerData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const authenticated = await authService.isAuthenticated();
      if (authenticated) {
        const data = await authService.getFarmerData();
        setFarmer(data);
        setIsAuthenticated(true);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const login = async (farmerId: string, farmerName: string) => {
    await authService.login(farmerId, farmerName);
    setFarmer({ id: farmerId, name: farmerName, phone_number: "" });
    setIsAuthenticated(true);
  };

  const logout = async () => {
    await authService.logout();
    setFarmer(null);
    setIsAuthenticated(false);
  };

  const updateFarmer = async (updates: Partial<FarmerData>) => {
    await authService.updateFarmerData(updates);
    setFarmer((prev) => (prev ? { ...prev, ...updates } : null));
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, farmer, loading, login, logout, updateFarmer }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
