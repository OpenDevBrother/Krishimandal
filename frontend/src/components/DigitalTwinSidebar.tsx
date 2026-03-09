import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  Dimensions,
  Platform,
} from "react-native";
import Svg, { Path } from "react-native-svg";
import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  Layers,
  X,
  RefreshCw,
  Sprout,
  Droplets,
  Thermometer,
  Wind,
  Activity,
  AlertTriangle,
  Calendar,
  Leaf,
  ChevronDown,
  ChevronUp,
} from "lucide-react-native";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import MarkdownRenderer from "./Markdown";

// ── Types ────────────────────────────────────────────────────────────────────

interface FarmProfile {
  farm_id: string;
  farmer_id: string;
  farmer_name: string;
  area_hectares: number;
  soil_type: string;
  irrigation_type: string;
  current_crops: {
    crop_type: string;
    variety: string;
    growth_stage: string;
    health_score: number;
    planting_date: string;
    area_hectares: number;
  }[];
  location: { lat: number; lng: number };
}

interface FarmState {
  farm_id: string;
  ndvi_mean: number;
  soil_moisture_pct: number;
  health_score: number;
  weather?: {
    temperature_c: number;
    humidity_pct: number;
    rainfall_mm: number;
    wind_speed_kmh: number;
    condition: string;
    forecast_7day?: {
      date: string;
      temp_min: number;
      temp_max: number;
      humidity: number;
      rainfall_mm: number;
      condition: string;
    }[];
  };
}

interface HarvestPrediction {
  crop: string;
  variety: string;
  growth_stage: string;
  days_since_planting: number;
  predicted_harvest_date: string;
  days_to_harvest: number;
  confidence: number;
  yield_estimate_quintals_per_hectare: number;
}

interface RiskAlert {
  type: string;
  severity: string;
  message: string;
}

