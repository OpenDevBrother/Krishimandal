import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import Toast from "react-native-toast-message";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Input from "../components/Input";
import Select from "../components/Select";
import Button from "../components/Button";
import { colors } from "../constants/theme";
import type { AddEditInventoryScreenProps } from "../navigation/types";

const CATEGORIES = [
  { value: "seed", label: "Seeds" },
  { value: "fertilizer", label: "Fertilizer" },
  { value: "pesticide", label: "Pesticides" },
  { value: "harvest", label: "Harvest Stock" },
  { value: "equipment", label: "Equipment" },
];

const UNITS = [
  { value: "kg", label: "Kilograms (kg)" },
  { value: "liters", label: "Liters" },
  { value: "bags", label: "Bags" },
  { value: "quintals", label: "Quintals" },
  { value: "pieces", label: "Pieces" },
];

export default function AddEditInventoryScreen({
  route,
  navigation,
}: AddEditInventoryScreenProps) {
  const itemId = route.params?.itemId;
  const isEdit = !!itemId;

  const [form, setForm] = useState({
    name: "",
    category: "seed",
    quantity: "",
    unit: "kg",
    threshold: "",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isEdit) {
      fetchItem();
    }
  }, [itemId]);

  const fetchItem = async () => {
    try {
      const path = await apiClient.farmPath(`/inventory/${itemId}`);
      const item = await apiClient.get<any>(path);
      setForm({
        name: item.name || "",
        category: item.category || "seed",
        quantity: item.quantity?.toString() || "",
        unit: item.unit || "kg",
        threshold: (item.threshold ?? item.alert_threshold ?? "")?.toString() || "",
      });
    } catch {
      // ignore
    }
  };

  const handleSubmit = async () => {
    if (!form.name || !form.quantity || !form.threshold) {
      Toast.show({ type: "error", text1: "Please fill all required fields" });
      return;
    }

    setLoading(true);
    try {
      if (isEdit) {
        const path = await apiClient.farmPath(`/inventory/${itemId}`);
        await apiClient.put(path, {
          name: form.name,
          category: form.category,
          quantity: parseFloat(form.quantity),
          unit: form.unit,
          alert_threshold: parseFloat(form.threshold),
        });
        Toast.show({ type: "success", text1: "Item updated successfully" });
      } else {
        const path = await apiClient.farmPath("/inventory");
        await apiClient.post(path, {
          name: form.name,
          category: form.category,
          quantity: parseFloat(form.quantity),
          unit: form.unit,
          alert_threshold: parseFloat(form.threshold),
        });
        Toast.show({ type: "success", text1: "Item added successfully" });
      }
      navigation.goBack();
    } catch (err: any) {
      Toast.show({ type: "error", text1: err.message || "Failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
    >
      <Card>
        <Text style={styles.cardTitle}>
          {isEdit ? "Edit" : "Add"} Inventory Item
        </Text>
        <Text style={styles.cardSubtitle}>
          {isEdit ? "Update" : "Add"} farm resource details
        </Text>

        <Input
          label="Item Name *"
          value={form.name}
          onChangeText={(t) => setForm({ ...form, name: t })}
          placeholder="e.g., Wheat Seeds, Urea Fertilizer"
        />

        <View style={{ marginTop: 12 }}>
          <Select
            label="Category *"
            options={CATEGORIES}
            value={form.category}
            onValueChange={(v) => setForm({ ...form, category: v })}
          />
        </View>

        <View style={styles.gridRow}>
          <View style={{ flex: 1 }}>
            <Input
              label="Quantity *"
              value={form.quantity}
              onChangeText={(t) => setForm({ ...form, quantity: t })}
              keyboardType="decimal-pad"
              placeholder="0.0"
            />
          </View>
          <View style={{ flex: 1 }}>
            <Select
              label="Unit *"
              options={UNITS}
              value={form.unit}
              onValueChange={(v) => setForm({ ...form, unit: v })}
            />
          </View>
        </View>

        <View style={{ marginTop: 12 }}>
          <Input
            label="Low Stock Threshold *"
            value={form.threshold}
            onChangeText={(t) => setForm({ ...form, threshold: t })}
            keyboardType="decimal-pad"
            placeholder="Alert when stock falls below this level"
          />
          <Text style={styles.helperText}>
            You'll receive an alert when stock falls below this level
          </Text>
        </View>

        <View style={styles.actionRow}>
          <Button
            title="Cancel"
            variant="outline"
            onPress={() => navigation.goBack()}
            style={{ flex: 1 }}
          />
          <Button
            title={isEdit ? "Update Item" : "Add Item"}
            onPress={handleSubmit}
            loading={loading}
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
  cardTitle: { fontSize: 18, fontWeight: "700", color: colors.gray[900], marginBottom: 4 },
  cardSubtitle: { fontSize: 13, color: colors.gray[500], marginBottom: 20 },
  gridRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 12,
  },
  helperText: { fontSize: 12, color: colors.gray[500], marginTop: 4 },
  actionRow: { flexDirection: "row", gap: 12, marginTop: 24 },
});
