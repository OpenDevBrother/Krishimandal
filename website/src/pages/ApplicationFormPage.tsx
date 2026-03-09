import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  CheckSquare, Square, FileCheck, Upload, ScanLine, Loader2, Sparkles, X,
} from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import { useAuth } from "../services/authContext";
import Card from "../components/Card";
import Input from "../components/Input";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Scheme { id: string; name: string; documents: string[]; }

interface OcrResult {
  document_type: string;
  extracted_fields?: Record<string, any>;
  extracted_text?: string;
  confidence: number;
  method: string;
}

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

  // OCR state
  const [ocrScanning, setOcrScanning] = useState(false);
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [ocrDocName, setOcrDocName] = useState<string | null>(null);
  const [showOcrPreview, setShowOcrPreview] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeDocRef = useRef<string | null>(null);

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

  // Handle file selection for a specific document
  const handleDocUpload = (docName: string) => {
    activeDocRef.current = docName;
    fileInputRef.current?.click();
  };

  // Process the selected file — upload + OCR + auto-fill
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const docName = activeDocRef.current;
    if (!file || !docName) return;

    // Reset input so same file can be re-selected
    e.target.value = "";

    setUploadingDoc(docName);
    setOcrScanning(true);
    setOcrDocName(docName);

    try {
      // Step 1: Call OCR endpoint — sends the filename to simulate OCR
      const ocrRes = await apiClient.post<OcrResult>("/documents/ocr", {
        image_path: file.name,
      });

      setOcrResult(ocrRes);

      // Step 2: Auto-fill form fields from OCR extracted data
      const fields = ocrRes.extracted_fields;
      if (fields) {
        autoFillFromOcr(fields);
        toast.success(`Document scanned! ${Object.keys(fields).length} fields auto-filled`);
      } else if (ocrRes.extracted_text) {
        // Try to parse fields from text response
        parseAndFillFromText(ocrRes.extracted_text);
        toast.success("Document scanned and processed!");
      }

      // Mark document as uploaded
      setDocuments((prev) => ({ ...prev, [docName]: true }));
      setShowOcrPreview(true);
    } catch (err: any) {
      toast.error("OCR scan failed. Document marked as uploaded.");
      setDocuments((prev) => ({ ...prev, [docName]: true }));
    } finally {
      setOcrScanning(false);
      setUploadingDoc(null);
    }
  };

  // Auto-fill form from structured OCR fields
  const autoFillFromOcr = (fields: Record<string, any>) => {
    setForm((prev) => {
      const updated = { ...prev };

      // Name
      if (fields.owner_name && !prev.name) {
        updated.name = fields.owner_name;
      }

      // Land size
      if (fields.area_hectares && !prev.landSize) {
        const acres = (parseFloat(fields.area_hectares) * 2.471).toFixed(1);
        updated.landSize = acres;
      }
      if (fields.area_acres && !prev.landSize) {
        updated.landSize = fields.area_acres.toString();
      }

      // Address fields
      const addressParts: string[] = [];
      if (fields.village) addressParts.push(fields.village);
      if (fields.taluka) addressParts.push(fields.taluka);
      if (fields.district) addressParts.push(fields.district);
      if (fields.state) addressParts.push(fields.state);
      if (addressParts.length > 0 && !prev.address) {
        updated.address = addressParts.join(", ");
      }

      // Aadhaar
      if (fields.aadhaar_number && !prev.aadhaar) {
        updated.aadhaar = fields.aadhaar_number;
      }

      // Bank
      if (fields.bank_account && !prev.bankDetails) {
        updated.bankDetails = fields.bank_account;
        if (fields.ifsc_code) {
          updated.bankDetails += ` / IFSC: ${fields.ifsc_code}`;
        }
      }

      // Additional info — crop info, survey number, etc.
      const extras: string[] = [];
      if (fields.survey_number) extras.push(`Survey No: ${fields.survey_number}`);
      if (fields.crop_listed) extras.push(`Crop: ${fields.crop_listed}`);
      if (extras.length > 0) {
        updated.additionalInfo = [prev.additionalInfo, ...extras].filter(Boolean).join("\n");
      }

      return updated;
    });
  };

  // Parse unstructured text for common field patterns
  const parseAndFillFromText = (text: string) => {
    const nameMatch = text.match(/(?:name|owner)[:\s]+([A-Za-z\s]+)/i);
    const aadhaarMatch = text.match(/(\d{4}[\s-]?\d{4}[\s-]?\d{4})/);
    const areaMatch = text.match(/([\d.]+)\s*(?:hectares?|ha)/i);
    const villageMatch = text.match(/(?:village|गांव)[:\s]+([A-Za-z\s]+)/i);

    setForm((prev) => {
      const updated = { ...prev };
      if (nameMatch && !prev.name) updated.name = nameMatch[1].trim();
      if (aadhaarMatch && !prev.aadhaar) updated.aadhaar = aadhaarMatch[1];
      if (areaMatch && !prev.landSize) {
        updated.landSize = (parseFloat(areaMatch[1]) * 2.471).toFixed(1);
      }
      if (villageMatch && !prev.address) updated.address = villageMatch[1].trim();
      return updated;
    });
  };

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
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf"
        className="hidden"
        onChange={handleFileSelected}
      />

      <button onClick={() => navigate(-1)} className="text-sm font-semibold mb-4 border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>← Back</button>
      <Card>
        <h1 className="text-lg font-bold mb-1" style={{ color: colors.gray[900] }}>Application Form</h1>
        <p className="text-sm mb-5" style={{ color: colors.gray[500] }}>{scheme.name}</p>

        {/* OCR Smart Scan Banner */}
        <div
          className="flex items-center gap-3 p-3 rounded-xl mb-5 border"
          style={{ backgroundColor: colors.blue[50], borderColor: colors.blue[500] + "30" }}
        >
          <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: colors.blue[100] }}>
            <ScanLine size={20} style={{ color: colors.blue[600] }} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold m-0" style={{ color: colors.blue[900] }}>Smart Document Scan</p>
            <p className="text-xs m-0" style={{ color: colors.blue[700] }}>
              Upload documents below — AI will scan and auto-fill your form fields
            </p>
          </div>
          <Sparkles size={16} style={{ color: colors.blue[500] }} />
        </div>

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
        <p className="text-sm mb-3" style={{ color: colors.gray[500] }}>
          Upload documents — AI will extract data and auto-fill your form
        </p>

        <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ backgroundColor: colors.gray[200] }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${progress}%`, backgroundColor: colors.primary }} />
        </div>
        <p className="text-xs mb-3" style={{ color: colors.gray[500] }}>{uploadedCount} of {totalDocs} documents uploaded</p>

        {Object.keys(documents).map((doc) => (
          <div
            key={doc}
            className="w-full flex items-center justify-between p-3.5 rounded-lg mb-2 border"
            style={{ borderColor: documents[doc] ? colors.primary + "40" : colors.gray[200], backgroundColor: documents[doc] ? colors.primaryLight + "40" : "transparent" }}
          >
            <div className="flex items-center gap-2.5">
              {documents[doc] ? <CheckSquare size={20} color={colors.primary} /> : <Square size={20} color={colors.gray[400]} />}
              <div>
                <span className="text-sm block" style={{ color: colors.gray[700] }}>{doc}</span>
                {documents[doc] && ocrDocName === doc && ocrResult && (
                  <span className="text-[11px]" style={{ color: colors.primary }}>
                    Scanned: {ocrResult.document_type} ({Math.round(ocrResult.confidence * 100)}% confidence)
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={() => handleDocUpload(doc)}
              disabled={ocrScanning}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border cursor-pointer transition-colors disabled:opacity-50"
              style={{
                borderColor: documents[doc] ? colors.primary : colors.gray[300],
                backgroundColor: documents[doc] ? colors.primaryLight : "transparent",
              }}
            >
              {uploadingDoc === doc ? (
                <>
                  <Loader2 size={14} className="animate-spin" style={{ color: colors.primary }} />
                  <span className="text-xs font-semibold" style={{ color: colors.primary }}>Scanning...</span>
                </>
              ) : documents[doc] ? (
                <>
                  <FileCheck size={14} color={colors.primary} />
                  <span className="text-xs font-semibold" style={{ color: colors.primary }}>Re-upload</span>
                </>
              ) : (
                <>
                  <Upload size={14} color={colors.gray[500]} />
                  <span className="text-xs font-semibold" style={{ color: colors.gray[500] }}>Upload & Scan</span>
                </>
              )}
            </button>
          </div>
        ))}

        {/* OCR Result Preview */}
        {showOcrPreview && ocrResult && (
          <div className="mt-3 p-3 rounded-xl border" style={{ backgroundColor: colors.green[50], borderColor: colors.green[600] + "30" }}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <ScanLine size={16} style={{ color: colors.green[700] }} />
                <span className="text-xs font-bold" style={{ color: colors.green[700] }}>
                  OCR Results — {ocrResult.document_type}
                </span>
              </div>
              <button onClick={() => setShowOcrPreview(false)} className="border-none bg-transparent cursor-pointer p-0">
                <X size={14} color={colors.gray[400]} />
              </button>
            </div>
            <div className="text-xs space-y-1" style={{ color: colors.gray[700] }}>
              {ocrResult.extracted_fields && Object.entries(ocrResult.extracted_fields).map(([key, val]) => (
                <div key={key} className="flex gap-2">
                  <span className="text-gray-500 capitalize min-w-[100px]">{key.replace(/_/g, " ")}:</span>
                  <span className="font-medium">{String(val)}</span>
                </div>
              ))}
              <div className="flex items-center gap-1 mt-2 pt-2 border-t border-green-200">
                <Sparkles size={12} style={{ color: colors.green[600] }} />
                <span style={{ color: colors.green[700] }}>
                  Fields auto-filled into your form ({Math.round(ocrResult.confidence * 100)}% confidence, {ocrResult.method})
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-3 mt-6">
          <Button title="Save as Draft" variant="outline" onPress={() => handleSubmit(true)} disabled={submitting} className="flex-1" />
          <Button title="Submit Application" onPress={() => handleSubmit(false)} loading={submitting} className="flex-1" />
        </div>
      </Card>
    </div>
  );
}
