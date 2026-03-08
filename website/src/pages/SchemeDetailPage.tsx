import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MapPin, Calendar, CheckCircle, FileText, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Scheme {
  id: string; name: string; category: string; state: string;
  description: string; benefits: string[]; documents: string[];
  deadline?: string; eligibility_status?: string; eligibility_missing?: string[];
}

export default function SchemeDetailPage() {
  const { schemeId } = useParams();
  const navigate = useNavigate();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchScheme(); }, [schemeId]);

  const fetchScheme = async () => {
    try {
      const data = await apiClient.get<any[]>(apiClient.farmPath("/schemes"));
      const raw = data.find((s) => (s.id || s.scheme_id) === schemeId);
      if (raw) {
        setScheme({
          id: raw.id || raw.scheme_id || "", name: raw.name || raw.scheme_name || "",
          category: raw.category || "subsidy", state: raw.state || "All India",
          description: raw.description || "",
          benefits: raw.benefits || (raw.benefits_inr ? [`₹${raw.benefits_inr.toLocaleString()}`] : []),
          documents: raw.documents || raw.requirements || [], deadline: raw.deadline,
          eligibility_status: raw.eligibility_status || (raw.eligibility_score >= 0.7 ? "eligible" : raw.eligibility_score >= 0.4 ? "partially_eligible" : "not_eligible"),
          eligibility_missing: raw.eligibility_missing || raw.missing_criteria || [],
        });
      }
    } catch { toast.error("Could not load scheme details"); }
    finally { setLoading(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-t-transparent rounded-full animate-spin" style={{ borderColor: colors.primary, borderTopColor: "transparent" }} /></div>;
  if (!scheme) return <div className="flex items-center justify-center h-64"><p style={{ color: colors.gray[500] }}>Scheme not found</p></div>;

  const catBadge: Record<string, { bg: string; text: string }> = {
    subsidy: { bg: colors.green[100], text: colors.green[700] },
    insurance: { bg: colors.blue[100], text: colors.blue[700] },
    irrigation: { bg: colors.cyan[100], text: colors.cyan[700] },
    credit: { bg: colors.purple[100], text: colors.purple[700] },
  };
  const badge = catBadge[scheme.category] || catBadge.subsidy;
  const eligible = scheme.eligibility_status === "eligible";

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <button onClick={() => navigate(-1)} className="text-sm font-semibold mb-4 border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>← Back</button>
      <Card>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <h1 className="text-lg font-bold mb-2" style={{ color: colors.gray[900] }}>{scheme.name}</h1>
            <p className="text-sm leading-relaxed" style={{ color: colors.gray[500] }}>{scheme.description}</p>
          </div>
          <Badge label={scheme.category} bgColor={badge.bg} textColor={badge.text} />
        </div>

        <div className="flex flex-wrap gap-4 mt-4">
          <div className="flex items-center gap-1.5"><MapPin size={16} color={colors.gray[400]} /><span className="text-sm" style={{ color: colors.gray[600] }}>{scheme.state}</span></div>
          {scheme.deadline && <div className="flex items-center gap-1.5"><Calendar size={16} color={colors.gray[400]} /><span className="text-sm" style={{ color: colors.gray[600] }}>Deadline: {new Date(scheme.deadline).toLocaleDateString()}</span></div>}
        </div>

        <hr className="my-4" style={{ borderColor: colors.gray[200] }} />

        <h3 className="text-sm font-bold mb-3" style={{ color: colors.gray[800] }}>Benefits</h3>
        {scheme.benefits.map((b, i) => (
          <div key={i} className="flex items-start gap-2 mb-2">
            <CheckCircle size={16} color={colors.green[600]} className="mt-0.5 shrink-0" />
            <span className="text-sm" style={{ color: colors.gray[700] }}>{b}</span>
          </div>
        ))}

        <hr className="my-4" style={{ borderColor: colors.gray[200] }} />

        <h3 className="text-sm font-bold mb-3" style={{ color: colors.gray[800] }}>Required Documents</h3>
        {scheme.documents.map((d, i) => (
          <div key={i} className="flex items-start gap-2 mb-2">
            <FileText size={16} color={colors.blue[600]} className="mt-0.5 shrink-0" />
            <span className="text-sm" style={{ color: colors.gray[700] }}>{d}</span>
          </div>
        ))}

        <hr className="my-4" style={{ borderColor: colors.gray[200] }} />

        {/* Eligibility */}
        <div className="rounded-lg p-4 mt-4 border" style={{
          backgroundColor: eligible ? colors.green[50] : colors.red[50],
          borderColor: eligible ? colors.green[100] : colors.red[100],
        }}>
          <div className="flex items-center gap-2">
            {eligible ? <CheckCircle size={20} color={colors.green[600]} /> : <XCircle size={20} color={colors.red[600]} />}
            <span className="text-sm font-semibold" style={{ color: colors.gray[800] }}>
              {eligible ? "You are eligible for this scheme" : "Not Eligible"}
            </span>
          </div>
          {(scheme.eligibility_missing || []).length > 0 && (
            <div className="mt-2">
              <p className="text-sm font-semibold" style={{ color: colors.gray[700] }}>Missing criteria:</p>
              {scheme.eligibility_missing!.map((m, i) => (
                <p key={i} className="text-xs ml-2 mt-0.5" style={{ color: colors.gray[600] }}>• {m}</p>
              ))}
            </div>
          )}
        </div>

        <Button title="Apply for This Scheme" size="lg" fullWidth onPress={() => navigate(`/apply/${scheme.id}`)} className="mt-5" />
      </Card>
    </div>
  );
}
