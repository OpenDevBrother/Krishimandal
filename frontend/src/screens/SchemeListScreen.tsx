import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { CheckCircle } from "lucide-react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Header from "../components/Header";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import { colors } from "../constants/theme";
import type { SchemeListScreenProps } from "../navigation/types";

interface SchemeRaw {
  scheme_id?: string;
  scheme_name?: string;
  id?: string;
  name?: string;
  category?: string;
  state?: string;
  description?: string;
  benefits?: string[];
  benefits_inr?: number;
  documents?: string[];
  requirements?: string[];
  deadline?: string;
  eligibility_status?: string;
  eligibility_score?: number;
  missing_criteria?: string[];
  application_url?: string;
}

interface Scheme {
  id: string;
  name: string;
  category: string;
  state: string;
  description: string;
  benefits: string[];
  documents: string[];
  deadline?: string;
  eligibility_status?: string;
}

const CATEGORIES = [
  { value: "all", label: "All" },
  { value: "subsidy", label: "Subsidy" },
  { value: "insurance", label: "Insurance" },
  { value: "irrigation", label: "Irrigation" },
  { value: "credit", label: "Credit" },
];

const CATEGORY_ICONS: Record<string, string> = {
  subsidy: "\u{1F4B0}",
  insurance: "\u{1F6E1}\uFE0F",
  irrigation: "\u{1F4A7}",
  credit: "\u{1F4B3}",
};

const CATEGORY_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  subsidy: { bg: colors.amber[100], text: colors.amber[700], label: "CENTRAL GOVT" },
  insurance: { bg: colors.blue[100], text: colors.blue[700], label: "INSURANCE" },
  irrigation: { bg: colors.cyan[100], text: colors.cyan[700], label: "IRRIGATION" },
  credit: { bg: colors.purple[100], text: colors.purple[700], label: "CREDIT" },
};

