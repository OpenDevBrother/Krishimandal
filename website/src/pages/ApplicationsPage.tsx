import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Calendar, CheckCircle, XCircle, Clock, FileEdit } from "lucide-react";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Application { id: string; scheme_id?: string; scheme_name?: string; status: string; submitted_date?: string; created_at?: string; }

const FILTERS = ["all", "draft", "submitted", "under_review", "approved"];

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => { fetchApplications(); }, []);

  const fetchApplications = async () => {
    try {
      const data = await apiClient.get<Application[]>(apiClient.farmPath("/applications"));
      setApplications(data);
    } catch { /* ignore */ }
  };

  const filtered = filter === "all" ? applications : applications.filter((a) => a.status === filter);
  const counts: Record<string, number> = {
    all: applications.length,
    draft: applications.filter((a) => a.status === "draft").length,
    submitted: applications.filter((a) => a.status === "submitted").length,
    under_review: applications.filter((a) => a.status === "under_review").length,
    approved: applications.filter((a) => a.status === "approved").length,
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "approved": return <CheckCircle size={20} color={colors.green[600]} />;
      case "rejected": return <XCircle size={20} color={colors.red[600]} />;
      case "under_review": return <Clock size={20} color={colors.blue[600]} />;
      case "submitted": return <FileText size={20} color={colors.purple[600]} />;
      default: return <FileEdit size={20} color={colors.gray[500]} />;
    }
  };

  const statusBadgeColors: Record<string, { bg: string; text: string }> = {
    approved: { bg: colors.green[100], text: colors.green[700] },
    rejected: { bg: colors.red[100], text: colors.red[700] },
    under_review: { bg: colors.blue[100], text: colors.blue[700] },
    submitted: { bg: colors.purple[100], text: colors.purple[700] },
    draft: { bg: colors.gray[100], text: colors.gray[700] },
    pending: { bg: colors.amber[100], text: colors.amber[700] },
  };

  const getStatusMessage = (status: string) => {
    switch (status) {
      case "approved": return "Your application has been approved! Benefits will be disbursed soon.";
      case "rejected": return "Your application was rejected. Please review the eligibility criteria.";
      case "under_review": return "Your application is under review. You will be notified once a decision is made.";
      case "submitted": return "Your application has been submitted successfully.";
      default: return "This application is saved as a draft. Complete and submit it.";
    }
  };

  const getStatusMsgBg = (status: string) => {
    switch (status) {
      case "approved": return { bg: colors.green[50], text: colors.green[700] };
      case "rejected": return { bg: colors.red[50], text: colors.red[700] };
      case "under_review": return { bg: colors.blue[50], text: colors.blue[700] };
      case "submitted": return { bg: colors.purple[50], text: colors.purple[700] };
      default: return { bg: colors.gray[100], text: colors.gray[700] };
    }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-1" style={{ color: colors.gray[900] }}>My Applications</h1>
      <p className="text-sm mb-4" style={{ color: colors.gray[500] }}>Track your scheme application status</p>

      <div className="flex gap-2 overflow-x-auto pb-1 mb-4">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-3.5 py-2 rounded-full text-xs font-semibold whitespace-nowrap border cursor-pointer"
            style={filter === f ? { backgroundColor: colors.primary, borderColor: colors.primary, color: colors.white } : { backgroundColor: colors.white, borderColor: colors.gray[300], color: colors.gray[600] }}
          >
            {f.replace("_", " ").charAt(0).toUpperCase() + f.replace("_", " ").slice(1)} ({counts[f] || 0})
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-10">
            <FileText size={48} color={colors.gray[300]} />
            <p className="text-base font-semibold mt-3" style={{ color: colors.gray[700] }}>No Applications Found</p>
            <p className="text-sm mt-1" style={{ color: colors.gray[500] }}>You haven't applied for any schemes yet.</p>
            <Button title="Browse Schemes" onPress={() => navigate("/schemes")} className="mt-3" />
          </div>
        </Card>
      ) : (
        filtered.map((app) => {
          const badgeC = statusBadgeColors[app.status] || statusBadgeColors.draft;
          const msgStyle = getStatusMsgBg(app.status);
          return (
            <Card key={app.id} className="mb-3">
              <div className="flex items-start gap-2.5">
                <div className="mt-0.5">{getStatusIcon(app.status)}</div>
                <div className="flex-1 min-w-0 mr-2">
                  <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{app.scheme_name || `Application ${app.id}`}</p>
                  {(app.submitted_date || app.created_at) && (
                    <div className="flex items-center gap-1 mt-1">
                      <Calendar size={12} color={colors.gray[400]} />
                      <span className="text-xs" style={{ color: colors.gray[500] }}>{new Date(app.submitted_date || app.created_at!).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>
                <Badge label={app.status.replace("_", " ").toUpperCase()} bgColor={badgeC.bg} textColor={badgeC.text} />
              </div>
              <div className="rounded-lg p-3 mt-3" style={{ backgroundColor: msgStyle.bg }}>
                <p className="text-xs" style={{ color: msgStyle.text }}>{getStatusMessage(app.status)}</p>
              </div>
              <div className="flex gap-2 mt-3">
                {app.status === "draft" && app.scheme_id && (
                  <Button title="Continue Application" size="sm" onPress={() => navigate(`/apply/${app.scheme_id}`)} className="flex-1" />
                )}
                <Button title="Download PDF" variant="outline" size="sm" onPress={() => {}} className="flex-1" />
              </div>
            </Card>
          );
        })
      )}
    </div>
  );
}
