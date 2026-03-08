import { useState } from "react";
import { Leaf } from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "../services/authContext";
import { DEMO_FARMERS } from "../services/auth";
import Input from "../components/Input";
import Button from "../components/Button";
import Card from "../components/Card";
import { colors } from "../constants/theme";

export default function LoginPage() {
  const [phone, setPhone] = useState("");
  const [showFarmerPicker, setShowFarmerPicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSendOTP = () => {
    if (phone.length < 10) {
      toast.error("Please enter a valid phone number");
      return;
    }
    const match = DEMO_FARMERS.find((f) => f.phone === phone);
    if (match) {
      handleLogin(match.id, match.name);
    } else {
      setShowFarmerPicker(true);
    }
  };

  const handleLogin = (farmerId: string, farmerName: string) => {
    setLoading(true);
    try {
      login(farmerId, farmerName);
      toast.success("Login successful!");
    } catch {
      toast.error("Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-5" style={{ backgroundColor: colors.gray[50] }}>
      <Card className="w-full max-w-md py-8 px-6">
        {/* Logo */}
        <div className="flex justify-center mb-4">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center"
            style={{ backgroundColor: colors.primary }}
          >
            <Leaf size={32} color={colors.white} />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center mb-1" style={{ color: colors.primary }}>
          KrishiMandal
        </h1>
        <p className="text-sm text-center mb-6" style={{ color: colors.gray[500] }}>
          Your Agriculture Platform
        </p>

        {!showFarmerPicker ? (
          <div className="space-y-4">
            <div className="flex items-end gap-2">
              <span className="text-sm font-medium pb-3.5" style={{ color: colors.gray[600] }}>
                +91
              </span>
              <div className="flex-1">
                <Input
                  placeholder="Enter 10-digit mobile number"
                  value={phone}
                  onChange={(e) =>
                    setPhone((e.target as HTMLInputElement).value.replace(/\D/g, "").slice(0, 10))
                  }
                  type="tel"
                />
              </div>
            </div>
            <Button title="Send OTP" onPress={handleSendOTP} loading={loading} fullWidth />
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm font-semibold" style={{ color: colors.gray[700] }}>
              Select a Demo Farmer
            </p>
            {DEMO_FARMERS.map((farmer) => (
              <button
                key={farmer.id}
                onClick={() => handleLogin(farmer.id, farmer.name)}
                className="w-full flex items-center gap-3 py-3 px-3 rounded-lg border-none cursor-pointer transition-colors hover:opacity-80"
                style={{ backgroundColor: colors.gray[50] }}
              >
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-base font-bold"
                  style={{ backgroundColor: colors.primaryLight, color: colors.primary }}
                >
                  {farmer.name[0]}
                </div>
                <div className="text-left">
                  <div className="text-sm font-semibold" style={{ color: colors.gray[800] }}>
                    {farmer.name}
                  </div>
                  <div className="text-xs" style={{ color: colors.gray[500] }}>
                    {farmer.id}
                  </div>
                </div>
              </button>
            ))}
            <Button
              title="Change Phone Number"
              variant="ghost"
              onPress={() => {
                setShowFarmerPicker(false);
                setPhone("");
              }}
              fullWidth
            />
          </div>
        )}
      </Card>
    </div>
  );
}
