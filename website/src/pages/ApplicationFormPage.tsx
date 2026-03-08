import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { CheckSquare, Square, FileCheck, Upload } from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import { useAuth } from "../services/authContext";
import Card from "../components/Card";
import Input from "../components/Input";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Scheme { id: string; name: string; documents: string[]; }

export default function ApplicationFormPage() {
  const { schemeId } = useParams();
  const navigate = useNavigate();
  const { farmer } = useAuth();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [form, setForm] = useState({
    name: farmer?.name || "", phone: farmer?.phone_number || "",
    aadhaar: "", landSize: farmer?.land_size?.toString() || "",
    bankDetails: "", address: farmer?.village ? `${farmer.village}, ${farmer.state || ""}` : "",
    additionalInfo: "",
  });
  const [documents, setDocuments] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchScheme(); }, [schemeId]);

  const fetchScheme = async () => {
    try {
      const data = await apiClient.get<any[]>(apiClient.farmPath("/schemes"));
      const found = data.find((s: any) => (s.id || s.scheme_id) === schemeId);
      if (found) {
        const mapped = { id: found.id || found.scheme_id || "", name: found.name || found.scheme_name || "", documents: found.documents || found.requirements || [] };
        setScheme(mapped);
        const docs: Record<string, boolean> = {};
        mapped.documents.forEach((d: string) => (docs[d] = false));
        setDocuments(docs);
      }
    } catch { toast.error("Could not load scheme"); }
  };

  const uploadedCount = Object.values(documents).filter(Boolean).length;
  const totalDocs = Object.keys(documents).length;
  const progress = totalDocs > 0 ? (uploadedCount / totalDocs) * 100 : 0;

  const handleSubmit = async (isDraft: boolean) => {
    if (!isDraft && uploadedCount < totalDocs) {
      toast.error("Please upload all required documents");
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post(apiClient.farmPath("/applications"), {
        scheme_id: schemeId, scheme_name: scheme?.name || "",
        status: isDraft ? "draft" : "submitted",
        personal_info: {
          name: form.name, phone: form.phone, aadhaar: form.aadhaar,
          land_size: parseFloat(form.landSize) || 0, bank_details: form.bankDetails,
          address: form.address, additional_info: form.additionalInfo,
        },
        documents: Object.entries(documents).map(([name, uploaded]) => ({ name, uploaded })),
      });
      toast.success(isDraft ? "Application saved as draft" : "Application submitted successfully!");
      setTimeout(() => navigate("/applications"), 500);
    } catch (err: any) { toast.error(err.message || "Failed to submit"); }
    finally { setSubmitting(false); }
  };

  if (!scheme) return <div className="flex items-center justify-center h-64"><p style={{ color: colors.gray[500] }}>Loading...</p></div>;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <button onClick={() => navigate(-1)} className="text-sm font-semibold mb-4 border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>← Back</button>
      <Card>
        <h1 className="text-lg font-bold mb-1" style={{ color: colors.gray[900] }}>Application Form</h1>
        <p className="text-sm mb-5" style={{ color: colors.gray[500] }}>{scheme.name}</p>

        <h3 className="text-sm font-bold mt-5 mb-3" style={{ color: colors.gray[800] }}>Personal Details</h3>
        <Input label="Full Name *" value={form.name} onChange={(e) => setForm({ ...form, name: (e.target as HTMLInputElement).value })} />
        <Input label="Phone Number *" value={form.phone} onChange={(e) => setForm({ ...form, phone: (e.target as HTMLInputElement).value })} type="tel" />
        <Input label="Aadhaar Number *" value={form.aadhaar} onChange={(e) => setForm({ ...form, aadhaar: (e.target as HTMLInputElement).value })} placeholder="XXXX-XXXX-XXXX" />
        <Input label="Land Size (acres) *" value={form.landSize} onChange={(e) => setForm({ ...form, landSize: (e.target as HTMLInputElement).value })} type="number" />

        <h3 className="text-sm font-bold mt-5 mb-3" style={{ color: colors.gray[800] }}>Bank Details</h3>
        <Input label="Bank Account Details *" value={form.bankDetails} onChange={(e) => setForm({ ...form, bankDetails: (e.target as HTMLInputElement).value })} placeholder="Account number and IFSC code" />

        <h3 className="text-sm font-bold mt-5 mb-3" style={{ color: colors.gray[800] }}>Address</h3>
        <Input label="Complete Address *" value={form.address} onChange={(e) => setForm({ ...form, address: (e.target as HTMLInputElement).value })} multiline numberOfLines={3} />

        <h3 className="text-sm font-bold mt-5 mb-3" style={{ color: colors.gray[800] }}>Additional Information</h3>
        <Input label="Any additional details (optional)" value={form.additionalInfo} onChange={(e) => setForm({ ...form, additionalInfo: (e.target as HTMLInputElement).value })} multiline numberOfLines={3} />

        <h3 className="text-sm font-bold mt-5 mb-3" style={{ color: colors.gray[800] }}>Required Documents</h3>
        <p className="text-sm mb-3" style={{ color: colors.gray[500] }}>Please upload all required documents</p>

        <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ backgroundColor: colors.gray[200] }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${progress}%`, backgroundColor: colors.primary }} />
        </div>
        <p className="text-xs mb-3" style={{ color: colors.gray[500] }}>{uploadedCount} of {totalDocs} documents uploaded</p>

        {Object.keys(documents).map((doc) => (
          <button
            key={doc}
            onClick={() => setDocuments((prev) => ({ ...prev, [doc]: !prev[doc] }))}
            className="w-full flex items-center justify-between p-3.5 rounded-lg mb-2 border cursor-pointer"
            style={{ borderColor: colors.gray[200], backgroundColor: "transparent" }}
          >
            <div className="flex items-center gap-2.5">
              {documents[doc] ? <CheckSquare size={20} color={colors.primary} /> : <Square size={20} color={colors.gray[400]} />}
              <span className="text-sm" style={{ color: colors.gray[700] }}>{doc}</span>
            </div>
            <div className="flex items-center gap-1 px-2.5 py-1.5 rounded-md border" style={{ borderColor: documents[doc] ? colors.primary : colors.gray[300] }}>
              {documents[doc] ? <><FileCheck size={14} color={colors.primary} /><span className="text-xs font-semibold" style={{ color: colors.primary }}>Uploaded</span></> : <><Upload size={14} color={colors.gray[500]} /><span className="text-xs font-semibold" style={{ color: colors.gray[500] }}>Upload</span></>}
            </div>
          </button>
        ))}

        <div className="flex gap-3 mt-6">
          <Button title="Save as Draft" variant="outline" onPress={() => handleSubmit(true)} disabled={submitting} className="flex-1" />
          <Button title="Submit Application" onPress={() => handleSubmit(false)} loading={submitting} className="flex-1" />
        </div>
      </Card>
    </div>
  );
}
