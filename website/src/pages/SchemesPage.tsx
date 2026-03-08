import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import { colors } from "../constants/theme";

interface Scheme {
  id: string; name: string; category: string; state: string;
  description: string; benefits: string[]; documents: string[];
  deadline?: string; eligibility_status?: string;
}

const CATEGORIES = [
  { value: "all", label: "All" },
  { value: "subsidy", label: "Subsidy" },
  { value: "insurance", label: "Insurance" },
  { value: "irrigation", label: "Irrigation" },
  { value: "credit", label: "Credit" },
];

const CATEGORY_ICONS: Record<string, string> = { subsidy: "💰", insurance: "🛡️", irrigation: "💧", credit: "💳" };
const CATEGORY_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  subsidy: { bg: colors.amber[100], text: colors.amber[700], label: "CENTRAL GOVT" },
  insurance: { bg: colors.blue[100], text: colors.blue[700], label: "INSURANCE" },
  irrigation: { bg: colors.cyan[100], text: colors.cyan[700], label: "IRRIGATION" },
  credit: { bg: colors.purple[100], text: colors.purple[700], label: "CREDIT" },
};

export default function SchemesPage() {
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");

  useEffect(() => { fetchSchemes(); }, []);

  const fetchSchemes = async () => {
    try {
      const data = await apiClient.get<any[]>(apiClient.farmPath("/schemes"));
      setSchemes(data.map((s) => ({
        id: s.id || s.scheme_id || "", name: s.name || s.scheme_name || "",
        category: s.category || "subsidy", state: s.state || "All India",
        description: s.description || "",
        benefits: s.benefits || (s.benefits_inr ? [`₹${s.benefits_inr.toLocaleString()}`] : []),
        documents: s.documents || s.requirements || [], deadline: s.deadline,
        eligibility_status: s.eligibility_status || (s.eligibility_score >= 0.7 ? "eligible" : undefined),
      })));
    } catch { toast.error("Could not load schemes"); }
  };

  const filtered = schemes.filter((s) => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) || s.description.toLowerCase().includes(search.toLowerCase());
    return matchSearch && (category === "all" || s.category === category);
  });

  const getBenefitPreview = (scheme: Scheme) => {
    if (scheme.name.includes("PM-KISAN")) return "₹6,000";
    if (scheme.name.includes("KCC")) return "₹1.6 Lakh";
    if (scheme.name.includes("PMFBY")) return "2% Premium";
    return "Benefits Available";
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-1" style={{ color: colors.gray[900] }}>Scheme & Credit</h1>
      <p className="text-sm mb-4" style={{ color: colors.gray[500] }}>Browse and apply for agricultural schemes</p>

      <Card className="mb-4">
        <Input placeholder="Search schemes..." value={search} onChange={(e) => setSearch((e.target as HTMLInputElement).value)} />
      </Card>

      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setCategory(cat.value)}
            className={`px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap border cursor-pointer transition-colors`}
            style={category === cat.value
              ? { backgroundColor: colors.primary, borderColor: colors.primary, color: colors.white }
              : { backgroundColor: colors.white, borderColor: colors.gray[300], color: colors.gray[600] }
            }
          >
            {cat.label}
          </button>
        ))}
      </div>

      <h2 className="text-base font-bold mb-3" style={{ color: colors.gray[800] }}>Eligible Schemes</h2>

      {filtered.length === 0 ? (
        <Card><p className="text-center py-10" style={{ color: colors.gray[500] }}>No schemes found matching your filters.</p></Card>
      ) : (
        filtered.map((scheme) => {
          const badge = CATEGORY_BADGE[scheme.category] || CATEGORY_BADGE.subsidy;
          return (
            <Card key={scheme.id} className="mb-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg shrink-0" style={{ backgroundColor: colors.primaryLight }}>
                  {CATEGORY_ICONS[scheme.category] || "💰"}
                </div>
                <div className="flex-1 min-w-0 mr-2">
                  <p className="text-sm font-semibold line-clamp-2" style={{ color: colors.gray[800] }}>{scheme.name}</p>
                  <p className="text-xs line-clamp-2 mt-0.5" style={{ color: colors.gray[500] }}>{scheme.description}</p>
                </div>
                <Badge label={badge.label} bgColor={badge.bg} textColor={badge.text} />
              </div>
              <div className="rounded-lg p-3 mt-3" style={{ backgroundColor: colors.gray[50] }}>
                <p className="text-[10px] font-semibold mb-1" style={{ color: colors.gray[500] }}>
                  {scheme.category === "subsidy" ? "ANNUAL BENEFIT" : "CREDIT LIMIT"}
                </p>
                <p className="text-lg font-bold" style={{ color: colors.primary }}>{getBenefitPreview(scheme)}</p>
              </div>
              {scheme.eligibility_status === "eligible" && (
                <div className="flex items-center gap-1 mt-2.5">
                  <CheckCircle size={14} color={colors.green[700]} />
                  <span className="text-xs" style={{ color: colors.green[700] }}>You are eligible</span>
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <Button title="View Details" variant="outline" size="sm" onPress={() => navigate(`/schemes/${scheme.id}`)} className="flex-1" />
                <Button title="Apply Now" size="sm" onPress={() => navigate(`/apply/${scheme.id}`)} className="flex-1" />
              </div>
            </Card>
          );
        })
      )}
    </div>
  );
}
