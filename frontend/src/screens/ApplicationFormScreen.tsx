import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Image,
} from "react-native";
import {
  CheckSquare,
  Square,
  FileCheck,
  Upload,
  Camera,
  Image as ImageIcon,
  Scan,
  Sparkles,
} from "lucide-react-native";
import * as ImagePicker from "expo-image-picker";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import { useAuth } from "../services/authContext";
import Card from "../components/Card";
import Input from "../components/Input";
import Button from "../components/Button";
import { colors } from "../constants/theme";
import type { ApplicationFormScreenProps } from "../navigation/types";

interface Scheme {
  id: string;
  name: string;
  documents: string[];
}

interface OcrResult {
  document_type: string;
  extracted_fields?: Record<string, any>;
  confidence: number;
  method: string;
}

interface DocState {
  uploaded: boolean;
  uri?: string;
  ocrResult?: OcrResult;
}

export default function ApplicationFormScreen({
  route,
  navigation,
}: ApplicationFormScreenProps) {
  const { schemeId } = route.params;
  const { farmer } = useAuth();
  const [scheme, setScheme] = useState<Scheme | null>(null);

  const [form, setForm] = useState({
    name: "",
    phone: "",
    aadhaar: "",
    landSize: "",
    bankDetails: "",
    address: "",
    additionalInfo: "",
  });

  const [documents, setDocuments] = useState<Record<string, DocState>>({});
  const [submitting, setSubmitting] = useState(false);
  const [ocrLoading, setOcrLoading] = useState<string | null>(null);
  const [ocrResults, setOcrResults] = useState<OcrResult[]>([]);
  const [autoFilledFields, setAutoFilledFields] = useState<string[]>([]);

  useEffect(() => {
    fetchScheme();
  }, [schemeId]);

  const fetchScheme = async () => {
    try {
      const path = await apiClient.farmPath("/schemes");
      const data = await apiClient.get<Scheme[]>(path);
      const found = data.find((s: any) => (s.id || s.scheme_id) === schemeId);
      if (found) {
        const mapped: Scheme = {
          id: (found as any).id || (found as any).scheme_id || "",
          name: (found as any).name || (found as any).scheme_name || "",
          documents: (found as any).documents || (found as any).requirements || [],
        };
        setScheme(mapped);
        const docs: Record<string, DocState> = {};
        (mapped.documents || []).forEach((d: string) => (docs[d] = { uploaded: false }));
        setDocuments(docs);
      }
    } catch {
      Toast.show({ type: "error", text1: "Could not load scheme" });
    }
  };

  const uploadedCount = Object.values(documents).filter((d) => d.uploaded).length;
  const totalDocs = Object.keys(documents).length;
  const progress = totalDocs > 0 ? (uploadedCount / totalDocs) * 100 : 0;

  // ── Pick document image ──
  const pickDocument = async (docName: string, source: "camera" | "gallery") => {
    try {
      let result: ImagePicker.ImagePickerResult;

      if (source === "camera") {
        const { granted } = await ImagePicker.requestCameraPermissionsAsync();
        if (!granted) {
          Toast.show({ type: "error", text1: "Camera permission denied" });
          return;
        }
        result = await ImagePicker.launchCameraAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          base64: true,
        });
      } else {
        const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!granted) {
          Toast.show({ type: "error", text1: "Gallery permission denied" });
          return;
        }
        result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ["images"],
          quality: 0.8,
          base64: true,
        });
      }

      if (result.canceled || !result.assets?.[0]) return;

      const asset = result.assets[0];
      setDocuments((prev) => ({
        ...prev,
        [docName]: { uploaded: true, uri: asset.uri },
      }));

      Toast.show({ type: "success", text1: `${docName} uploaded` });

      // Run OCR automatically
      await runOcr(docName, asset.uri);
    } catch (err: any) {
      Toast.show({ type: "error", text1: "Failed to pick document" });
    }
  };

  // ── Run OCR on uploaded document ──
  const runOcr = async (docName: string, uri: string) => {
    setOcrLoading(docName);
    try {
      const ocrRes = await apiClient.post<OcrResult>("/documents/ocr", {
        image_path: uri,
        document_name: docName,
      });

      setDocuments((prev) => ({
        ...prev,
        [docName]: { ...prev[docName], ocrResult: ocrRes },
      }));

      setOcrResults((prev) => [...prev, ocrRes]);

      // Auto-fill form fields from OCR
      if (ocrRes.extracted_fields) {
        autoFillFromOcr(ocrRes.extracted_fields);
      }

      Toast.show({
        type: "success",
        text1: "OCR Complete",
        text2: `${ocrRes.document_type} — ${Math.round(ocrRes.confidence * 100)}% confidence`,
      });
    } catch {
      Toast.show({ type: "info", text1: "Document uploaded (OCR unavailable)" });
    } finally {
      setOcrLoading(null);
    }
  };

  // ── Auto-fill from structured OCR fields ──
  // Only fills: Full Name, Aadhaar Number, Complete Address
  const autoFillFromOcr = (fields: Record<string, any>) => {
    setForm((prev) => {
      const updated = { ...prev };
      const filled: string[] = [];

      // Full Name
      const name = fields.name || fields.owner_name;
      if (name) {
        updated.name = String(name);
        filled.push("Full Name");
      }

      // Aadhaar Number
      const aadhaar = fields.aadhaar_number || fields.aadhaar_last4 || fields.aadhaar;
      if (aadhaar) {
        updated.aadhaar = String(aadhaar).replace(/\s/g, "-");
        filled.push("Aadhaar");
      }

      // Complete Address — nested object or flat fields
      if (fields.address && typeof fields.address === "object") {
        const addr = fields.address;
        if (addr.raw) {
          updated.address = addr.raw;
        } else {
          const parts = [addr.village, addr.taluka, addr.district, addr.state, addr.pincode].filter(Boolean);
          if (parts.length > 0) updated.address = parts.join(", ");
        }
        filled.push("Address");
      } else if (fields.village || fields.district || fields.taluka || fields.state) {
        const parts = [fields.village, fields.taluka, fields.district, fields.state].filter(Boolean);
        if (parts.length > 0) {
          updated.address = parts.join(", ");
          filled.push("Address");
        }
      }

      if (filled.length > 0) {
        setAutoFilledFields((p) => [...new Set([...p, ...filled])]);
      }
      return updated;
    });
  };

  // ── Show document picker options ──
  const showPickerOptions = (docName: string) => {
    pickDocument(docName, "gallery");
  };

  const handleSubmit = async (isDraft: boolean) => {
    if (!isDraft && uploadedCount < totalDocs) {
      Toast.show({ type: "error", text1: "Please upload all required documents" });
      return;
    }

    setSubmitting(true);
    try {
      const path = await apiClient.farmPath("/applications");
      await apiClient.post(path, {
        scheme_id: schemeId,
        scheme_name: scheme?.name || "",
        status: isDraft ? "draft" : "submitted",
        personal_info: {
          name: form.name,
          phone: form.phone,
          aadhaar: form.aadhaar,
          land_size: parseFloat(form.landSize) || 0,
          bank_details: form.bankDetails,
          address: form.address,
          additional_info: form.additionalInfo,
        },
        documents: Object.entries(documents).map(([name, state]) => ({
          name,
          uploaded: state.uploaded,
        })),
      });

      Toast.show({
        type: "success",
        text1: isDraft
          ? "Application saved as draft"
          : "Application submitted successfully!",
      });
      setTimeout(() => navigation.navigate("Applications"), 500);
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed to submit" });
    } finally {
      setSubmitting(false);
    }
  };

  if (!scheme) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>Loading...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
    >
      <Card>
        <Text style={styles.cardTitle}>Application Form</Text>
        <Text style={styles.cardSubtitle}>{scheme.name}</Text>

        {/* OCR auto-fill banner */}
        {autoFilledFields.length > 0 && (
          <View style={styles.ocrBanner}>
            <Sparkles size={16} color={colors.primary} />
            <View style={{ flex: 1 }}>
              <Text style={styles.ocrBannerTitle}>
                Auto-filled from document OCR
              </Text>
              <Text style={styles.ocrBannerFields}>
                {autoFilledFields.join(", ")}
              </Text>
            </View>
          </View>
        )}

        {/* Personal Details */}
        <Text style={styles.sectionTitle}>Personal Details</Text>
        <Input
          label="Full Name *"
          value={form.name}
          onChangeText={(t) => setForm({ ...form, name: t })}
        />
        <Input
          label="Phone Number *"
          value={form.phone}
          onChangeText={(t) => setForm({ ...form, phone: t })}
          keyboardType="phone-pad"
        />
        <Input
          label="Aadhaar Number *"
          value={form.aadhaar}
          onChangeText={(t) => setForm({ ...form, aadhaar: t })}
          placeholder="XXXX-XXXX-XXXX"
          keyboardType="number-pad"
        />
        <Input
          label="Land Size (acres) *"
          value={form.landSize}
          onChangeText={(t) => setForm({ ...form, landSize: t })}
          keyboardType="decimal-pad"
        />

        {/* Bank Details */}
        <Text style={styles.sectionTitle}>Bank Details</Text>
        <Input
          label="Bank Account Details *"
          value={form.bankDetails}
          onChangeText={(t) => setForm({ ...form, bankDetails: t })}
          placeholder="Account number and IFSC code"
        />

        {/* Address */}
        <Text style={styles.sectionTitle}>Address</Text>
        <Input
          label="Complete Address *"
          value={form.address}
          onChangeText={(t) => setForm({ ...form, address: t })}
          multiline
          numberOfLines={3}
          style={{ textAlignVertical: "top", minHeight: 80 }}
        />

        {/* Additional Info */}
        <Text style={styles.sectionTitle}>Additional Information</Text>
        <Input
          label="Any additional details (optional)"
          value={form.additionalInfo}
          onChangeText={(t) => setForm({ ...form, additionalInfo: t })}
          multiline
          numberOfLines={3}
          style={{ textAlignVertical: "top", minHeight: 80 }}
        />

        {/* Documents */}
        <Text style={styles.sectionTitle}>Required Documents</Text>
        <Text style={styles.docHelper}>
          Upload documents to auto-fill form fields with OCR
        </Text>

        {/* Progress bar */}
        <View style={styles.progressBg}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>
          {uploadedCount} of {totalDocs} documents uploaded
        </Text>

        {Object.keys(documents).map((doc) => {
          const docState = documents[doc];
          const isOcrLoading = ocrLoading === doc;

          return (
            <View key={doc} style={styles.docCard}>
              <View style={styles.docRow}>
                <View style={styles.docLeft}>
                  {docState.uploaded ? (
                    <CheckSquare size={20} color={colors.primary} />
                  ) : (
                    <Square size={20} color={colors.gray[400]} />
                  )}
                  <Text style={styles.docName}>{doc}</Text>
                </View>

                {isOcrLoading && (
                  <View style={styles.ocrLoadingBadge}>
                    <ActivityIndicator size="small" color={colors.primary} />
                    <Text style={styles.ocrLoadingText}>Scanning...</Text>
                  </View>
                )}
              </View>

              {/* Upload buttons */}
              <View style={styles.docActions}>
                <TouchableOpacity
                  style={styles.docActionBtn}
                  onPress={() => pickDocument(doc, "camera")}
                  activeOpacity={0.7}
                >
                  <Camera size={16} color={colors.primary} />
                  <Text style={styles.docActionText}>Camera</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.docActionBtn}
                  onPress={() => pickDocument(doc, "gallery")}
                  activeOpacity={0.7}
                >
                  <ImageIcon size={16} color={colors.primary} />
                  <Text style={styles.docActionText}>Gallery</Text>
                </TouchableOpacity>

                {docState.uploaded && !isOcrLoading && (
                  <TouchableOpacity
                    style={[styles.docActionBtn, styles.docActionBtnOcr]}
                    onPress={() => docState.uri && runOcr(doc, docState.uri)}
                    activeOpacity={0.7}
                  >
                    <Scan size={16} color={colors.white} />
                    <Text style={[styles.docActionText, { color: colors.white }]}>
                      Re-scan OCR
                    </Text>
                  </TouchableOpacity>
                )}
              </View>

              {/* Document preview thumbnail */}
              {docState.uri && (
                <Image
                  source={{ uri: docState.uri }}
                  style={styles.docPreview}
                  resizeMode="cover"
                />
              )}

              {/* OCR result preview */}
              {docState.ocrResult && (
                <View style={styles.ocrResultBox}>
                  <View style={styles.ocrResultHeader}>
                    <Sparkles size={12} color={colors.primary} />
                    <Text style={styles.ocrResultType}>
                      {docState.ocrResult.document_type}
                    </Text>
                    <Text style={styles.ocrResultConf}>
                      {Math.round(docState.ocrResult.confidence * 100)}%
                    </Text>
                  </View>
                  {docState.ocrResult.extracted_fields && (
                    <View style={styles.ocrFields}>
                      {Object.entries(docState.ocrResult.extracted_fields).map(
                        ([key, value]) => (
                          <Text key={key} style={styles.ocrFieldText}>
                            {key.replace(/_/g, " ")}: {String(value)}
                          </Text>
                        )
                      )}
                    </View>
                  )}
                </View>
              )}
            </View>
          );
        })}

        {/* Buttons */}
        <View style={styles.actionRow}>
          <Button
            title="Save as Draft"
            variant="outline"
            onPress={() => handleSubmit(true)}
            disabled={submitting}
            style={{ flex: 1 }}
          />
          <Button
            title="Submit Application"
            onPress={() => handleSubmit(false)}
            loading={submitting}
            style={{ flex: 1 }}
          />
        </View>
      </Card>
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  scrollContent: { padding: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  emptyText: { color: colors.gray[500] },
  cardTitle: { fontSize: 18, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  cardSubtitle: { fontSize: 13, color: colors.gray[500], marginBottom: 20 },
  sectionTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.gray[800],
    marginTop: 20,
    marginBottom: 12,
  },
  // OCR banner
  ocrBanner: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    backgroundColor: "#E8F5E9",
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  ocrBannerTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.primary,
  },
  ocrBannerFields: {
    fontSize: 11,
    color: colors.gray[600],
    marginTop: 2,
  },
  // Documents
  docHelper: { fontSize: 13, color: colors.gray[500], marginBottom: 12 },
  progressBg: {
    height: 6,
    backgroundColor: colors.gray[200],
    borderRadius: 3,
    overflow: "hidden",
    marginBottom: 8,
  },
  progressFill: {
    height: "100%",
    backgroundColor: colors.primary,
    borderRadius: 3,
  },
  progressText: { fontSize: 12, color: colors.gray[500], marginBottom: 12 },
  docCard: {
    borderWidth: 1,
    borderColor: colors.gray[200],
    borderRadius: 10,
    marginBottom: 10,
    padding: 12,
    backgroundColor: colors.white,
  },
  docRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  docLeft: { flexDirection: "row", alignItems: "center", gap: 10, flex: 1 },
  docName: { fontSize: 14, fontWeight: "600", color: colors.gray[700] },
  docActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  docActionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 6,
  },
  docActionBtnOcr: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  docActionText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.primary,
  },
  docPreview: {
    width: "100%",
    height: 120,
    borderRadius: 6,
    marginTop: 10,
    backgroundColor: colors.gray[100],
  },
  ocrLoadingBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  ocrLoadingText: {
    fontSize: 11,
    color: colors.primary,
  },
  ocrResultBox: {
    backgroundColor: colors.gray[50],
    borderRadius: 6,
    padding: 10,
    marginTop: 8,
    borderWidth: 1,
    borderColor: colors.gray[200],
  },
  ocrResultHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  ocrResultType: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.gray[700],
    flex: 1,
  },
  ocrResultConf: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.primary,
  },
  ocrFields: { gap: 2 },
  ocrFieldText: {
    fontSize: 11,
    color: colors.gray[600],
  },
  actionRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 24,
  },
});
