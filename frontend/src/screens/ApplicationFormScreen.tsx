import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from "react-native";
import { CheckSquare, Square, FileCheck, Upload } from "lucide-react-native";
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

export default function ApplicationFormScreen({
  route,
  navigation,
}: ApplicationFormScreenProps) {
  const { schemeId } = route.params;
  const { farmer } = useAuth();
  const [scheme, setScheme] = useState<Scheme | null>(null);

  const [form, setForm] = useState({
    name: farmer?.name || "",
    phone: farmer?.phone_number || "",
    aadhaar: "",
    landSize: farmer?.land_size?.toString() || "",
    bankDetails: "",
    address: farmer?.village
      ? `${farmer.village}, ${farmer.state || ""}`
      : "",
    additionalInfo: "",
  });

  const [documents, setDocuments] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);

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
        const docs: Record<string, boolean> = {};
        (mapped.documents || []).forEach((d: string) => (docs[d] = false));
        setDocuments(docs);
      }
    } catch {
      Toast.show({ type: "error", text1: "Could not load scheme" });
    }
  };

  const uploadedCount = Object.values(documents).filter(Boolean).length;
  const totalDocs = Object.keys(documents).length;
  const progress = totalDocs > 0 ? (uploadedCount / totalDocs) * 100 : 0;

  const toggleDoc = (doc: string) => {
    setDocuments((prev) => ({ ...prev, [doc]: !prev[doc] }));
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
        documents: Object.entries(documents).map(([name, uploaded]) => ({
          name,
          uploaded,
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
          Please upload all required documents
        </Text>

        {/* Progress bar */}
        <View style={styles.progressBg}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>
          {uploadedCount} of {totalDocs} documents uploaded
        </Text>

        {Object.keys(documents).map((doc) => (
          <TouchableOpacity
            key={doc}
            style={styles.docRow}
            onPress={() => toggleDoc(doc)}
            activeOpacity={0.7}
          >
            <View style={styles.docLeft}>
              {documents[doc] ? (
                <CheckSquare size={20} color={colors.primary} />
              ) : (
                <Square size={20} color={colors.gray[400]} />
              )}
              <Text style={styles.docName}>{doc}</Text>
            </View>
            <View
              style={[
                styles.uploadBtn,
                documents[doc] && { borderColor: colors.primary },
              ]}
            >
              {documents[doc] ? (
                <>
                  <FileCheck size={14} color={colors.primary} />
                  <Text style={[styles.uploadText, { color: colors.primary }]}>
                    Uploaded
                  </Text>
                </>
              ) : (
                <>
                  <Upload size={14} color={colors.gray[500]} />
                  <Text style={styles.uploadText}>Upload</Text>
                </>
              )}
            </View>
          </TouchableOpacity>
        ))}

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
  docRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 14,
    borderWidth: 1,
    borderColor: colors.gray[200],
    borderRadius: 8,
    marginBottom: 8,
  },
  docLeft: { flexDirection: "row", alignItems: "center", gap: 10, flex: 1 },
  docName: { fontSize: 14, color: colors.gray[700] },
  uploadBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: colors.gray[300],
    borderRadius: 6,
  },
  uploadText: { fontSize: 12, fontWeight: "600", color: colors.gray[500] },
  actionRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 24,
  },
});
