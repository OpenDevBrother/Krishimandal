import { useState, useEffect } from "react";
import { User, MapPin, Sprout, Save, LogOut } from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "../services/authContext";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Input from "../components/Input";
import Select from "../components/Select";
import Button from "../components/Button";
import { colors } from "../constants/theme";

const STATES = [
  "Andhra Pradesh", "Bihar", "Gujarat", "Haryana", "Karnataka", "Kerala",
  "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan",
  "Tamil Nadu", "Telangana", "Uttar Pradesh", "West Bengal",
].map((s) => ({ value: s, label: s }));

const CROPS = [
  "Rice", "Wheat", "Cotton", "Sugarcane", "Maize", "Pulses",
  "Groundnut", "Soybean", "Vegetables", "Fruits",
].map((c) => ({ value: c, label: c }));

export default function ProfilePage() {
  const { farmer, logout, updateFarmer } = useAuth();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [form, setForm] = useState({
    name: "", email: "", state: "", district: "",
    village: "", land_size: "0", crop_type: "", farm_income: "0",
  });

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const data = await apiClient.get<any>(apiClient.farmPath(""));
      setForm({
        name: data.name || farmer?.name || "", email: data.email || "",
        state: data.state || "", district: data.district || "",
        village: data.village || "", land_size: (data.land_size || 0).toString(),
        crop_type: data.crop_type || "", farm_income: (data.farm_income || 0).toString(),
      });
    } catch {
      if (farmer) {
        setForm({
          name: farmer.name || "", email: farmer.email || "",
          state: farmer.state || "", district: farmer.district || "",
          village: farmer.village || "", land_size: (farmer.land_size || 0).toString(),
          crop_type: farmer.crop_type || "", farm_income: (farmer.farm_income || 0).toString(),
        });
      }
    } finally { setFetching(false); }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await apiClient.put(apiClient.farmPath(""), {
        name: form.name, email: form.email, state: form.state,
        district: form.district, village: form.village,
        land_size: parseFloat(form.land_size) || 0,
        crop_type: form.crop_type, farm_income: parseFloat(form.farm_income) || 0,
      });
      updateFarmer({
        name: form.name, email: form.email, state: form.state,
        district: form.district, village: form.village,
        land_size: parseFloat(form.land_size) || 0,
        crop_type: form.crop_type, farm_income: parseFloat(form.farm_income) || 0,
      });
      toast.success("Profile updated successfully!");
    } catch (err: any) { toast.error(err.message || "Failed to update profile"); }
    finally { setLoading(false); }
  };

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
  };

  if (fetching) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-t-transparent rounded-full animate-spin" style={{ borderColor: colors.primary, borderTopColor: "transparent" }} /></div>;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex justify-between items-start mb-5">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: colors.gray[900] }}>Profile</h1>
          <p className="text-sm" style={{ color: colors.gray[500] }}>Complete your profile to auto-fill applications</p>
        </div>
        <Button variant="outline" size="sm" onPress={handleLogout}>
          <div className="flex items-center gap-1.5">
            <LogOut size={16} color={colors.primary} />
            <span className="text-sm font-semibold" style={{ color: colors.primary }}>Logout</span>
          </div>
        </Button>
      </div>

      <Card className="mb-4">
        <div className="flex items-center gap-2 mb-4">
          <User size={20} color={colors.gray[700]} />
          <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Personal Details</h2>
        </div>
        <Input label="Full Name *" value={form.name} onChange={(e) => setForm({ ...form, name: (e.target as HTMLInputElement).value })} />
        <div className="mt-3">
          <Input label="Email Address" value={form.email} onChange={(e) => setForm({ ...form, email: (e.target as HTMLInputElement).value })} type="email" />
        </div>
      </Card>

      <Card className="mb-4">
        <div className="flex items-center gap-2 mb-4">
          <MapPin size={20} color={colors.gray[700]} />
          <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Location Details</h2>
        </div>
        <Select label="State *" options={STATES} value={form.state} onValueChange={(v) => setForm({ ...form, state: v })} placeholder="Select state" />
        <div className="mt-3"><Input label="District *" value={form.district} onChange={(e) => setForm({ ...form, district: (e.target as HTMLInputElement).value })} /></div>
        <div className="mt-3"><Input label="Village/Town *" value={form.village} onChange={(e) => setForm({ ...form, village: (e.target as HTMLInputElement).value })} /></div>
      </Card>

      <Card className="mb-4">
        <div className="flex items-center gap-2 mb-4">
          <Sprout size={20} color={colors.gray[700]} />
          <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Farm Details</h2>
        </div>
        <Input label="Land Size (acres) *" value={form.land_size} onChange={(e) => setForm({ ...form, land_size: (e.target as HTMLInputElement).value })} type="number" />
        <div className="mt-3"><Select label="Primary Crop Type" options={CROPS} value={form.crop_type} onValueChange={(v) => setForm({ ...form, crop_type: v })} placeholder="Select primary crop" /></div>
        <div className="mt-3"><Input label="Annual Farm Income (Rs)" value={form.farm_income} onChange={(e) => setForm({ ...form, farm_income: (e.target as HTMLInputElement).value })} type="number" /></div>
      </Card>

      <Button onPress={handleSave} loading={loading} fullWidth size="lg">
        <div className="flex items-center gap-2">
          <Save size={18} color={colors.white} />
          <span className="text-base font-semibold text-white">{loading ? "Saving..." : "Save Profile"}</span>
        </div>
      </Button>

      <div className="h-8" />
    </div>
  );
}
