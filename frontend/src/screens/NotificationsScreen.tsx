import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import {
  Bell,
  FileText,
  Package,
  TrendingUp,
  DollarSign,
  Calendar,
  AlertTriangle,
} from "lucide-react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Header from "../components/Header";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  created_at?: string;
  read: boolean;
}

interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  alert_threshold?: number;
  threshold?: number;
}

export default function NotificationsScreen() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [lowStockItems, setLowStockItems] = useState<InventoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNotifications = async () => {
    try {
      const path = await apiClient.farmPath("/notifications");
      const data = await apiClient.get<any[]>(path);
      const mapped = data.map((n: any) => ({
        ...n,
        id: String(n.id),
        read: n.read ?? n.is_read ?? false,
      }));
      setNotifications(mapped.filter((n) => !n.read));
    } catch {
      // ignore
    }
  };

  const fetchLowStock = async () => {
    try {
      const path = await apiClient.farmPath("/inventory");
      const data = await apiClient.get<InventoryItem[]>(path);
      const low = data.filter((item) => {
        const threshold = item.alert_threshold ?? item.threshold ?? 0;
        return threshold > 0 && item.quantity <= threshold;
      });
      setLowStockItems(low);
    } catch {
      // ignore
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchNotifications();
      fetchLowStock();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchNotifications(), fetchLowStock()]);
    setRefreshing(false);
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: string) => {
    switch (type) {
      case "scheme":
      case "scheme_deadline":
        return <FileText size={20} color={colors.blue[600]} />;
      case "subsidy":
        return <DollarSign size={20} color={colors.green[600]} />;
      case "inventory":
      case "inventory_alert":
        return <Package size={20} color={colors.orange[600]} />;
      case "crop":
      case "pest_warning":
        return <TrendingUp size={20} color={colors.purple[600]} />;
      case "application":
      case "application_update":
        return <Calendar size={20} color={colors.cyan[600]} />;
      default:
        return <Bell size={20} color={colors.gray[500]} />;
    }
  };

  const handleMarkAsRead = async (id: string) => {
    try {
      const path = await apiClient.farmPath(`/notifications/${id}/read`);
      await apiClient.put(path);
      fetchNotifications();
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed" });
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const path = await apiClient.farmPath("/notifications/read-all");
      await apiClient.put(path);
      fetchNotifications();
      Toast.show({ type: "success", text1: "All notifications marked as read" });
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed" });
    }
  };

  const totalAlerts = unreadCount + lowStockItems.length;

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
        {/* Header */}
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Notifications</Text>
            <Text style={styles.subtitle}>
              Stay updated with alerts and reminders
            </Text>
          </View>
          {totalAlerts > 0 && (
            <Badge
              label={`${totalAlerts} New`}
              bgColor={colors.red[500]}
              textColor={colors.white}
            />
          )}
        </View>

        {unreadCount > 0 && (
          <Button
            title="Mark All as Read"
            variant="ghost"
            size="sm"
            onPress={handleMarkAllRead}
            style={{ alignSelf: "flex-end", marginBottom: 12 }}
          />
        )}

        {/* Low Stock Alerts */}
        {lowStockItems.length > 0 && (
          <Card
            borderLeftColor={colors.red[500]}
            style={styles.mb12}
          >
            <View style={styles.lowStockHeader}>
              <AlertTriangle size={20} color={colors.red[600]} />
              <Text style={styles.lowStockTitle}>Low Stock Alert</Text>
              <Badge
                label={`${lowStockItems.length}`}
                bgColor={colors.red[500]}
                textColor={colors.white}
                textStyle={{ fontSize: 10 }}
              />
            </View>
            <Text style={styles.lowStockSubtitle}>
              The following items are running low and need restocking:
            </Text>
            {lowStockItems.map((item) => (
              <View key={item.id} style={styles.lowStockRow}>
                <Package size={16} color={colors.orange[600]} />
                <View style={styles.lowStockInfo}>
                  <Text style={styles.lowStockName}>{item.name}</Text>
                  <Text style={styles.lowStockCategory}>
                    {item.category}
                  </Text>
                </View>
                <View style={styles.lowStockQty}>
                  <Text style={styles.lowStockQtyText}>
                    {item.quantity} {item.unit}
                  </Text>
                  <Text style={styles.lowStockThreshold}>
                    min: {item.alert_threshold ?? item.threshold} {item.unit}
                  </Text>
                </View>
              </View>
            ))}
          </Card>
        )}

        {/* Notifications */}
        {notifications.length === 0 && lowStockItems.length === 0 ? (
          <Card>
            <View style={styles.emptyBox}>
              <Bell size={48} color={colors.gray[300]} />
              <Text style={styles.emptyTitle}>No Notifications</Text>
              <Text style={styles.emptySubtitle}>
                You're all caught up! Check back later for updates.
              </Text>
            </View>
          </Card>
        ) : (
          notifications.map((notif) => (
            <Card
              key={notif.id}
              borderLeftColor={!notif.read ? colors.primary : undefined}
              style={{ ...styles.mb12, ...(notif.read ? { opacity: 0.7 } : {}) }}
            >
              <View style={styles.notifRow}>
                <View style={{ marginTop: 2 }}>{getIcon(notif.type)}</View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <View style={styles.notifHeader}>
                    <Text style={styles.notifTitle} numberOfLines={1}>
                      {notif.title}
                    </Text>
                    {!notif.read && (
                      <Badge
                        label="New"
                        bgColor={colors.primary}
                        textColor={colors.white}
                        textStyle={{ fontSize: 10 }}
                      />
                    )}
                  </View>
                  <Text style={styles.notifMessage}>{notif.message}</Text>
                  {notif.created_at && (
                    <Text style={styles.notifDate}>
                      {new Date(notif.created_at).toLocaleString()}
                    </Text>
                  )}
                  {!notif.read && (
                    <Button
                      title="Mark as Read"
                      variant="ghost"
                      size="sm"
                      onPress={() => handleMarkAsRead(notif.id)}
                      style={{ alignSelf: "flex-start", marginTop: 6 }}
                      textStyle={{ fontSize: 12 }}
                    />
                  )}
                </View>
              </View>
            </Card>
          ))
        )}

        {/* Info Card */}
        <Card style={{ backgroundColor: colors.blue[50], marginTop: 4 }}>
          <View style={styles.notifRow}>
            <Bell size={20} color={colors.blue[600]} />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.infoTitle}>Notification Channels</Text>
              <Text style={styles.infoText}>
                You'll receive alerts via in-app notifications, SMS, and
                WhatsApp for important updates like scheme deadlines, subsidy
                disbursements, and low inventory alerts.
              </Text>
            </View>
          </View>
        </Card>

        <View style={{ height: 24 }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.gray[50] },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  title: { fontSize: 22, fontWeight: "700", color: colors.gray[900], marginBottom: 2 },
  subtitle: { fontSize: 14, color: colors.gray[500] },
  mb12: { marginBottom: 12 },
  // Low stock
  lowStockHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  lowStockTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.red[700],
    flex: 1,
  },
  lowStockSubtitle: {
    fontSize: 12,
    color: colors.gray[500],
    marginBottom: 10,
  },
  lowStockRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.gray[100],
  },
  lowStockInfo: { flex: 1 },
  lowStockName: { fontSize: 14, fontWeight: "600", color: colors.gray[800] },
  lowStockCategory: { fontSize: 11, color: colors.gray[400], textTransform: "capitalize" },
  lowStockQty: { alignItems: "flex-end" },
  lowStockQtyText: { fontSize: 14, fontWeight: "700", color: colors.red[600] },
  lowStockThreshold: { fontSize: 10, color: colors.gray[400] },
  // Empty
  emptyBox: { alignItems: "center", paddingVertical: 40 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: colors.gray[700], marginTop: 12 },
  emptySubtitle: { fontSize: 13, color: colors.gray[500], marginTop: 4 },
  // Notification
  notifRow: { flexDirection: "row", alignItems: "flex-start" },
  notifHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  notifTitle: { fontSize: 14, fontWeight: "600", color: colors.gray[800], flex: 1 },
  notifMessage: { fontSize: 13, color: colors.gray[500], marginBottom: 6 },
  notifDate: { fontSize: 11, color: colors.gray[400] },
  infoTitle: { fontSize: 14, fontWeight: "600", color: colors.blue[900], marginBottom: 4 },
  infoText: { fontSize: 12, color: colors.blue[700], lineHeight: 18 },
});
