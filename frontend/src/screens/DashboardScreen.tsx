import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import {
  Sun,
  Droplets,
  Sprout,
  CheckCircle,
  FileText,
  TrendingUp,
  AlertCircle,
} from "lucide-react-native";
import Svg, { Path } from "react-native-svg";
import Toast from "react-native-toast-message";
import { useAuth } from "../services/authContext";
import { apiClient } from "../services/api";
import Header from "../components/Header";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";
import type { DashboardScreenProps } from "../navigation/types";

interface AppItem {
  id: string;
  scheme_name?: string;
  status: string;
  submitted_date?: string;
  created_at?: string;
}

interface InvItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  threshold?: number;
  alert_threshold?: number;
}

interface SchemeItem {
  id: string;
  name: string;
  scheme_id?: string;
  scheme_name?: string;
  deadline?: string;
}

export default function DashboardScreen({ navigation }: DashboardScreenProps) {
  const { farmer } = useAuth();
  const [applications, setApplications] = useState<AppItem[]>([]);
  const [lowStock, setLowStock] = useState<InvItem[]>([]);
  const [schemes, setSchemes] = useState<SchemeItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [weatherTemp, setWeatherTemp] = useState<string>("--");
  const [weatherRain, setWeatherRain] = useState<string>("--");
  const [weatherCondition, setWeatherCondition] = useState<string>("clear");
  const [farmLocation, setFarmLocation] = useState<string>("");

  const fetchData = async () => {
    try {
      const [appsPath, invPath, schemesPath, statePath] = await Promise.all([
        apiClient.farmPath("/applications"),
        apiClient.farmPath("/inventory/alerts"),
        apiClient.farmPath("/schemes"),
        apiClient.farmPath("/state"),
      ]);

      const [appsData, invData, schemesData, stateData] = await Promise.allSettled([
        apiClient.get<AppItem[]>(appsPath),
        apiClient.get<InvItem[]>(invPath),
        apiClient.get<SchemeItem[]>(schemesPath),
        apiClient.get<any>(statePath),
      ]);

      if (stateData.status === "fulfilled") {
        const w = stateData.value?.weather;
        if (w) {
          setWeatherTemp(`${Math.round(w.temperature_c)}°C`);
          setWeatherRain(`Rain: ${Math.round(w.humidity_pct)}%`);
          setWeatherCondition(w.condition || "clear");
        }
      }

      if (appsData.status === "fulfilled") setApplications(appsData.value.slice(0, 2));
      if (invData.status === "fulfilled") setLowStock(invData.value.slice(0, 2));
      if (schemesData.status === "fulfilled") {
        const mapped = schemesData.value.map((s: any) => ({
          id: s.id || s.scheme_id,
          name: s.name || s.scheme_name,
          deadline: s.deadline,
        }));
        setSchemes(mapped.slice(0, 3));
      }
    } catch {
      Toast.show({ type: "error", text1: "Could not connect to server" });
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { bg: string; text: string }> = {
      approved: { bg: colors.green[100], text: colors.green[700] },
      rejected: { bg: colors.red[100], text: colors.red[700] },
      under_review: { bg: colors.blue[100], text: colors.blue[700] },
      submitted: { bg: colors.purple[100], text: colors.purple[700] },
      draft: { bg: colors.gray[100], text: colors.gray[700] },
      pending: { bg: colors.amber[100], text: colors.amber[700] },
    };
    const s = map[status] || map.draft;
    return <Badge label={status.replace("_", " ")} bgColor={s.bg} textColor={s.text} />;
  };

  return (
    <View style={styles.container}>
      <Header />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.primary]} />
        }
      >
        {/* Welcome */}
        <View style={styles.section}>
          <Text style={styles.welcome}>
            Namaste, {farmer?.name || "Farmer"}!
          </Text>
          <Text style={styles.subtext}>Let's check your farm today</Text>
        </View>

        {/* Stats Row */}
        <View style={styles.statsRow}>
          {/* Farm Health */}
          <Card style={styles.statCard}>
            <View style={styles.statCenter}>
              <View style={styles.healthRing}>
                <Svg width={80} height={80} viewBox="0 0 36 36">
                  <Path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke={colors.primaryLight}
                    strokeWidth={3}
                  />
                  <Path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke={colors.primary}
                    strokeWidth={3}
                    strokeDasharray="85, 100"
                    strokeLinecap="round"
                  />
                </Svg>
                <Text style={styles.healthScore}>85</Text>
              </View>
              <Text style={styles.statLabel}>Farm Health</Text>
            </View>
          </Card>

          {/* Weather */}
          <Card style={styles.statCard}>
            <View style={styles.statCenter}>
              <View style={styles.weatherRow}>
                <Sun size={36} color={colors.yellow[500]} />
                <Text style={styles.tempText}>{weatherTemp}</Text>
              </View>
              <View style={styles.rainRow}>
                <Droplets size={14} color={colors.blue[500]} />
                <Text style={styles.rainText}>{weatherRain}</Text>
              </View>
              <Text style={styles.smallMuted}>
                {farmer?.village || farmer?.district || "Your Farm"}
              </Text>
            </View>
          </Card>
        </View>

        {/* Scheme Deadlines */}
        {schemes.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Scheme Deadlines</Text>
              <TouchableOpacity onPress={() => navigation.navigate("Schemes")}>
                <Text style={styles.viewAll}>View All</Text>
              </TouchableOpacity>
            </View>
            {schemes.map((scheme) => (
              <Card key={scheme.id} borderLeftColor={colors.amber[500]} style={styles.mb12}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemTitle} numberOfLines={1}>
                      {scheme.name}
                    </Text>
                    {scheme.deadline && (
                      <Text style={styles.smallMuted}>
                        Deadline: {new Date(scheme.deadline).toLocaleDateString()}
                      </Text>
                    )}
                  </View>
                  <Button
                    title="Apply"
                    variant="outline"
                    size="sm"
                    onPress={() =>
                      navigation.navigate("SchemeDetail", { schemeId: scheme.id })
                    }
                  />
                </View>
              </Card>
            ))}
          </View>
        )}

        {/* Crop Price */}
        <Card style={styles.mb16}>
          <View style={styles.row}>
            <View style={styles.cropIcon}>
              <Sprout size={18} color={colors.amber[700]} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.itemTitle}>Wheat (Gehu)</Text>
              <Text style={styles.smallMuted}>Indore Mandi</Text>
            </View>
            <Badge label="+2.4%" bgColor={colors.green[100]} textColor={colors.green[700]} />
          </View>
          <Text style={[styles.smallMuted, { marginTop: 12 }]}>Today's Price</Text>
          <Text style={styles.priceText}>
            ₹2,125 <Text style={styles.priceUnit}>/qt</Text>
          </Text>
          <View style={styles.progressBg}>
            <View style={[styles.progressFill, { width: "75%", backgroundColor: colors.green[600] }]} />
          </View>
        </Card>

        {/* Harvest Progress */}
        <Card style={styles.mb16}>
          <View style={styles.row}>
            <Text style={styles.sectionTitle}>Harvest in</Text>
            <Text style={styles.harvestDays}>15 Days</Text>
          </View>
          <View style={[styles.progressBg, { marginTop: 12 }]}>
            <View style={[styles.progressFill, { width: "70%" }]} />
          </View>
          <View style={[styles.row, { marginTop: 8 }]}>
            <Text style={styles.smallMuted}>Sowing</Text>
            <Text style={styles.smallMuted}>Growth</Text>
            <Text style={styles.smallMuted}>Maturity</Text>
          </View>
        </Card>

        {/* PM-KISAN Alert */}
        <Card style={{ ...styles.mb16, backgroundColor: colors.primary }}>
          <View style={styles.row}>
            <View style={styles.pmkisanIcon}>
              <CheckCircle size={22} color={colors.white} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.whiteTitle}>PM-KISAN</Text>
              <Text style={styles.whiteSubtext}>Eligibility Confirmed</Text>
            </View>
            <Button
              title="Check Now"
              variant="outline"
              size="sm"
              onPress={() =>
                navigation.navigate("SchemeDetail", { schemeId: "PMKISAN" })
              }
              style={{ backgroundColor: colors.white, borderColor: colors.white }}
              textStyle={{ color: colors.primary }}
            />
          </View>
        </Card>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity
            style={styles.quickCard}
            onPress={() => navigation.navigate("Schemes")}
            activeOpacity={0.7}
          >
            <Card style={styles.quickCardInner}>
              <View style={[styles.quickIcon, { backgroundColor: colors.green[100] }]}>
                <FileText size={24} color={colors.primary} />
              </View>
              <Text style={styles.quickLabel}>Browse Schemes</Text>
            </Card>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.quickCard}
            onPress={() => navigation.navigate("Inventory")}
            activeOpacity={0.7}
          >
            <Card style={styles.quickCardInner}>
              <View style={[styles.quickIcon, { backgroundColor: colors.blue[100] }]}>
                <TrendingUp size={24} color={colors.blue[600]} />
              </View>
              <Text style={styles.quickLabel}>Manage Inventory</Text>
            </Card>
          </TouchableOpacity>
        </View>

        {/* Recent Applications */}
        {applications.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Recent Applications</Text>
              <TouchableOpacity onPress={() => navigation.navigate("Applications")}>
                <Text style={styles.viewAll}>View All</Text>
              </TouchableOpacity>
            </View>
            {applications.map((app) => (
              <Card key={app.id} style={styles.mb12}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemTitle}>
                      {app.scheme_name || `Application ${app.id}`}
                    </Text>
                    <Text style={styles.smallMuted}>
                      {app.submitted_date || app.created_at
                        ? new Date(
                            app.submitted_date || app.created_at!
                          ).toLocaleDateString()
                        : "Draft"}
                    </Text>
                  </View>
                  {getStatusBadge(app.status)}
                </View>
              </Card>
            ))}
          </View>
        )}

        {/* Low Stock Alerts */}
        {lowStock.length > 0 && (
          <View style={styles.section}>
            <View style={[styles.sectionHeader, { gap: 8 }]}>
              <AlertCircle size={20} color={colors.red[600]} />
              <Text style={styles.sectionTitle}>Low Stock Alerts</Text>
            </View>
            {lowStock.map((item) => (
              <Card key={item.id} borderLeftColor={colors.red[500]} style={styles.mb12}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.itemTitle}>{item.name}</Text>
                    <Text style={[styles.smallMuted, { color: colors.red[600] }]}>
                      {item.quantity} {item.unit} remaining
                    </Text>
                  </View>
                  <Button
                    title="Manage"
                    variant="outline"
                    size="sm"
                    onPress={() => navigation.navigate("Inventory")}
                  />
                </View>
              </Card>
            ))}
          </View>
        )}

        <View style={{ height: 24 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  section: { marginBottom: 20 },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.gray[800] },
  viewAll: { fontSize: 13, fontWeight: "600", color: colors.primary },
  welcome: { fontSize: 22, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  subtext: { fontSize: 14, color: colors.gray[500] },
  statsRow: { flexDirection: "row", gap: 12, marginBottom: 20 },
  statCard: { flex: 1 },
  statCenter: { alignItems: "center" },
  healthRing: { width: 80, height: 80, alignItems: "center", justifyContent: "center", marginBottom: 8 },
  healthScore: {
    position: "absolute",
    fontSize: 24,
    fontWeight: "bold",
    color: colors.primary,
  },
  statLabel: { fontSize: 13, color: colors.gray[500] },
  weatherRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  tempText: { fontSize: 24, fontWeight: "bold", color: colors.gray[800] },
  rainRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  rainText: { fontSize: 12, color: colors.gray[500] },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  mb12: { marginBottom: 12 },
  mb16: { marginBottom: 16 },
  itemTitle: { fontSize: 14, fontWeight: "600", color: colors.gray[800], marginBottom: 2 },
  smallMuted: { fontSize: 12, color: colors.gray[500] },
  cropIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.amber[100],
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  priceText: { fontSize: 24, fontWeight: "bold", color: colors.primary, marginTop: 4 },
  priceUnit: { fontSize: 14, fontWeight: "normal", color: colors.gray[500] },
  progressBg: {
    height: 6,
    backgroundColor: colors.gray[200],
    borderRadius: 3,
    overflow: "hidden",
    marginTop: 12,
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.primary,
    borderRadius: 3,
  },
  harvestDays: { fontSize: 18, fontWeight: "bold", color: colors.gray[800] },
  pmkisanIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  whiteTitle: { fontSize: 15, fontWeight: "700", color: colors.white },
  whiteSubtext: { fontSize: 13, color: "rgba(255,255,255,0.9)" },
  quickActions: { flexDirection: "row", gap: 12, marginBottom: 20 },
  quickCard: { flex: 1 },
  quickCardInner: { alignItems: "center", paddingVertical: 20 },
  quickIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  quickLabel: { fontSize: 13, fontWeight: "600", color: colors.gray[700] },
});
