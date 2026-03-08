import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sun, Droplets, Sprout, CheckCircle, FileText, TrendingUp, AlertCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "../services/authContext";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface AppItem { id: string; scheme_name?: string; status: string; submitted_date?: string; created_at?: string; }
interface InvItem { id: string; name: string; quantity: number; unit: string; threshold?: number; alert_threshold?: number; }
interface SchemeItem { id: string; name: string; deadline?: string; }

export default function DashboardPage() {
  const { farmer } = useAuth();
  const navigate = useNavigate();
  const [applications, setApplications] = useState<AppItem[]>([]);
  const [lowStock, setLowStock] = useState<InvItem[]>([]);
  const [schemes, setSchemes] = useState<SchemeItem[]>([]);
  const [weatherTemp, setWeatherTemp] = useState("--");
  const [weatherRain, setWeatherRain] = useState("--");

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [appsData, invData, schemesData, stateData] = await Promise.allSettled([
        apiClient.get<AppItem[]>(apiClient.farmPath("/applications")),
        apiClient.get<InvItem[]>(apiClient.farmPath("/inventory/alerts")),
        apiClient.get<any[]>(apiClient.farmPath("/schemes")),
        apiClient.get<any>(apiClient.farmPath("/state")),
      ]);

      if (stateData.status === "fulfilled") {
        const w = stateData.value?.weather;
        if (w) {
          setWeatherTemp(`${Math.round(w.temperature_c)}°C`);
          setWeatherRain(`Rain: ${Math.round(w.humidity_pct)}%`);
        }
      }
      if (appsData.status === "fulfilled") setApplications(appsData.value.slice(0, 2));
      if (invData.status === "fulfilled") setLowStock(invData.value.slice(0, 2));
      if (schemesData.status === "fulfilled") {
        setSchemes(schemesData.value.map((s: any) => ({
          id: s.id || s.scheme_id, name: s.name || s.scheme_name, deadline: s.deadline,
        })).slice(0, 3));
      }
    } catch {
      toast.error("Could not connect to server");
    }
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
    <div className="p-4 max-w-4xl mx-auto">
      {/* Welcome */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold" style={{ color: colors.gray[900] }}>
          Namaste, {farmer?.name || "Farmer"}!
        </h1>
        <p className="text-sm" style={{ color: colors.gray[500] }}>Let's check your farm today</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <Card>
          <div className="flex flex-col items-center">
            <div className="relative w-20 h-20 mb-2">
              <svg width="80" height="80" viewBox="0 0 36 36">
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={colors.primaryLight} strokeWidth={3} />
                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke={colors.primary} strokeWidth={3} strokeDasharray="85, 100" strokeLinecap="round" />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold" style={{ color: colors.primary }}>85</span>
            </div>
            <span className="text-sm" style={{ color: colors.gray[500] }}>Farm Health</span>
          </div>
        </Card>
        <Card>
          <div className="flex flex-col items-center">
            <div className="flex items-center gap-2 mb-2">
              <Sun size={36} color={colors.yellow[500]} />
              <span className="text-2xl font-bold" style={{ color: colors.gray[800] }}>{weatherTemp}</span>
            </div>
            <div className="flex items-center gap-1">
              <Droplets size={14} color={colors.blue[500]} />
              <span className="text-xs" style={{ color: colors.gray[500] }}>{weatherRain}</span>
            </div>
            <span className="text-xs mt-1" style={{ color: colors.gray[500] }}>{farmer?.village || farmer?.district || "Your Farm"}</span>
          </div>
        </Card>
      </div>

      {/* Scheme Deadlines */}
      {schemes.length > 0 && (
        <div className="mb-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Scheme Deadlines</h2>
            <button onClick={() => navigate("/schemes")} className="text-sm font-semibold border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>View All</button>
          </div>
          {schemes.map((scheme) => (
            <Card key={scheme.id} borderLeftColor={colors.amber[500]} className="mb-3">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: colors.gray[800] }}>{scheme.name}</p>
                  {scheme.deadline && <p className="text-xs" style={{ color: colors.gray[500] }}>Deadline: {new Date(scheme.deadline).toLocaleDateString()}</p>}
                </div>
                <Button title="Apply" variant="outline" size="sm" onPress={() => navigate(`/schemes/${scheme.id}`)} />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Crop Price */}
      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.amber[100] }}>
              <Sprout size={18} color={colors.amber[700]} />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>Wheat (Gehu)</p>
              <p className="text-xs" style={{ color: colors.gray[500] }}>Indore Mandi</p>
            </div>
          </div>
          <Badge label="+2.4%" bgColor={colors.green[100]} textColor={colors.green[700]} />
        </div>
        <p className="text-xs mt-3" style={{ color: colors.gray[500] }}>Today's Price</p>
        <p className="text-2xl font-bold mt-1" style={{ color: colors.primary }}>
          ₹2,125 <span className="text-sm font-normal" style={{ color: colors.gray[500] }}>/qt</span>
        </p>
        <div className="h-1.5 rounded-full mt-3 overflow-hidden" style={{ backgroundColor: colors.gray[200] }}>
          <div className="h-full rounded-full" style={{ width: "75%", backgroundColor: colors.green[600] }} />
        </div>
      </Card>

      {/* Harvest Progress */}
      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold" style={{ color: colors.gray[800] }}>Harvest in</h3>
          <span className="text-lg font-bold" style={{ color: colors.gray[800] }}>15 Days</span>
        </div>
        <div className="h-1.5 rounded-full mt-3 overflow-hidden" style={{ backgroundColor: colors.gray[200] }}>
          <div className="h-full rounded-full" style={{ width: "70%", backgroundColor: colors.primary }} />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs" style={{ color: colors.gray[500] }}>Sowing</span>
          <span className="text-xs" style={{ color: colors.gray[500] }}>Growth</span>
          <span className="text-xs" style={{ color: colors.gray[500] }}>Maturity</span>
        </div>
      </Card>

      {/* PM-KISAN Alert */}
      <Card className="mb-4" style={{ backgroundColor: colors.primary }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <CheckCircle size={22} color={colors.white} />
            </div>
            <div>
              <p className="text-sm font-bold text-white">PM-KISAN</p>
              <p className="text-sm text-white/90">Eligibility Confirmed</p>
            </div>
          </div>
          <Button title="Check Now" variant="outline" size="sm" onPress={() => navigate("/schemes/PMKISAN")} style={{ backgroundColor: colors.white, borderColor: colors.white, color: colors.primary }} />
        </div>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <button onClick={() => navigate("/schemes")} className="border-none bg-transparent cursor-pointer p-0">
          <Card className="flex flex-col items-center py-5 hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mb-3" style={{ backgroundColor: colors.green[100] }}>
              <FileText size={24} color={colors.primary} />
            </div>
            <span className="text-sm font-semibold" style={{ color: colors.gray[700] }}>Browse Schemes</span>
          </Card>
        </button>
        <button onClick={() => navigate("/inventory")} className="border-none bg-transparent cursor-pointer p-0">
          <Card className="flex flex-col items-center py-5 hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mb-3" style={{ backgroundColor: colors.blue[100] }}>
              <TrendingUp size={24} color={colors.blue[600]} />
            </div>
            <span className="text-sm font-semibold" style={{ color: colors.gray[700] }}>Manage Inventory</span>
          </Card>
        </button>
      </div>

      {/* Recent Applications */}
      {applications.length > 0 && (
        <div className="mb-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Recent Applications</h2>
            <button onClick={() => navigate("/applications")} className="text-sm font-semibold border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>View All</button>
          </div>
          {applications.map((app) => (
            <Card key={app.id} className="mb-3">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{app.scheme_name || `Application ${app.id}`}</p>
                  <p className="text-xs" style={{ color: colors.gray[500] }}>
                    {app.submitted_date || app.created_at ? new Date(app.submitted_date || app.created_at!).toLocaleDateString() : "Draft"}
                  </p>
                </div>
                {getStatusBadge(app.status)}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Low Stock Alerts */}
      {lowStock.length > 0 && (
        <div className="mb-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle size={20} color={colors.red[600]} />
            <h2 className="text-base font-bold" style={{ color: colors.gray[800] }}>Low Stock Alerts</h2>
          </div>
          {lowStock.map((item) => (
            <Card key={item.id} borderLeftColor={colors.red[500]} className="mb-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{item.name}</p>
                  <p className="text-xs" style={{ color: colors.red[600] }}>{item.quantity} {item.unit} remaining</p>
                </div>
                <Button title="Manage" variant="outline" size="sm" onPress={() => navigate("/inventory")} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
