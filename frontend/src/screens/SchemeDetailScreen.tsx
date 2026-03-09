import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import {
  MapPin,
  Calendar,
  CheckCircle,
  FileText,
  XCircle,
  AlertCircle,
} from "lucide-react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";
import type { SchemeDetailScreenProps } from "../navigation/types";

interface Scheme {
  id: string;
  name: string;
  category: string;
  state: string;
  description: string;
  benefits: string[];
  documents: string[];
  deadline?: string;
  eligibility?: {
    minLandSize?: number;
    maxLandSize?: number;
    cropTypes?: string[];
    state?: string;
  };
  eligibility_status?: string;
  eligibility_missing?: string[];
}

export default function SchemeDetailScreen({
  route,
  navigation,
}: SchemeDetailScreenProps) {
  const { schemeId } = route.params;
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScheme();
  }, [schemeId]);

  const fetchScheme = async () => {
    try {
      const path = await apiClient.farmPath("/schemes");
      const data = await apiClient.get<any[]>(path);
      const raw = data.find((s) => (s.id || s.scheme_id) === schemeId);
      if (raw) {
        setScheme({
          id: raw.id || raw.scheme_id || "",
          name: raw.name || raw.scheme_name || "",
          category: raw.category || "subsidy",
          state: raw.state || "All India",
          description: raw.description || "",
          benefits: raw.benefits || (raw.benefits_inr ? [`\u20B9${raw.benefits_inr.toLocaleString()}`] : []),
          documents: raw.documents || raw.requirements || [],
          deadline: raw.deadline,
          eligibility_status: raw.eligibility_status || (raw.eligibility_score != null ? (raw.eligibility_score >= 0.7 ? "eligible" : raw.eligibility_score >= 0.4 ? "partially_eligible" : "not_eligible") : "eligible"),
          eligibility_missing: raw.eligibility_missing || raw.missing_criteria || [],
        });
      } else {
        setScheme(null);
      }
    } catch {
      Toast.show({ type: "error", text1: "Could not load scheme details" });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!scheme) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>Scheme not found</Text>
      </View>
    );
  }

  const catBadge: Record<string, { bg: string; text: string }> = {
    subsidy: { bg: colors.green[100], text: colors.green[700] },
    insurance: { bg: colors.blue[100], text: colors.blue[700] },
    irrigation: { bg: colors.cyan[100], text: colors.cyan[700] },
    credit: { bg: colors.purple[100], text: colors.purple[700] },
  };
  const badge = catBadge[scheme.category] || catBadge.subsidy;

  const eligStatus = scheme.eligibility_status || "eligible";
  const eligible = eligStatus === "eligible";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
    >
      <Card>
        {/* Header */}
        <View style={styles.row}>
          <View style={{ flex: 1, marginRight: 12 }}>
            <Text style={styles.name}>{scheme.name}</Text>
            <Text style={styles.description}>{scheme.description}</Text>
          </View>
          <Badge label={scheme.category} bgColor={badge.bg} textColor={badge.text} />
        </View>

        {/* Meta */}
        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <MapPin size={16} color={colors.gray[400]} />
            <Text style={styles.metaText}>{scheme.state || "All India"}</Text>
          </View>
          {scheme.deadline && (
            <View style={styles.metaItem}>
              <Calendar size={16} color={colors.gray[400]} />
              <Text style={styles.metaText}>
                Deadline: {new Date(scheme.deadline).toLocaleDateString()}
              </Text>
            </View>
          )}
        </View>

        {/* Divider */}
        <View style={styles.divider} />

        {/* Benefits */}
        <Text style={styles.sectionTitle}>Benefits</Text>
        {(scheme.benefits || []).map((b, i) => (
          <View key={i} style={styles.listItem}>
            <CheckCircle size={16} color={colors.green[600]} />
            <Text style={styles.listText}>{b}</Text>
          </View>
        ))}

        <View style={styles.divider} />

        {/* Documents */}
        <Text style={styles.sectionTitle}>Required Documents</Text>
        {(scheme.documents || []).map((d, i) => (
          <View key={i} style={styles.listItem}>
            <FileText size={16} color={colors.blue[600]} />
            <Text style={styles.listText}>{d}</Text>
          </View>
        ))}

        <View style={styles.divider} />

        {/* Eligibility Criteria */}
        <Text style={styles.sectionTitle}>Eligibility Criteria</Text>
        {scheme.eligibility?.minLandSize && (
          <Text style={styles.criteriaText}>
            {"\u2022"} Minimum land size: {scheme.eligibility.minLandSize} acres
          </Text>
        )}
        {scheme.eligibility?.maxLandSize && (
          <Text style={styles.criteriaText}>
            {"\u2022"} Maximum land size: {scheme.eligibility.maxLandSize} acres
          </Text>
        )}
        {scheme.eligibility?.cropTypes &&
          scheme.eligibility.cropTypes.length > 0 && (
            <Text style={styles.criteriaText}>
              {"\u2022"} Applicable for: {scheme.eligibility.cropTypes.join(", ")}
            </Text>
          )}
        {scheme.eligibility?.state && (
          <Text style={styles.criteriaText}>
            {"\u2022"} Available in: {scheme.eligibility.state}
          </Text>
        )}

        {/* Eligibility Check */}
        <View
          style={[
            styles.eligBox,
            eligible
              ? { backgroundColor: colors.green[50], borderColor: colors.green[100] }
              : eligStatus === "partially_eligible"
              ? { backgroundColor: colors.yellow[50], borderColor: colors.yellow[200] }
              : { backgroundColor: colors.red[50], borderColor: colors.red[100] },
          ]}
        >
          <View style={styles.eligRow}>
            {eligible ? (
              <CheckCircle size={20} color={colors.green[600]} />
            ) : eligStatus === "partially_eligible" ? (
              <AlertCircle size={20} color={colors.yellow[600]} />
            ) : (
              <XCircle size={20} color={colors.red[600]} />
            )}
            <Text style={styles.eligTitle}>
              {eligible
                ? "You are eligible for this scheme"
                : eligStatus === "partially_eligible"
                ? "Partially Eligible"
                : "Not Eligible"}
            </Text>
          </View>
          {(scheme.eligibility_missing || []).length > 0 && (
            <View style={{ marginTop: 8 }}>
              <Text style={styles.eligMissingTitle}>Missing criteria:</Text>
              {scheme.eligibility_missing!.map((m, i) => (
                <Text key={i} style={styles.eligMissingItem}>
                  {"\u2022"} {m}
                </Text>
              ))}
            </View>
          )}
        </View>

        {/* Apply Button */}
        <Button
          title="Apply for This Scheme"
          size="lg"
          fullWidth
          onPress={() =>
            navigation.navigate("ApplicationForm", { schemeId: scheme.id })
          }
          style={{ marginTop: 20 }}
        />
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
  row: { flexDirection: "row", alignItems: "flex-start" },
  name: { fontSize: 18, fontWeight: "700", color: colors.gray[900], marginBottom: 8 },
  description: { fontSize: 13, color: colors.gray[500], lineHeight: 19 },
  metaRow: { flexDirection: "row", flexWrap: "wrap", gap: 16, marginTop: 16 },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  metaText: { fontSize: 13, color: colors.gray[600] },
  divider: {
    height: 1,
    backgroundColor: colors.gray[200],
    marginVertical: 16,
  },
  sectionTitle: { fontSize: 14, fontWeight: "700", color: colors.gray[800], marginBottom: 12 },
  listItem: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 8 },
  listText: { fontSize: 13, color: colors.gray[700], flex: 1 },
  criteriaText: { fontSize: 13, color: colors.gray[600], marginBottom: 6 },
  eligBox: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
    marginTop: 16,
  },
  eligRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  eligTitle: { fontSize: 14, fontWeight: "600", color: colors.gray[800] },
  eligMissingTitle: { fontSize: 13, fontWeight: "600", color: colors.gray[700] },
  eligMissingItem: { fontSize: 12, color: colors.gray[600], marginLeft: 8, marginTop: 2 },
});
