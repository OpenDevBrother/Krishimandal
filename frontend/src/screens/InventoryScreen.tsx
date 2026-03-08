import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Modal,
  RefreshControl,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import {
  Plus,
  Pencil,
  Trash2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Package,
} from "lucide-react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Header from "../components/Header";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import Select from "../components/Select";
import { colors } from "../constants/theme";
import type { InventoryScreenProps } from "../navigation/types";

interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  threshold: number;
  alert_threshold?: number;
  last_updated?: string;
  updated_at?: string;
}

const CATEGORIES = [
  { value: "all", label: "All Items" },
  { value: "seed", label: "Seeds" },
  { value: "fertilizer", label: "Fertilizer" },
  { value: "pesticide", label: "Pesticides" },
  { value: "harvest", label: "Harvest Stock" },
  { value: "equipment", label: "Equipment" },
];

const CAT_ICONS: Record<string, string> = {
  seed: "\u{1F331}",
  fertilizer: "\u{1F9EA}",
  pesticide: "\u{1F6E1}\uFE0F",
  harvest: "\u{1F33E}",
  equipment: "\u{1F527}",
};

const CAT_COLORS: Record<string, { bg: string; text: string }> = {
  seed: { bg: colors.green[100], text: colors.green[700] },
  fertilizer: { bg: colors.blue[100], text: colors.blue[700] },
  pesticide: { bg: colors.red[100], text: colors.red[700] },
  harvest: { bg: colors.yellow[200], text: colors.amber[700] },
  equipment: { bg: colors.purple[100], text: colors.purple[700] },
};