export default function SchemeListScreen({ navigation }: SchemeListScreenProps) {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  const fetchSchemes = async () => {
    try {
      const path = await apiClient.farmPath("/schemes");
      const data = await apiClient.get<SchemeRaw[]>(path);
      const mapped: Scheme[] = data.map((s) => ({
        id: s.id || s.scheme_id || "",
        name: s.name || s.scheme_name || "",
        category: s.category || "subsidy",
        state: s.state || "All India",
        description: s.description || "",
        benefits: s.benefits || (s.benefits_inr ? [`\u20B9${s.benefits_inr.toLocaleString()}`] : []),
        documents: s.documents || s.requirements || [],
        deadline: s.deadline,
        eligibility_status: s.eligibility_status || (s.eligibility_score && s.eligibility_score >= 0.7 ? "eligible" : undefined),
      }));
      setSchemes(mapped);
    } catch {
      Toast.show({ type: "error", text1: "Could not load schemes" });
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchSchemes();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchSchemes();
    setRefreshing(false);
  };

  const filtered = schemes.filter((s) => {
    const matchSearch =
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.description || "").toLowerCase().includes(search.toLowerCase());
    const matchCat = category === "all" || s.category === category;
    return matchSearch && matchCat;
  });

  const getBenefitPreview = (scheme: Scheme) => {
    if (scheme.name.includes("PM-KISAN")) return "\u20B96,000";
    if (scheme.name.includes("KCC")) return "\u20B91.6 Lakh";
    if (scheme.name.includes("PMFBY")) return "2% Premium";
    return "Benefits Available";
  };

  return (
    <View style={styles.container}>
      <Header />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.primary]} />
        }
      >
        <Text style={styles.title}>Scheme & Credit</Text>
        <Text style={styles.subtitle}>Browse and apply for agricultural schemes</Text>

        {/* Search */}
        <Card style={styles.mb16}>
          <Input
            placeholder="Search schemes..."
            value={search}
            onChangeText={setSearch}
          />
        </Card>

        {/* Category Pills */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.pillScroll}
          contentContainerStyle={styles.pillRow}
        >
          {CATEGORIES.map((cat) => (
            <TouchableOpacity
              key={cat.value}
              onPress={() => setCategory(cat.value)}
              style={[
                styles.pill,
                category === cat.value && styles.pillActive,
              ]}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.pillText,
                  category === cat.value && styles.pillTextActive,
                ]}
              >
                {cat.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Text style={[styles.sectionTitle, styles.mb12]}>Eligible Schemes</Text>

        {filtered.length === 0 ? (
          <Card>
            <Text style={styles.emptyText}>
              No schemes found matching your filters.
            </Text>
          </Card>
        ) : (
          filtered.map((scheme) => {
            const badge = CATEGORY_BADGE[scheme.category] || CATEGORY_BADGE.subsidy;
            return (
              <Card key={scheme.id} style={styles.mb12}>
                <View style={styles.row}>
                  <View style={styles.schemeIcon}>
                    <Text style={{ fontSize: 18 }}>
                      {CATEGORY_ICONS[scheme.category] || "\u{1F4B0}"}
                    </Text>
                  </View>
                  <View style={{ flex: 1, marginRight: 8 }}>
                    <Text style={styles.schemeName} numberOfLines={2}>
                      {scheme.name}
                    </Text>
                    <Text style={styles.schemeDesc} numberOfLines={2}>
                      {scheme.description}
                    </Text>
                  </View>
                  <Badge
                    label={badge.label}
                    bgColor={badge.bg}
                    textColor={badge.text}
                    textStyle={{ fontSize: 9 }}
                  />
                </View>

                {/* Benefit preview */}
                <View style={styles.benefitBox}>
                  <Text style={styles.benefitLabel}>
                    {scheme.category === "subsidy" ? "ANNUAL BENEFIT" : "CREDIT LIMIT"}
                  </Text>
                  <Text style={styles.benefitValue}>{getBenefitPreview(scheme)}</Text>
                </View>

                {/* Eligibility */}
                {scheme.eligibility_status === "eligible" && (
                  <View style={styles.eligibleRow}>
                    <CheckCircle size={14} color={colors.green[700]} />
                    <Text style={styles.eligibleText}>You are eligible</Text>
                  </View>
                )}

                {/* Actions */}
                <View style={styles.actionRow}>
                  <Button
                    title="View Details"
                    variant="outline"
                    size="sm"
                    onPress={() =>
                      navigation.navigate("SchemeDetail", { schemeId: scheme.id })
                    }
                    style={{ flex: 1 }}
                  />
                  <Button
                    title="Apply Now"
                    size="sm"
                    onPress={() =>
                      navigation.navigate("ApplicationForm", { schemeId: scheme.id })
                    }
                    style={{ flex: 1 }}
                  />
                </View>
              </Card>
            );
          })
        )}

        <View style={{ height: 24 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  title: { fontSize: 22, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  subtitle: { fontSize: 14, color: colors.gray[500], marginBottom: 16 },
  mb12: { marginBottom: 12 },
  mb16: { marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.gray[800] },
  pillScroll: { marginBottom: 16 },
  pillRow: { gap: 8, paddingVertical: 4 },
  pill: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.gray[300],
    backgroundColor: colors.white,
  },
  pillActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  pillText: { fontSize: 13, fontWeight: "600", color: colors.gray[600] },
  pillTextActive: { color: colors.white },
  emptyText: { textAlign: "center", color: colors.gray[500], paddingVertical: 40 },
  row: { flexDirection: "row", alignItems: "flex-start" },
  schemeIcon: {
    width: 40,
    height: 40,
    borderRadius: 8,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  schemeName: { fontSize: 14, fontWeight: "600", color: colors.gray[800], marginBottom: 2 },
  schemeDesc: { fontSize: 12, color: colors.gray[500], lineHeight: 17 },
  benefitBox: {
    backgroundColor: colors.gray[50],
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
  },
  benefitLabel: { fontSize: 10, fontWeight: "600", color: colors.gray[500], marginBottom: 4 },
  benefitValue: { fontSize: 18, fontWeight: "bold", color: colors.primary },
  eligibleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 10,
  },
  eligibleText: { fontSize: 12, color: colors.green[700] },
  actionRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 12,
  },
});
