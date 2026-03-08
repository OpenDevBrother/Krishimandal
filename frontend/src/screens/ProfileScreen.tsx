import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { User, MapPin, Sprout, Save, LogOut, Loader } from "lucide-react-native";
import Toast from "react-native-toast-message";
import { useAuth } from "../services/authContext";
import { apiClient } from "../services/api";
import Header from "../components/Header";
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

export default function ProfileScreen() {
  const { farmer, logout, updateFarmer } = useAuth();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const [form, setForm] = useState({
    name: "",
    email: "",
    state: "",
    district: "",
    village: "",
    land_size: "0",
    crop_type: "",
    farm_income: "0",
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const path = await apiClient.farmPath("");
      const data = await apiClient.get<any>(path);
      setForm({
        name: data.name || farmer?.name || "",
        email: data.email || "",
        state: data.state || "",
        district: data.district || "",
        village: data.village || "",
        land_size: (data.land_size || 0).toString(),
        crop_type: data.crop_type || "",
        farm_income: (data.farm_income || 0).toString(),
      });
    } catch {
      // Use local farmer data
      if (farmer) {
        setForm({
          name: farmer.name || "",
          email: farmer.email || "",
          state: farmer.state || "",
          district: farmer.district || "",
          village: farmer.village || "",
          land_size: (farmer.land_size || 0).toString(),
          crop_type: farmer.crop_type || "",
          farm_income: (farmer.farm_income || 0).toString(),
        });
      }
    } finally {
      setFetching(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const path = await apiClient.farmPath("");
      await apiClient.put(path, {
        name: form.name,
        email: form.email,
        state: form.state,
        district: form.district,
        village: form.village,
        land_size: parseFloat(form.land_size) || 0,
        crop_type: form.crop_type,
        farm_income: parseFloat(form.farm_income) || 0,
      });

      // Update local auth state
      await updateFarmer({
        name: form.name,
        email: form.email,
        state: form.state,
        district: form.district,
        village: form.village,
        land_size: parseFloat(form.land_size) || 0,
        crop_type: form.crop_type,
        farm_income: parseFloat(form.farm_income) || 0,
      });

      Toast.show({ type: "success", text1: "Profile updated successfully!" });
    } catch (err: any) {
      Toast.show({
        type: "error",
        text1: err.message || "Failed to update profile",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    Toast.show({ type: "success", text1: "Logged out successfully" });
  };

  if (fetching) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Header />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Header */}
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Profile</Text>
            <Text style={styles.subtitle}>
              Complete your profile to auto-fill applications
            </Text>
          </View>
          <Button variant="outline" size="sm" onPress={handleLogout}>
            <View style={styles.logoutRow}>
              <LogOut size={16} color={colors.primary} />
              <Text style={styles.logoutText}>Logout</Text>
            </View>
          </Button>
        </View>

        {/* Personal Details */}
        <Card style={styles.mb16}>
          <View style={styles.cardHeader}>
            <User size={20} color={colors.gray[700]} />
            <Text style={styles.cardTitle}>Personal Details</Text>
          </View>
          <Input
            label="Full Name *"
            value={form.name}
            onChangeText={(t) => setForm({ ...form, name: t })}
          />
          <View style={{ marginTop: 12 }}>
            <Input
              label="Email Address"
              value={form.email}
              onChangeText={(t) => setForm({ ...form, email: t })}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          </View>
        </Card>

        {/* Location */}
        <Card style={styles.mb16}>
          <View style={styles.cardHeader}>
            <MapPin size={20} color={colors.gray[700]} />
            <Text style={styles.cardTitle}>Location Details</Text>
          </View>
          <Select
            label="State *"
            options={STATES}
            value={form.state}
            onValueChange={(v) => setForm({ ...form, state: v })}
            placeholder="Select state"
          />
          <View style={{ marginTop: 12 }}>
            <Input
              label="District *"
              value={form.district}
              onChangeText={(t) => setForm({ ...form, district: t })}
            />
          </View>
          <View style={{ marginTop: 12 }}>
            <Input
              label="Village/Town *"
              value={form.village}
              onChangeText={(t) => setForm({ ...form, village: t })}
            />
          </View>
        </Card>

        {/* Farm Details */}
        <Card style={styles.mb16}>
          <View style={styles.cardHeader}>
            <Sprout size={20} color={colors.gray[700]} />
            <Text style={styles.cardTitle}>Farm Details</Text>
          </View>
          <Input
            label="Land Size (acres) *"
            value={form.land_size}
            onChangeText={(t) => setForm({ ...form, land_size: t })}
            keyboardType="decimal-pad"
          />
          <View style={{ marginTop: 12 }}>
            <Select
              label="Primary Crop Type"
              options={CROPS}
              value={form.crop_type}
              onValueChange={(v) => setForm({ ...form, crop_type: v })}
              placeholder="Select primary crop"
            />
          </View>
          <View style={{ marginTop: 12 }}>
            <Input
              label="Annual Farm Income (Rs)"
              value={form.farm_income}
              onChangeText={(t) => setForm({ ...form, farm_income: t })}
              keyboardType="number-pad"
            />
          </View>
        </Card>

        {/* Save Button */}
        <Button
          onPress={handleSave}
          loading={loading}
          fullWidth
          size="lg"
        >
          <View style={styles.saveBtnRow}>
            <Save size={18} color={colors.white} />
            <Text style={styles.saveBtnText}>
              {loading ? "Saving..." : "Save Profile"}
            </Text>
          </View>
        </Button>

        <View style={{ height: 32 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 20,
  },
  title: { fontSize: 22, fontWeight: "700", color: colors.gray[900], marginBottom: 2 },
  subtitle: { fontSize: 14, color: colors.gray[500] },
  mb16: { marginBottom: 16 },
  logoutRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  logoutText: { fontSize: 13, fontWeight: "600", color: colors.primary },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
  },
  cardTitle: { fontSize: 16, fontWeight: "700", color: colors.gray[800] },
  saveBtnRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  saveBtnText: { fontSize: 16, fontWeight: "600", color: colors.white },
});