interface SimulationResult {
  scenario: string;
  yield_impact_pct: number;
  recommendation: string;
  risk: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const SCENARIOS = [
  { key: "drought", label: "Drought" },
  { key: "pest_outbreak", label: "Pest Outbreak" },
  { key: "early_harvest", label: "Early Harvest" },
  { key: "alternative_crop", label: "Alt. Crop" },
];

const SCREEN_WIDTH = Dimensions.get("window").width;
const SIDEBAR_WIDTH = Math.min(320, SCREEN_WIDTH * 0.85);

// ── Sub-components ───────────────────────────────────────────────────────────

function GaugeRing({
  value,
  max,
  color,
  label,
  unit,
}: {
  value: number;
  max: number;
  color: string;
  label: string;
  unit: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  const displayValue =
    typeof value === "number" ? (value % 1 === 0 ? value.toString() : value.toFixed(1)) : String(value);

  return (
    <View style={gaugeStyles.wrap}>
      <View style={gaugeStyles.ring}>
        <Svg width={56} height={56} viewBox="0 0 36 36">
          <Path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={3}
          />
          <Path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke={color}
            strokeWidth={3}
            strokeDasharray={`${pct}, 100`}
            strokeLinecap="round"
          />
        </Svg>
        <Text style={[gaugeStyles.value, { color }]}>{displayValue}</Text>
      </View>
      <Text style={gaugeStyles.label}>{label}</Text>
      <Text style={gaugeStyles.unit}>{unit}</Text>
    </View>
  );
}

const gaugeStyles = StyleSheet.create({
  wrap: { alignItems: "center" },
  ring: { width: 56, height: 56, alignItems: "center", justifyContent: "center" },
  value: {
    position: "absolute",
    fontSize: 11,
    fontWeight: "bold",
  },
  label: { fontSize: 10, fontWeight: "600", color: colors.gray[500], marginTop: 4 },
  unit: { fontSize: 9, color: colors.gray[400] },
});

function SeverityDot({ severity }: { severity: string }) {
  const colorMap: Record<string, string> = {
    low: colors.green[600],
    medium: colors.amber[500],
    high: colors.red[500],
    critical: colors.red[700],
  };
  return (
    <View
      style={[
        dotStyles.dot,
        { backgroundColor: colorMap[severity] || colors.gray[400] },
      ]}
    />
  );
}

const dotStyles = StyleSheet.create({
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 6, marginTop: 3 },
});

function WeatherConditionIcon({ condition, size = 14 }: { condition: string; size?: number }) {
  const c = condition.toLowerCase();
  if (c.includes("rain") || c.includes("drizzle"))
    return <Droplets size={size} color={colors.blue[700]} />;
  if (c.includes("cloud"))
    return <Wind size={size} color={colors.gray[500]} />;
  return <Thermometer size={size} color={colors.amber[500]} />;
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function DigitalTwinSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<FarmProfile | null>(null);
  const [state, setState] = useState<FarmState | null>(null);
  const [harvest, setHarvest] = useState<HarvestPrediction | null>(null);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [forecastOpen, setForecastOpen] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const farmerId = (await AsyncStorage.getItem("farmer_id")) || "F1001";
      const farmPath = `/farm/${farmerId}`;
      const [profileRes, stateRes] = await Promise.allSettled([
        apiClient.get<FarmProfile>(farmPath),
        apiClient.get<FarmState>(`${farmPath}/state`),
      ]);

      if (profileRes.status === "fulfilled" && profileRes.value && typeof profileRes.value === "object") {
        const p = profileRes.value;
        setProfile({
          ...p,
          current_crops: Array.isArray(p.current_crops) ? p.current_crops : [],
        });
      }
      if (stateRes.status === "fulfilled" && stateRes.value && typeof stateRes.value === "object") {
        setState(stateRes.value);
      }

      // Harvest prediction
      try {
        const harvestRes = await apiClient.post<{
          final_response: string;
          agents_invoked: string[];
        }>("/query", {
          query: "predict harvest",
          farmer_id: farmerId,
          language: "en",
          context: { silent: true },
        });
        const resp = harvestRes.final_response;
        const daysMatch = resp.match(/(\d+)\s*days/);
        const yieldMatch = resp.match(/([\d.]+)\s*quintals/);
        const cropMatch = resp.match(/Your\s+(\w+)/i);
        const stageMatch = resp.match(/in the (\w+) stage/i);
        if (daysMatch) {
          setHarvest({
            crop: cropMatch?.[1] || "Wheat",
            variety: "",
            growth_stage: stageMatch?.[1] || "vegetative",
            days_since_planting: 0,
            predicted_harvest_date: "",
            days_to_harvest: parseInt(daysMatch[1]),
            confidence: 0.78,
            yield_estimate_quintals_per_hectare: yieldMatch
              ? parseFloat(yieldMatch[1])
              : 18,
          });
        }
      } catch {
        // non-critical
      }

      // Risk alerts
      try {
        const alertRes = await apiClient.post<{ final_response: string }>("/query", {
          query: "farm risk alerts",
          farmer_id: farmerId,
          language: "en",
        });
        const parts = alertRes.final_response
          .split("|")
          .map((s) => s.trim())
          .filter(Boolean);
        setAlerts(
          parts.map((msg) => ({
            type: "alert",
            severity: msg.toLowerCase().includes("critical") ||
              msg.toLowerCase().includes("low at")
              ? "high"
              : msg.toLowerCase().includes("no immediate")
                ? "low"
                : "medium",
            message: msg,
          }))
        );
      } catch {
        // non-critical
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && !profile) fetchAll();
  }, [isOpen]);

  const runSimulation = async (scenario: string) => {
    setSimLoading(true);
    setSimulation(null);

    // Try remote API first, fall back to local calculation
    try {
      const res = await apiClient.post<SimulationResult>(
        await apiClient.farmPath("/simulate"),
        { scenario }
      );
      // Only use remote result if it has a real impact value
      if (res && res.yield_impact_pct !== undefined && res.yield_impact_pct !== 0) {
        setSimulation(res);
        setSimLoading(false);
        return;
      }
    } catch {
      // fall through to local simulation
    }

    // ── Local simulation using available farm data ──────────────────────
    const health = state?.health_score ?? 72;
    const moisture = state?.soil_moisture_pct ?? 45;
    const ndvi = state?.ndvi_mean ?? 0.55;
    const temp = state?.weather?.temperature_c ?? 28;
    const rainfall = state?.weather?.rainfall_mm ?? 2;
    const crop = profile?.current_crops?.[0]?.crop_type || "Wheat";
    const yieldEst = harvest?.yield_estimate_quintals_per_hectare ?? 18;

    let impact = 0;
    let risk: "low" | "medium" | "high" = "medium";
    let recommendation = "";
    let scenarioLabel = "";

    switch (scenario) {
      case "drought": {
        scenarioLabel = "Drought Scenario";
        // Impact based on current moisture — drier soil = worse impact
        const moistureFactor = moisture < 25 ? -35 : moisture < 40 ? -22 : -14;
        const healthFactor = health < 60 ? -8 : -3;
        impact = moistureFactor + healthFactor + Math.round((ndvi - 0.5) * -10);
        impact = Math.max(-45, Math.min(-5, impact));
        risk = impact < -25 ? "high" : impact < -15 ? "medium" : "low";
        const estLoss = Math.abs(Math.round((yieldEst * impact) / 100 * 10) / 10);
        recommendation = `With current soil moisture at **${moisture}%**, a drought could reduce ${crop} yield by ~**${estLoss} qt/ha**. ${
          moisture < 30
            ? "**Urgent:** Set up drip irrigation immediately and apply mulch to retain moisture."
            : "Consider scheduling supplemental irrigation and applying organic mulch to conserve water."
        } NDVI of ${ndvi.toFixed(2)} suggests ${ndvi >= 0.5 ? "adequate" : "stressed"} vegetation cover.`;
        break;
      }
      case "pest_outbreak": {
        scenarioLabel = "Pest Outbreak";
        // Lower health = already vulnerable
        const vulnFactor = health < 60 ? -30 : health < 75 ? -20 : -12;
        const ndviFactor = ndvi < 0.4 ? -8 : -2;
        impact = vulnFactor + ndviFactor;
        impact = Math.max(-40, Math.min(-5, impact));
        risk = impact < -22 ? "high" : impact < -14 ? "medium" : "low";
        const estLoss = Math.abs(Math.round((yieldEst * impact) / 100 * 10) / 10);
        recommendation = `Current crop health of **${health}/100** makes ${crop} ${
          health < 70 ? "highly vulnerable" : "moderately resistant"
        } to pest attacks. Estimated yield loss: **${estLoss} qt/ha**. ${
          health < 70
            ? "Apply neem-based organic pesticide and inspect leaves daily. Contact KVK helpline (1800-180-1551) for IPM guidance."
            : "Monitor regularly with yellow sticky traps. Ensure proper spacing for air circulation."
        }`;
        break;
      }
      case "early_harvest": {
        scenarioLabel = "Early Harvest";
        const daysLeft = harvest?.days_to_harvest ?? 45;
        // Harvesting early means lower grain filling
        if (daysLeft > 30) {
          impact = Math.round(-15 - (daysLeft - 30) * 0.3);
          risk = "medium";
        } else if (daysLeft > 15) {
          impact = Math.round(-8 - (daysLeft - 15) * 0.2);
          risk = "low";
        } else {
          impact = -3;
          risk = "low";
        }
        impact = Math.max(-30, impact);
        const estLoss = Math.abs(Math.round((yieldEst * impact) / 100 * 10) / 10);
        recommendation = `Harvesting ${crop} **${daysLeft} days early** would reduce yield by ~**${estLoss} qt/ha** due to incomplete grain filling. ${
          daysLeft > 25
            ? "Not recommended — significant quality and weight loss expected."
            : daysLeft > 12
              ? "Possible with moderate losses. Consider if weather risks justify early harvest."
              : "Minimal impact — crop is near maturity. Safe to proceed if needed."
        }`;
        break;
      }
      case "alternative_crop": {
        scenarioLabel = "Alternative Crop";
        // Suggest rotation benefits
        const altCrops: Record<string, { name: string; gain: number; reason: string }> = {
          Wheat: { name: "Mustard", gain: 12, reason: "Mustard has lower water needs and current moisture suits it well" },
          Rice: { name: "Pulses (Moong)", gain: 15, reason: "Pulses fix nitrogen and improve soil health for next season" },
          Cotton: { name: "Soybean", gain: 10, reason: "Soybean requires less pesticide and enriches soil nitrogen" },
          Sugarcane: { name: "Maize", gain: 8, reason: "Maize has shorter cycle and lower irrigation requirement" },
        };
        const alt = altCrops[crop] || { name: "Pulses", gain: 10, reason: "crop rotation improves soil health and breaks pest cycles" };
        impact = alt.gain + (moisture > 40 ? 3 : 0) + (health > 70 ? 2 : -2);
        risk = "low";
        recommendation = `Switching from **${crop}** to **${alt.name}** could improve returns by ~**${impact}%** (≈ +${Math.round((yieldEst * impact) / 100 * 10) / 10} qt/ha equivalent). ${alt.reason}. Current conditions — moisture ${moisture}%, health ${health}/100 — ${
          moisture > 35 && health > 60
            ? "are favorable for this switch."
            : "may need soil preparation before switching."
        }`;
        break;
      }
      default:
        scenarioLabel = scenario;
        impact = -10;
        risk = "medium";
        recommendation = "No specific simulation available for this scenario.";
    }

    setSimulation({
      scenario: scenarioLabel,
      yield_impact_pct: impact,
      recommendation,
      risk,
    });
    setSimLoading(false);
  };

  const harvestProgress = harvest
    ? Math.max(5, Math.min(95, 100 - (harvest.days_to_harvest / 120) * 100))
    : 0;

  return (
    <>
      {/* Floating Toggle Button */}
      {!isOpen && (
        <TouchableOpacity
          style={styles.toggleBtn}
          onPress={() => setIsOpen(true)}
          activeOpacity={0.8}
        >
          <Layers size={18} color={colors.white} />
          <Text style={styles.toggleLabel}>TWIN</Text>
        </TouchableOpacity>
      )}

      {/* Sidebar Modal */}
      <Modal visible={isOpen} transparent animationType="slide">
        <View style={styles.overlay}>
          <TouchableOpacity
            style={styles.overlayDismiss}
            activeOpacity={1}
            onPress={() => setIsOpen(false)}
          />
          <View style={styles.sidebar}>
            {/* Header */}
            <View style={styles.sidebarHeader}>
              <Layers size={20} color={colors.white} />
              <View style={styles.headerTextWrap}>
                <Text style={styles.headerTitle}>Digital Twin</Text>
                <Text style={styles.headerSub}>
                  {profile ? `${profile.farmer_name}'s Farm` : "Farm Overview"}
                </Text>
              </View>
              <TouchableOpacity
                style={styles.headerBtn}
                onPress={fetchAll}
                disabled={loading}
              >
                <RefreshCw size={14} color={colors.white} />
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.headerBtn}
                onPress={() => setIsOpen(false)}
              >
                <X size={16} color={colors.white} />
              </TouchableOpacity>
            </View>

            {/* Content */}
            <ScrollView
              style={styles.content}
              contentContainerStyle={styles.contentContainer}
              showsVerticalScrollIndicator={false}
            >
              {loading && !state ? (
                <View style={styles.loadingCenter}>
                  <ActivityIndicator size="large" color={colors.primary} />
                </View>
              ) : (
                <>
                  {/* Farm Info */}
                  {profile && (
                    <View style={styles.section}>
                      <View style={styles.sectionHeader}>
                        <Leaf size={14} color={colors.primary} />
                        <Text style={styles.sectionTitle}>Farm Info</Text>
                      </View>
                      <View style={styles.infoGrid}>
                        <Text style={styles.infoLabel}>Area</Text>
                        <Text style={styles.infoValue}>{profile.area_hectares} ha</Text>
                        <Text style={styles.infoLabel}>Soil</Text>
                        <Text style={[styles.infoValue, styles.capitalize]}>
                          {profile.soil_type}
                        </Text>
                        <Text style={styles.infoLabel}>Irrigation</Text>
                        <Text style={[styles.infoValue, styles.capitalize]}>
                          {profile.irrigation_type}
                        </Text>
                        {profile.current_crops?.[0] && (
                          <>
                            <Text style={styles.infoLabel}>Crop</Text>
                            <Text style={styles.infoValue}>
                              {profile.current_crops[0].crop_type}
                              {profile.current_crops[0].variety
                                ? ` (${profile.current_crops[0].variety})`
                                : ""}
                            </Text>
                            <Text style={styles.infoLabel}>Stage</Text>
                            <Text
                              style={[
                                styles.infoValue,
                                styles.capitalize,
                                { color: colors.primary },
                              ]}
                            >
                              {profile.current_crops[0].growth_stage}
                            </Text>
                          </>
                        )}
                      </View>
                    </View>
                  )}

                  {/* Health Gauges */}
                  {state && (
                    <View style={styles.section}>
                      <View style={styles.sectionHeader}>
                        <Activity size={14} color={colors.primary} />
                        <Text style={styles.sectionTitle}>Farm Health Metrics</Text>
                      </View>
                      <View style={styles.gaugeRow}>
                        <GaugeRing
                          value={state.health_score}
                          max={100}
                          color={
                            state.health_score >= 70
                              ? colors.green[600]
                              : state.health_score >= 40
                                ? colors.amber[500]
                                : colors.red[500]
                          }
                          label="Health"
                          unit="/100"
                        />
                        <GaugeRing
                          value={state.ndvi_mean}
                          max={1}
                          color={
                            state.ndvi_mean >= 0.5
                              ? colors.green[600]
                              : colors.amber[500]
                          }
                          label="NDVI"
                          unit="index"
                        />
                        <GaugeRing
                          value={state.soil_moisture_pct}
                          max={100}
                          color={
                            state.soil_moisture_pct >= 30
                              ? colors.blue[600]
                              : colors.red[500]
                          }
                          label="Moisture"
                          unit="%"
                        />
                      </View>
                    </View>
                  )}

                  {/* Weather */}
                  {state?.weather && (
                    <View style={styles.section}>
                      <View style={styles.sectionHeader}>
                        <WeatherConditionIcon condition={state.weather.condition} />
                        <Text style={styles.sectionTitle}>Weather</Text>
                        <Text style={styles.weatherCondition}>
                          {state.weather.condition}
                        </Text>
                      </View>
                      <View style={styles.weatherGrid}>
                        <View style={styles.weatherItem}>
                          <Thermometer size={13} color={colors.red[500]} />
                          <Text style={styles.weatherValue}>
                            {Math.round(state.weather.temperature_c)}°C
                          </Text>
                        </View>
                        <View style={styles.weatherItem}>
                          <Droplets size={13} color={colors.blue[500]} />
                          <Text style={styles.weatherValue}>
                            {state.weather.humidity_pct}%
                          </Text>
                        </View>
                        <View style={styles.weatherItem}>
                          <Droplets size={13} color={colors.blue[700]} />
                          <Text style={styles.weatherValue}>
                            {state.weather.rainfall_mm} mm
                          </Text>
                        </View>
                        <View style={styles.weatherItem}>
                          <Wind size={13} color={colors.gray[500]} />
                          <Text style={styles.weatherValue}>
                            {Math.round(state.weather.wind_speed_kmh)} km/h
                          </Text>
                        </View>
                      </View>

                      {/* 7-day forecast */}
                      {state.weather.forecast_7day &&
                        state.weather.forecast_7day.length > 0 && (
                          <View style={styles.forecastWrap}>
                            <TouchableOpacity
                              style={styles.forecastToggle}
                              onPress={() => setForecastOpen(!forecastOpen)}
                            >
                              {forecastOpen ? (
                                <ChevronUp size={12} color={colors.primary} />
                              ) : (
                                <ChevronDown size={12} color={colors.primary} />
                              )}
                              <Text style={styles.forecastToggleText}>
                                7-Day Forecast
                              </Text>
                            </TouchableOpacity>
                            {forecastOpen &&
                              state.weather.forecast_7day.map((day, i) => (
                                <View key={i} style={styles.forecastDay}>
                                  <Text style={styles.forecastDate}>
                                    {new Date(day.date).toLocaleDateString("en-IN", {
                                      weekday: "short",
                                      day: "numeric",
                                    })}
                                  </Text>
                                  <WeatherConditionIcon
                                    condition={day.condition}
                                    size={12}
                                  />
                                  <Text style={styles.forecastTemp}>
                                    {Math.round(day.temp_min)}–
                                    {Math.round(day.temp_max)}°C
                                  </Text>
                                  <Text style={styles.forecastRain}>
                                    {day.rainfall_mm > 0
                                      ? `${day.rainfall_mm}mm`
                                      : "—"}
                                  </Text>
                                </View>
                              ))}
                          </View>
                        )}
                    </View>
                  )}

                  {/* Harvest Prediction */}
                  {harvest && (
                    <View style={styles.section}>
                      <View style={styles.sectionHeader}>
                        <Calendar size={14} color={colors.primary} />
                        <Text style={styles.sectionTitle}>Harvest Prediction</Text>
                      </View>
                      <View style={styles.harvestRow}>
                        <View>
                          <Text style={styles.harvestDays}>
                            {harvest.days_to_harvest} days
                          </Text>
                          <Text style={styles.harvestCrop}>
                            {harvest.crop} — {harvest.growth_stage}
                          </Text>
                        </View>
                        <View style={styles.harvestYield}>
                          <Text style={styles.yieldValue}>
                            {harvest.yield_estimate_quintals_per_hectare} qt/ha
                          </Text>
                          <Text style={styles.yieldLabel}>
                            est. yield ({Math.round(harvest.confidence * 100)}%)
                          </Text>
                        </View>
                      </View>
                      <View style={styles.progressBar}>
                        <View
                          style={[
                            styles.progressFill,
                            { width: `${harvestProgress}%` },
                          ]}
                        />
                      </View>
                      <View style={styles.progressLabels}>
                        <Text style={styles.progressLabel}>Sowing</Text>
                        <Text style={styles.progressLabel}>Growth</Text>
                        <Text style={styles.progressLabel}>Harvest</Text>
                      </View>
                    </View>
                  )}

                  {/* Risk Alerts */}
                  {alerts.length > 0 && (
                    <View style={styles.section}>
                      <View style={styles.sectionHeader}>
                        <AlertTriangle size={14} color={colors.amber[500]} />
                        <Text style={styles.sectionTitle}>Risk Alerts</Text>
                      </View>
                      {alerts.map((alert, i) => (
                        <View key={i} style={styles.alertRow}>
                          <SeverityDot severity={alert.severity} />
                          <View style={styles.alertTextWrap}>
                            <MarkdownRenderer fontSize={11} color={colors.gray[600]}>
                              {alert.message}
                            </MarkdownRenderer>
                          </View>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* What-If Simulator */}
                  <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                      <Sprout size={14} color={colors.primary} />
                      <Text style={styles.sectionTitle}>What-If Simulator</Text>
                    </View>
                    <View style={styles.simGrid}>
                      {SCENARIOS.map((s) => (
                        <TouchableOpacity
                          key={s.key}
                          style={styles.simBtn}
                          onPress={() => runSimulation(s.key)}
                          disabled={simLoading}
                          activeOpacity={0.7}
                        >
                          <Text style={styles.simBtnText}>{s.label}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                    {simLoading && (
                      <View style={styles.simLoading}>
                        <ActivityIndicator size="small" color={colors.primary} />
                      </View>
                    )}
                    {simulation && !simLoading && (
                      <View style={styles.simResult}>
                        <Text style={styles.simScenario}>{simulation.scenario}</Text>
                        <View style={styles.simImpactRow}>
                          <Text style={styles.simImpactLabel}>Yield Impact:</Text>
                          <Text
                            style={[
                              styles.simImpactValue,
                              {
                                color:
                                  simulation.yield_impact_pct < 0
                                    ? colors.red[600]
                                    : colors.green[600],
                              },
                            ]}
                          >
                            {simulation.yield_impact_pct > 0 ? "+" : ""}
                            {simulation.yield_impact_pct}%
                          </Text>
                          <View
                            style={[
                              styles.riskBadge,
                              {
                                backgroundColor:
                                  simulation.risk === "high"
                                    ? colors.red[100]
                                    : simulation.risk === "medium"
                                      ? colors.amber[100]
                                      : colors.green[100],
                              },
                            ]}
                          >
                            <Text
                              style={[
                                styles.riskBadgeText,
                                {
                                  color:
                                    simulation.risk === "high"
                                      ? colors.red[700]
                                      : simulation.risk === "medium"
                                        ? colors.amber[700]
                                        : colors.green[700],
                                },
                              ]}
                            >
                              {simulation.risk} risk
                            </Text>
                          </View>
                        </View>
                        <MarkdownRenderer fontSize={11} color={colors.gray[600]}>
                          {simulation.recommendation}
                        </MarkdownRenderer>
                      </View>
                    )}
                  </View>
                </>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // Toggle button
  toggleBtn: {
    position: "absolute",
    right: 0,
    top: "45%",
    zIndex: 90,
    width: 40,
    height: 80,
    borderTopLeftRadius: 12,
    borderBottomLeftRadius: 12,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    shadowColor: "#000",
    shadowOffset: { width: -2, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 8,
  },
  toggleLabel: {
    fontSize: 8,
    fontWeight: "bold",
    color: colors.white,
    letterSpacing: 1,
  },

  // Overlay
  overlay: {
    flex: 1,
    flexDirection: "row",
  },
  overlayDismiss: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
  },

  // Sidebar
  sidebar: {
    width: SIDEBAR_WIDTH,
    backgroundColor: colors.white,
    shadowColor: "#000",
    shadowOffset: { width: -4, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 10,
    elevation: 20,
  },
  sidebarHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: Platform.OS === "ios" ? 56 : 16,
    paddingBottom: 12,
    backgroundColor: colors.primary,
  },
  headerTextWrap: { flex: 1 },
  headerTitle: { fontSize: 14, fontWeight: "bold", color: colors.white },
  headerSub: { fontSize: 11, color: "rgba(255,255,255,0.8)" },
  headerBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.15)",
    alignItems: "center",
    justifyContent: "center",
  },

  // Content
  content: { flex: 1 },
  contentContainer: { padding: 14, gap: 12, paddingBottom: 40 },
  loadingCenter: { alignItems: "center", justifyContent: "center", height: 160 },

  // Section card
  section: {
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.gray[100],
    backgroundColor: colors.gray[50],
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 12, fontWeight: "bold", color: colors.gray[700], flex: 1 },

  // Farm info
  infoGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  infoLabel: {
    width: "40%",
    fontSize: 11,
    color: colors.gray[500],
    paddingVertical: 3,
  },
  infoValue: {
    width: "60%",
    fontSize: 11,
    fontWeight: "600",
    color: colors.gray[700],
    textAlign: "right",
    paddingVertical: 3,
  },
  capitalize: { textTransform: "capitalize" },

  // Gauges
  gaugeRow: {
    flexDirection: "row",
    justifyContent: "space-around",
  },

  // Weather
  weatherCondition: {
    fontSize: 10,
    color: colors.gray[400],
    textTransform: "capitalize",
  },
  weatherGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  weatherItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    width: "45%",
  },
  weatherValue: { fontSize: 12, color: colors.gray[600] },

  // Forecast
  forecastWrap: { marginTop: 8 },
  forecastToggle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  forecastToggleText: { fontSize: 11, fontWeight: "600", color: colors.primary },
  forecastDay: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[50],
  },
  forecastDate: { fontSize: 10, color: colors.gray[500], width: 60 },
  forecastTemp: { fontSize: 10, fontWeight: "500", color: colors.gray[700] },
  forecastRain: { fontSize: 10, color: colors.blue[500] },

  // Harvest
  harvestRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  harvestDays: { fontSize: 18, fontWeight: "bold", color: colors.primary },
  harvestCrop: { fontSize: 11, color: colors.gray[500] },
  harvestYield: { alignItems: "flex-end" },
  yieldValue: { fontSize: 14, fontWeight: "bold", color: colors.amber[700] },
  yieldLabel: { fontSize: 10, color: colors.gray[400] },
  progressBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gray[200],
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
    backgroundColor: colors.primary,
  },
  progressLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
  },
  progressLabel: { fontSize: 9, color: colors.gray[400] },

  // Alerts
  alertRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 6,
  },
  alertTextWrap: { flex: 1 },

  // Simulator
  simGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  simBtn: {
    width: "48%",
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.primary + "30",
    backgroundColor: colors.primaryLight,
    alignItems: "center",
  },
  simBtnText: { fontSize: 11, fontWeight: "600", color: colors.primary },
  simLoading: { alignItems: "center", paddingVertical: 12 },
  simResult: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
    backgroundColor: colors.white,
    gap: 6,
  },
  simScenario: { fontSize: 12, fontWeight: "600", color: colors.gray[700] },
  simImpactRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  simImpactLabel: { fontSize: 11, color: colors.gray[500] },
  simImpactValue: { fontSize: 12, fontWeight: "bold" },
  riskBadge: {
    marginLeft: "auto",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  riskBadgeText: { fontSize: 9, fontWeight: "600", textTransform: "capitalize" },
});
