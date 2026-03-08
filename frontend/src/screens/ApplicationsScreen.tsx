import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import {
  FileText,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  FileEdit,
} from "lucide-react-native";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";
import type { ApplicationsScreenProps } from "../navigation/types";

interface Application {
  id: string;
  scheme_id?: string;
  scheme_name?: string;
  status: string;
  submitted_date?: string;
  created_at?: string;
}

const FILTERS = ["all", "draft", "submitted", "under_review", "approved"];

export default function ApplicationsScreen({
  navigation,
}: ApplicationsScreenProps) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [filter, setFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  const fetchApplications = async () => {
    try {
      const path = await apiClient.farmPath("/applications");
      const data = await apiClient.get<Application[]>(path);
      setApplications(data);
    } catch {
      // ignore
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchApplications();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchApplications();
    setRefreshing(false);
  };

  const filtered =
    filter === "all"
      ? applications
      : applications.filter((a) => a.status === filter);

  const counts = {
    all: applications.length,
    draft: applications.filter((a) => a.status === "draft").length,
    submitted: applications.filter((a) => a.status === "submitted").length,
    under_review: applications.filter((a) => a.status === "under_review").length,
    approved: applications.filter((a) => a.status === "approved").length,
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "approved":
        return <CheckCircle size={20} color={colors.green[600]} />;
      case "rejected":
        return <XCircle size={20} color={colors.red[600]} />;
      case "under_review":
        return <Clock size={20} color={colors.blue[600]} />;
      case "submitted":
        return <FileText size={20} color={colors.purple[600]} />;
      default:
        return <FileEdit size={20} color={colors.gray[500]} />;
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
      case "approved":
        return "Your application has been approved! Benefits will be disbursed soon.";
      case "rejected":
        return "Your application was rejected. Please review the eligibility criteria.";
      case "under_review":
        return "Your application is under review. You will be notified once a decision is made.";
      case "submitted":
        return "Your application has been submitted successfully.";
      default:
        return "This application is saved as a draft. Complete and submit it.";
    }
  };

  const getStatusMsgBg = (status: string) => {
    switch (status) {
      case "approved":
        return { bg: colors.green[50], text: colors.green[700] };
      case "rejected":
        return { bg: colors.red[50], text: colors.red[700] };
      case "under_review":
        return { bg: colors.blue[50], text: colors.blue[700] };
      case "submitted":
        return { bg: colors.purple[50], text: colors.purple[700] };
      default:
        return { bg: colors.gray[100], text: colors.gray[700] };
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[colors.primary]} />
      }
    >
      <Text style={styles.title}>My Applications</Text>
      <Text style={styles.subtitle}>Track your scheme application status</Text>

      {/* Filter pills */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.pillScroll}
        contentContainerStyle={styles.pillRow}
      >
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f}
            onPress={() => setFilter(f)}
            style={[styles.pill, filter === f && styles.pillActive]}
            activeOpacity={0.7}
          >
            <Text
              style={[styles.pillText, filter === f && styles.pillTextActive]}
            >
              {f.replace("_", " ").charAt(0).toUpperCase() +
                f.replace("_", " ").slice(1)}{" "}
              ({(counts as any)[f] || 0})
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {filtered.length === 0 ? (
        <Card>
          <View style={styles.emptyBox}>
            <FileText size={48} color={colors.gray[300]} />
            <Text style={styles.emptyTitle}>No Applications Found</Text>
            <Text style={styles.emptySubtitle}>
              You haven't applied for any schemes yet.
            </Text>
            <Button
              title="Browse Schemes"
              onPress={() => navigation.navigate("MainTabs", { screen: "Schemes" })}
              style={{ marginTop: 12 }}
            />
          </View>
        </Card>
      ) : (
        filtered.map((app) => {
          const badgeC =
            statusBadgeColors[app.status] || statusBadgeColors.draft;
          const msgStyle = getStatusMsgBg(app.status);

          return (
            <Card key={app.id} style={styles.mb12}>
              <View style={styles.row}>
                <View style={{ marginRight: 10, marginTop: 2 }}>
                  {getStatusIcon(app.status)}
                </View>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <Text style={styles.appName}>
                    {app.scheme_name || `Application ${app.id}`}
                  </Text>
                  {(app.submitted_date || app.created_at) && (
                    <View style={styles.dateRow}>
                      <Calendar size={12} color={colors.gray[400]} />
                      <Text style={styles.dateText}>
                        {new Date(
                          app.submitted_date || app.created_at!
                        ).toLocaleDateString()}
                      </Text>
                    </View>
                  )}
                </View>
                <Badge
                  label={app.status.replace("_", " ").toUpperCase()}
                  bgColor={badgeC.bg}
                  textColor={badgeC.text}
                />
              </View>

              {/* Status message */}
              <View
                style={[
                  styles.statusMsg,
                  { backgroundColor: msgStyle.bg },
                ]}
              >
                <Text style={[styles.statusMsgText, { color: msgStyle.text }]}>
                  {getStatusMessage(app.status)}
                </Text>
              </View>

              {/* Actions */}
              <View style={styles.actionRow}>
                {app.status === "draft" && app.scheme_id && (
                  <Button
                    title="Continue Application"
                    size="sm"
                    onPress={() =>
                      navigation.navigate("ApplicationForm", {
                        schemeId: app.scheme_id!,
                      })
                    }
                    style={{ flex: 1 }}
                  />
                )}
                <Button
                  title="Download PDF"
                  variant="outline"
                  size="sm"
                  onPress={() => {}}
                  style={app.status === "draft" ? { flex: 1 } : { width: "100%" }}
                />
              </View>
            </Card>
          );
        })
      )}

      <View style={{ height: 24 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  scrollContent: { padding: 16 },
  title: { fontSize: 22, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  subtitle: { fontSize: 14, color: colors.gray[500], marginBottom: 16 },
  mb12: { marginBottom: 12 },
  pillScroll: { marginBottom: 16 },
  pillRow: { gap: 8, paddingVertical: 4 },
  pill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.gray[300],
    backgroundColor: colors.white,
  },
  pillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  pillText: { fontSize: 12, fontWeight: "600", color: colors.gray[600] },
  pillTextActive: { color: colors.white },
  emptyBox: { alignItems: "center", paddingVertical: 40 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: colors.gray[700], marginTop: 12 },
  emptySubtitle: { fontSize: 13, color: colors.gray[500], marginTop: 4 },
  row: { flexDirection: "row", alignItems: "flex-start" },
  appName: { fontSize: 14, fontWeight: "600", color: colors.gray[800], marginBottom: 4 },
  dateRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  dateText: { fontSize: 12, color: colors.gray[500] },
  statusMsg: { borderRadius: 8, padding: 12, marginTop: 12 },
  statusMsgText: { fontSize: 12 },
  actionRow: { flexDirection: "row", gap: 8, marginTop: 12 },
});