export default function InventoryScreen({ navigation }: InventoryScreenProps) {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [filter, setFilter] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  // Dialog state
  const [showUpdateDialog, setShowUpdateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [updateMode, setUpdateMode] = useState<"add" | "deduct">("add");
  const [updateQty, setUpdateQty] = useState("");

  const fetchInventory = async () => {
    try {
      const path = await apiClient.farmPath("/inventory");
      const data = await apiClient.get<any[]>(path);
      const mapped: InventoryItem[] = data.map((item) => ({
        id: String(item.id),
        name: item.name,
        category: item.category,
        quantity: item.quantity,
        unit: item.unit,
        threshold: item.threshold ?? item.alert_threshold ?? 0,
        last_updated: item.last_updated || item.updated_at,
      }));
      setItems(mapped);
    } catch {
      Toast.show({ type: "error", text1: "Could not load inventory" });
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchInventory();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchInventory();
    setRefreshing(false);
  };

  const filteredItems =
    filter === "all" ? items : items.filter((i) => i.category === filter);

  const lowStock = items.filter((i) => i.quantity <= i.threshold);

  const handleUpdateQuantity = async () => {
    if (!selectedItem || !updateQty) return;
    const amount = parseFloat(updateQty);
    if (isNaN(amount) || amount <= 0) return;

    try {
      const path = await apiClient.farmPath(
        `/inventory/${selectedItem.id}/adjust`
      );
      await apiClient.post(path, {
        adjustment: updateMode === "add" ? amount : -amount,
        reason: updateMode === "add" ? "Stock added" : "Stock deducted",
      });
      Toast.show({
        type: "success",
        text1: updateMode === "add" ? "Stock added" : "Stock deducted",
      });
      setShowUpdateDialog(false);
      setUpdateQty("");
      fetchInventory();
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed" });
    }
  };

  const handleDelete = async () => {
    if (!selectedItem) return;
    try {
      const path = await apiClient.farmPath(
        `/inventory/${selectedItem.id}`
      );
      await apiClient.delete(path);
      Toast.show({ type: "success", text1: "Item deleted" });
      setShowDeleteDialog(false);
      fetchInventory();
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed" });
    }
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
        {/* Header */}
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Inventory</Text>
            <Text style={styles.subtitle}>Track your farm resources</Text>
          </View>
          <Button
            size="sm"
            onPress={() => navigation.navigate("AddEditInventory", {})}
          >
            <View style={styles.addRow}>
              <Plus size={16} color={colors.white} />
              <Text style={styles.addText}>Add Item</Text>
            </View>
          </Button>
        </View>

        {/* Low Stock Alerts */}
        {lowStock.length > 0 && (
          <Card
            borderLeftColor={colors.red[500]}
            style={{ ...styles.mb16, backgroundColor: colors.red[50] }}
          >
            <View style={styles.alertHeader}>
              <AlertTriangle size={20} color={colors.red[600]} />
              <Text style={styles.alertTitle}>Low Stock Alert</Text>
            </View>
            {lowStock.map((item) => (
              <View key={item.id} style={styles.alertRow}>
                <Text style={styles.alertName}>{item.name}</Text>
                <Text style={styles.alertQty}>
                  {item.quantity} {item.unit} left
                </Text>
              </View>
            ))}
          </Card>
        )}

        {/* Filter */}
        <Card style={styles.mb16}>
          <Select
            options={CATEGORIES}
            value={filter}
            onValueChange={setFilter}
            placeholder="Filter by category"
          />
        </Card>

        {/* Items */}
        {filteredItems.length === 0 ? (
          <Card>
            <View style={styles.emptyBox}>
              <Package size={48} color={colors.gray[300]} />
              <Text style={styles.emptyTitle}>No Inventory Items</Text>
              <Text style={styles.emptySubtitle}>
                Start tracking by adding items.
              </Text>
              <Button
                title="Add First Item"
                onPress={() => navigation.navigate("AddEditInventory", {})}
                style={{ marginTop: 12 }}
              >
                <View style={styles.addRow}>
                  <Plus size={16} color={colors.white} />
                  <Text style={styles.addText}>Add First Item</Text>
                </View>
              </Button>
            </View>
          </Card>
        ) : (
          filteredItems.map((item) => {
            const catColor = CAT_COLORS[item.category] || CAT_COLORS.seeds;
            return (
              <Card key={item.id} style={styles.mb12}>
                {/* Item header */}
                <View style={styles.row}>
                  <View style={[styles.catIcon, { backgroundColor: colors.primaryLight }]}>
                    <Text style={{ fontSize: 18 }}>
                      {CAT_ICONS[item.category] || "\u{1F4E6}"}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <View style={styles.nameRow}>
                      <Text style={styles.itemName}>{item.name}</Text>
                      {item.quantity <= item.threshold && (
                        <AlertTriangle size={16} color={colors.red[600]} />
                      )}
                    </View>
                    <Badge
                      label={item.category}
                      bgColor={catColor.bg}
                      textColor={catColor.text}
                    />
                  </View>
                </View>

                {/* Stock info */}
                <View style={styles.stockRow}>
                  <View style={styles.stockCol}>
                    <Text style={styles.stockLabel}>Current Stock</Text>
                    <Text style={styles.stockValue}>
                      {item.quantity} {item.unit}
                    </Text>
                  </View>
                  <View style={styles.stockCol}>
                    <Text style={styles.stockLabel}>Alert Threshold</Text>
                    <Text style={styles.stockValue}>
                      {item.threshold} {item.unit}
                    </Text>
                  </View>
                </View>

                {/* Actions */}
                <View style={styles.actionRow}>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={() => {
                      setSelectedItem(item);
                      setUpdateMode("add");
                      setShowUpdateDialog(true);
                    }}
                    style={{ flex: 1 }}
                  >
                    <View style={styles.btnInner}>
                      <TrendingUp size={14} color={colors.primary} />
                      <Text style={styles.btnText}>Add</Text>
                    </View>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={() => {
                      setSelectedItem(item);
                      setUpdateMode("deduct");
                      setShowUpdateDialog(true);
                    }}
                    style={{ flex: 1 }}
                  >
                    <View style={styles.btnInner}>
                      <TrendingDown size={14} color={colors.primary} />
                      <Text style={styles.btnText}>Deduct</Text>
                    </View>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={() =>
                      navigation.navigate("AddEditInventory", {
                        itemId: item.id,
                      })
                    }
                  >
                    <Pencil size={16} color={colors.primary} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={() => {
                      setSelectedItem(item);
                      setShowDeleteDialog(true);
                    }}
                  >
                    <Trash2 size={16} color={colors.red[600]} />
                  </Button>
                </View>

                {item.last_updated && (
                  <Text style={styles.lastUpdated}>
                    Last updated:{" "}
                    {new Date(item.last_updated).toLocaleDateString()}
                  </Text>
                )}
              </Card>
            );
          })
        )}

        <View style={{ height: 24 }} />
      </ScrollView>

      {/* Update Quantity Dialog */}
      <Modal visible={showUpdateDialog} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {updateMode === "add" ? "Add Stock" : "Deduct Stock"}
            </Text>
            <Text style={styles.modalSubtitle}>
              {updateMode === "add"
                ? "Add quantity to the inventory"
                : "Deduct quantity from the inventory"}
            </Text>
            <Input
              label="Item"
              value={selectedItem?.name || ""}
              editable={false}
            />
            <Input
              label="Current Quantity"
              value={`${selectedItem?.quantity || 0} ${selectedItem?.unit || ""}`}
              editable={false}
            />
            <Input
              label={`Amount to ${updateMode === "add" ? "Add" : "Deduct"}`}
              value={updateQty}
              onChangeText={setUpdateQty}
              keyboardType="decimal-pad"
              placeholder={`Enter amount in ${selectedItem?.unit || ""}`}
            />
            <View style={styles.modalActions}>
              <Button
                title="Cancel"
                variant="outline"
                onPress={() => {
                  setShowUpdateDialog(false);
                  setUpdateQty("");
                }}
                style={{ flex: 1 }}
              />
              <Button
                title={updateMode === "add" ? "Add" : "Deduct"}
                onPress={handleUpdateQuantity}
                style={{ flex: 1 }}
              />
            </View>
          </View>
        </View>
      </Modal>

      {/* Delete Dialog */}
      <Modal visible={showDeleteDialog} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Delete Item</Text>
            <Text style={styles.modalSubtitle}>
              Are you sure you want to delete "{selectedItem?.name}"? This
              action cannot be undone.
            </Text>
            <View style={styles.modalActions}>
              <Button
                title="Cancel"
                variant="outline"
                onPress={() => setShowDeleteDialog(false)}
                style={{ flex: 1 }}
              />
              <Button
                title="Delete"
                variant="destructive"
                onPress={handleDelete}
                style={{ flex: 1 }}
              />
            </View>
          </View>
        </View>
      </Modal>
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
  mb16: { marginBottom: 16 },
  addRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  addText: { fontSize: 13, fontWeight: "600", color: colors.white },
  alertHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  alertTitle: { fontSize: 15, fontWeight: "700", color: colors.red[900] },
  alertRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.white,
    padding: 8,
    borderRadius: 8,
    marginBottom: 4,
  },
  alertName: { fontSize: 14, fontWeight: "600", color: colors.gray[800] },
  alertQty: { fontSize: 12, color: colors.red[600] },
  emptyBox: { alignItems: "center", paddingVertical: 40 },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.gray[700],
    marginTop: 12,
  },
  emptySubtitle: { fontSize: 13, color: colors.gray[500], marginTop: 4 },
  row: { flexDirection: "row", alignItems: "center" },
  catIcon: {
    width: 40,
    height: 40,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  nameRow: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  itemName: { fontSize: 14, fontWeight: "600", color: colors.gray[800] },
  stockRow: {
    flexDirection: "row",
    backgroundColor: colors.gray[50],
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
    gap: 16,
  },
  stockCol: { flex: 1 },
  stockLabel: { fontSize: 11, color: colors.gray[500], marginBottom: 2 },
  stockValue: { fontSize: 15, fontWeight: "600", color: colors.gray[800] },
  actionRow: { flexDirection: "row", gap: 8, marginTop: 12 },
  btnInner: { flexDirection: "row", alignItems: "center", gap: 4 },
  btnText: { fontSize: 13, fontWeight: "600", color: colors.primary },
  lastUpdated: { fontSize: 11, color: colors.gray[400], marginTop: 10 },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    padding: 24,
  },
  modalContent: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 20,
  },
  modalTitle: { fontSize: 18, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  modalSubtitle: { fontSize: 13, color: colors.gray[500], marginBottom: 16 },
  modalActions: { flexDirection: "row", gap: 12, marginTop: 16 },
});
