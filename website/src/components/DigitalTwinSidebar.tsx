import { useEffect, useState } from "react";
import {
  Layers, X, RefreshCw, Sprout, Droplets, Thermometer, Wind,
  Activity, AlertTriangle, Calendar, Loader2, CloudRain, Sun,
  Cloud, CloudSnow, Leaf, ChevronDown, ChevronUp,
} from "lucide-react";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import Markdown from "./Markdown";

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

const SCENARIOS = [
  { key: "drought", label: "Drought" },
  { key: "pest_outbreak", label: "Pest Outbreak" },
  { key: "early_harvest", label: "Early Harvest" },
  { key: "alternative_crop", label: "Alt. Crop" },
];

function WeatherIcon({ condition, size = 16 }: { condition: string; size?: number }) {
  const c = condition.toLowerCase();
  if (c.includes("rain") || c.includes("drizzle")) return <CloudRain size={size} />;
  if (c.includes("cloud")) return <Cloud size={size} />;
  if (c.includes("snow")) return <CloudSnow size={size} />;
  return <Sun size={size} />;
}

function GaugeRing({ value, max, color, label, unit }: { value: number; max: number; color: string; label: string; unit: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-16 h-16">
        <svg width="64" height="64" viewBox="0 0 36 36">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="#e5e7eb" strokeWidth={3}
          />
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke={color} strokeWidth={3}
            strokeDasharray={`${pct}, 100`} strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold" style={{ color }}>
          {typeof value === "number" ? (value % 1 === 0 ? value : value.toFixed(1)) : value}
        </span>
      </div>
      <span className="text-[10px] font-semibold mt-1 text-gray-500">{label}</span>
      <span className="text-[9px] text-gray-400">{unit}</span>
    </div>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const colorMap: Record<string, string> = {
    low: colors.green[600],
    medium: colors.amber[500],
    high: colors.red[500],
    critical: colors.red[700],
  };
  return (
    <span
      className="inline-block w-2 h-2 rounded-full mr-1.5 shrink-0 mt-1"
      style={{ backgroundColor: colorMap[severity] || colors.gray[400] }}
    />
  );
}

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
      const farmerId = localStorage.getItem("farmer_id") || "F1001";
      const [profileRes, stateRes] = await Promise.allSettled([
        apiClient.get<FarmProfile>(`/farm/${farmerId}`),
        apiClient.get<FarmState>(apiClient.farmPath("/state")),
      ]);

      if (profileRes.status === "fulfilled") setProfile(profileRes.value);
      if (stateRes.status === "fulfilled") setState(stateRes.value);

      // Fetch harvest prediction and health via the query endpoint
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
        // Parse harvest data from response if possible
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
            yield_estimate_quintals_per_hectare: yieldMatch ? parseFloat(yieldMatch[1]) : 18,
          });
        }
      } catch {
        // non-critical
      }

      // Fetch risk alerts
      try {
        const alertRes = await apiClient.post<{
          final_response: string;
        }>("/query", {
          query: "farm risk alerts",
          farmer_id: farmerId,
          language: "en",
        });
        const parts = alertRes.final_response.split("|").map((s) => s.trim()).filter(Boolean);
        setAlerts(
          parts.map((msg) => ({
            type: "alert",
            severity: msg.toLowerCase().includes("critical") || msg.toLowerCase().includes("low at")
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
    try {
      const res = await apiClient.post<SimulationResult>(
        apiClient.farmPath("/simulate"),
        { scenario }
      );
      setSimulation(res);
    } catch {
      setSimulation({
        scenario: "Error",
        yield_impact_pct: 0,
        recommendation: "Could not run simulation. Try again later.",
        risk: "unknown",
      });
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <>
      {/* Toggle button on right edge */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed top-1/2 -translate-y-1/2 right-0 z-[90] w-10 h-24 rounded-l-xl shadow-lg flex flex-col items-center justify-center gap-1 border-none cursor-pointer transition-all hover:w-12"
          style={{ backgroundColor: colors.primary, color: "#fff" }}
          title="Digital Twin"
        >
          <Layers size={18} />
          <span className="text-[9px] font-bold tracking-wide" style={{ writingMode: "vertical-rl", textOrientation: "mixed" }}>
            TWIN
          </span>
        </button>
      )}

      {/* Sidebar panel */}
      {isOpen && (
        <div className="fixed top-0 right-0 z-[90] w-80 h-full bg-white shadow-2xl border-l border-gray-200 flex flex-col overflow-hidden">
          {/* Header */}
          <div
            className="flex items-center gap-2.5 px-4 py-3 shrink-0"
            style={{ backgroundColor: colors.primary, color: "#fff" }}
          >
            <Layers size={20} />
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold m-0">Digital Twin</h3>
              <p className="text-[11px] opacity-80 m-0">
                {profile ? `${profile.farmer_name}'s Farm` : "Farm Overview"}
              </p>
            </div>
            <button
              onClick={() => fetchAll()}
              disabled={loading}
              className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center border-none cursor-pointer hover:bg-white/25 transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center border-none cursor-pointer hover:bg-white/25 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {loading && !state ? (
              <div className="flex items-center justify-center h-40">
                <Loader2 size={24} className="animate-spin" style={{ color: colors.primary }} />
              </div>
            ) : (
              <div className="p-4 space-y-4">

                {/* Farm Info Card */}
                {profile && (
                  <div className="rounded-xl p-3 border border-gray-100 bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <Leaf size={14} style={{ color: colors.primary }} />
                      <span className="text-xs font-bold text-gray-700">Farm Info</span>
                    </div>
                    <div className="grid grid-cols-2 gap-y-1.5 text-xs">
                      <span className="text-gray-500">Area</span>
                      <span className="font-semibold text-gray-700 text-right">{profile.area_hectares} ha</span>
                      <span className="text-gray-500">Soil</span>
                      <span className="font-semibold text-gray-700 text-right capitalize">{profile.soil_type}</span>
                      <span className="text-gray-500">Irrigation</span>
                      <span className="font-semibold text-gray-700 text-right capitalize">{profile.irrigation_type}</span>
                      {profile.current_crops?.[0] && (
                        <>
                          <span className="text-gray-500">Crop</span>
                          <span className="font-semibold text-gray-700 text-right">
                            {profile.current_crops[0].crop_type}
                            {profile.current_crops[0].variety ? ` (${profile.current_crops[0].variety})` : ""}
                          </span>
                          <span className="text-gray-500">Stage</span>
                          <span className="font-semibold text-right capitalize" style={{ color: colors.primary }}>
                            {profile.current_crops[0].growth_stage}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Gauges */}
                {state && (
                  <div className="rounded-xl p-3 border border-gray-100">
                    <div className="flex items-center gap-2 mb-3">
                      <Activity size={14} style={{ color: colors.primary }} />
                      <span className="text-xs font-bold text-gray-700">Farm Health Metrics</span>
                    </div>
                    <div className="flex justify-around">
                      <GaugeRing
                        value={state.health_score}
                        max={100}
                        color={state.health_score >= 70 ? colors.green[600] : state.health_score >= 40 ? colors.amber[500] : colors.red[500]}
                        label="Health"
                        unit="/100"
                      />
                      <GaugeRing
                        value={state.ndvi_mean}
                        max={1}
                        color={state.ndvi_mean >= 0.5 ? colors.green[600] : colors.amber[500]}
                        label="NDVI"
                        unit="index"
                      />
                      <GaugeRing
                        value={state.soil_moisture_pct}
                        max={100}
                        color={state.soil_moisture_pct >= 30 ? colors.blue[600] : colors.red[500]}
                        label="Moisture"
                        unit="%"
                      />
                    </div>
                  </div>
                )}

                {/* Weather */}
                {state?.weather && (
                  <div className="rounded-xl p-3 border border-gray-100">
                    <div className="flex items-center gap-2 mb-2">
                      <WeatherIcon condition={state.weather.condition} size={14} />
                      <span className="text-xs font-bold text-gray-700">Weather</span>
                      <span className="text-[10px] capitalize text-gray-400 ml-auto">{state.weather.condition}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex items-center gap-1.5 text-xs">
                        <Thermometer size={13} style={{ color: colors.red[500] }} />
                        <span className="text-gray-600">{Math.round(state.weather.temperature_c)}°C</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <Droplets size={13} style={{ color: colors.blue[500] }} />
                        <span className="text-gray-600">{state.weather.humidity_pct}%</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <CloudRain size={13} style={{ color: colors.blue[700] }} />
                        <span className="text-gray-600">{state.weather.rainfall_mm} mm</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <Wind size={13} style={{ color: colors.gray[500] }} />
                        <span className="text-gray-600">{Math.round(state.weather.wind_speed_kmh)} km/h</span>
                      </div>
                    </div>

                    {/* 7-day forecast toggle */}
                    {state.weather.forecast_7day && state.weather.forecast_7day.length > 0 && (
                      <div className="mt-2">
                        <button
                          onClick={() => setForecastOpen(!forecastOpen)}
                          className="flex items-center gap-1 text-[11px] font-semibold border-none bg-transparent cursor-pointer px-0"
                          style={{ color: colors.primary }}
                        >
                          {forecastOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          7-Day Forecast
                        </button>
                        {forecastOpen && (
                          <div className="mt-1.5 space-y-1">
                            {state.weather.forecast_7day.map((day, i) => (
                              <div key={i} className="flex items-center justify-between text-[11px] py-1 border-b border-gray-50 last:border-0">
                                <span className="text-gray-500 w-16">{new Date(day.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric" })}</span>
                                <WeatherIcon condition={day.condition} size={12} />
                                <span className="text-gray-700 font-medium">{Math.round(day.temp_min)}–{Math.round(day.temp_max)}°C</span>
                                <span className="text-blue-500">{day.rainfall_mm > 0 ? `${day.rainfall_mm}mm` : "—"}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Harvest Prediction */}
                {harvest && (
                  <div className="rounded-xl p-3 border border-gray-100">
                    <div className="flex items-center gap-2 mb-2">
                      <Calendar size={14} style={{ color: colors.primary }} />
                      <span className="text-xs font-bold text-gray-700">Harvest Prediction</span>
                    </div>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="text-lg font-bold m-0" style={{ color: colors.primary }}>
                          {harvest.days_to_harvest} days
                        </p>
                        <p className="text-[11px] text-gray-500 m-0">
                          {harvest.crop} — {harvest.growth_stage}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold m-0" style={{ color: colors.amber[700] }}>
                          {harvest.yield_estimate_quintals_per_hectare} qt/ha
                        </p>
                        <p className="text-[10px] text-gray-400 m-0">
                          est. yield ({Math.round(harvest.confidence * 100)}%)
                        </p>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: colors.gray[200] }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.max(5, Math.min(95, 100 - (harvest.days_to_harvest / 120) * 100))}%`,
                          backgroundColor: colors.primary,
                        }}
                      />
                    </div>
                    <div className="flex justify-between mt-1 text-[9px] text-gray-400">
                      <span>Sowing</span>
                      <span>Growth</span>
                      <span>Harvest</span>
                    </div>
                  </div>
                )}

                {/* Risk Alerts */}
                {alerts.length > 0 && (
                  <div className="rounded-xl p-3 border border-gray-100">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle size={14} style={{ color: colors.amber[500] }} />
                      <span className="text-xs font-bold text-gray-700">Risk Alerts</span>
                    </div>
                    <div className="space-y-1.5">
                      {alerts.map((alert, i) => (
                        <div key={i} className="flex items-start text-xs">
                          <SeverityDot severity={alert.severity} />
                          <span className="text-gray-600 leading-snug">{alert.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scenario Simulator */}
                <div className="rounded-xl p-3 border border-gray-100">
                  <div className="flex items-center gap-2 mb-2">
                    <Sprout size={14} style={{ color: colors.primary }} />
                    <span className="text-xs font-bold text-gray-700">What-If Simulator</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {SCENARIOS.map((s) => (
                      <button
                        key={s.key}
                        onClick={() => runSimulation(s.key)}
                        disabled={simLoading}
                        className="text-[11px] font-semibold py-1.5 px-2 rounded-lg border cursor-pointer transition-colors disabled:opacity-50"
                        style={{
                          backgroundColor: colors.primaryLight,
                          borderColor: colors.primary + "30",
                          color: colors.primary,
                        }}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                  {simLoading && (
                    <div className="flex items-center justify-center py-3">
                      <Loader2 size={16} className="animate-spin" style={{ color: colors.primary }} />
                    </div>
                  )}
                  {simulation && !simLoading && (
                    <div className="mt-2.5 p-2.5 rounded-lg bg-gray-50 text-xs space-y-1.5">
                      <p className="font-semibold text-gray-700 m-0">{simulation.scenario}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">Yield Impact:</span>
                        <span
                          className="font-bold"
                          style={{
                            color: simulation.yield_impact_pct < 0 ? colors.red[600] : colors.green[600],
                          }}
                        >
                          {simulation.yield_impact_pct > 0 ? "+" : ""}
                          {simulation.yield_impact_pct}%
                        </span>
                        <span
                          className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-medium capitalize"
                          style={{
                            backgroundColor:
                              simulation.risk === "high" ? colors.red[100] :
                              simulation.risk === "medium" ? colors.amber[100] :
                              colors.green[100],
                            color:
                              simulation.risk === "high" ? colors.red[700] :
                              simulation.risk === "medium" ? colors.amber[700] :
                              colors.green[700],
                          }}
                        >
                          {simulation.risk} risk
                        </span>
                      </div>
                      <div className="text-gray-600 m-0 leading-snug text-sm">
                        <Markdown>{simulation.recommendation}</Markdown>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
