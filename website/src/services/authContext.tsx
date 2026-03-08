import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { authService, type FarmerData } from "./auth";

interface AuthContextType {
  isAuthenticated: boolean;
  farmer: FarmerData | null;
  loading: boolean;
  login: (farmerId: string, farmerName: string) => void;
  logout: () => void;
  updateFarmer: (updates: Partial<FarmerData>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [farmer, setFarmer] = useState<FarmerData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const authenticated = authService.isAuthenticated();
    if (authenticated) {
      const data = authService.getFarmerData();
      setFarmer(data);
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const login = (farmerId: string, farmerName: string) => {
    authService.login(farmerId, farmerName);
    setFarmer({ id: farmerId, name: farmerName, phone_number: "" });
    setIsAuthenticated(true);
  };

  const logout = () => {
    authService.logout();
    setFarmer(null);
    setIsAuthenticated(false);
  };

  const updateFarmer = (updates: Partial<FarmerData>) => {
    authService.updateFarmerData(updates);
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
