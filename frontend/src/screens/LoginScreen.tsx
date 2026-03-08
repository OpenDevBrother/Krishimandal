import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Leaf } from "lucide-react-native";
import Toast from "react-native-toast-message";
import { useAuth } from "../services/authContext";
import { DEMO_FARMERS } from "../services/auth";
import Input from "../components/Input";
import Button from "../components/Button";
import Card from "../components/Card";
import { colors } from "../constants/theme";

export default function LoginScreen() {
  const [phone, setPhone] = useState("");
  const [showFarmerPicker, setShowFarmerPicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSendOTP = () => {
    if (phone.length < 10) {
      Toast.show({ type: "error", text1: "Please enter a valid phone number" });
      return;
    }
    // Match phone to a demo farmer, or show picker
    const match = DEMO_FARMERS.find((f) => f.phone === phone);
    if (match) {
      handleLogin(match.id, match.name);
    } else {
      setShowFarmerPicker(true);
    }
  };

  const handleLogin = async (farmerId: string, farmerName: string) => {
    setLoading(true);
    try {
      await login(farmerId, farmerName);
      Toast.show({ type: "success", text1: "Login successful!" });
    } catch {
      Toast.show({ type: "error", text1: "Login failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.content}>
        <Card style={styles.card}>
          {/* Logo */}
          <View style={styles.logoWrap}>
            <View style={styles.logoCircle}>
              <Leaf size={32} color={colors.white} />
            </View>
          </View>
          <Text style={styles.title}>KrishiMandal</Text>
          <Text style={styles.subtitle}>Your Agriculture Platform</Text>

          {!showFarmerPicker ? (
            <View style={styles.form}>
              <View style={styles.phoneRow}>
                <Text style={styles.prefix}>+91</Text>
                <Input
                  placeholder="Enter 10-digit mobile number"
                  value={phone}
                  onChangeText={(t) =>
                    setPhone(t.replace(/\D/g, "").slice(0, 10))
                  }
                  keyboardType="phone-pad"
                  style={{ flex: 1 }}
                />
              </View>
              <Button
                title="Send OTP"
                onPress={handleSendOTP}
                loading={loading}
                fullWidth
              />
            </View>
          ) : (
            <View style={styles.form}>
              <Text style={styles.pickerLabel}>Select a Demo Farmer</Text>
              <FlatList
                data={DEMO_FARMERS}
                keyExtractor={(item) => item.id}
                scrollEnabled={false}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.farmerItem}
                    onPress={() => handleLogin(item.id, item.name)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.farmerAvatar}>
                      <Text style={styles.farmerAvatarText}>
                        {item.name[0]}
                      </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.farmerName}>{item.name}</Text>
                      <Text style={styles.farmerId}>{item.id}</Text>
                    </View>
                  </TouchableOpacity>
                )}
              />
              <Button
                title="Change Phone Number"
                variant="ghost"
                onPress={() => {
                  setShowFarmerPicker(false);
                  setPhone("");
                }}
                fullWidth
              />
            </View>
          )}
        </Card>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.gray[50],
  },
  content: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 20,
  },
  card: {
    paddingVertical: 32,
    paddingHorizontal: 24,
  },
  logoWrap: {
    alignItems: "center",
    marginBottom: 16,
  },
  logoCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    color: colors.primary,
    textAlign: "center",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: colors.gray[500],
    textAlign: "center",
    marginBottom: 24,
  },
  form: {
    gap: 16,
  },
  phoneRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  prefix: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.gray[600],
    paddingBottom: 14,
  },
  pickerLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.gray[700],
    marginBottom: 8,
  },
  farmerItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: colors.gray[50],
    marginBottom: 8,
  },
  farmerAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  farmerAvatarText: {
    fontSize: 16,
    fontWeight: "bold",
    color: colors.primary,
  },
  farmerName: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.gray[800],
  },
  farmerId: {
    fontSize: 12,
    color: colors.gray[500],
  },
});
