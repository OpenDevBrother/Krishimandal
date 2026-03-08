import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Input from "../components/Input";
import Select from "../components/Select";
import Button from "../components/Button";
import { colors } from "../constants/theme";

const CATEGORIES = [
  { value: "seed", label: "Seeds" }, { value: "fertilizer", label: "Fertilizer" },
  { value: "pesticide", label: "Pesticides" }, { value: "harvest", label: "Harvest Stock" },
  { value: "equipment", label: "Equipment" },
];
const UNITS = [
  { value: "kg", label: "Kilograms (kg)" }, { value: "liters", label: "Liters" },
  { value: "bags", label: "Bags" }, { value: "quintals", label: "Quintals" },
  { value: "pieces", label: "Pieces" },
];

export default function AddEditInventoryPage() {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const isEdit = !!itemId;
  const [form, setForm] = useState({ name: "", category: "seed", quantity: "", unit: "kg", threshold: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (isEdit) fetchItem(); }, [itemId]);

  const fetchItem = async () => {
    try {
      const item = await apiClient.get<any>(apiClient.farmPath(`/inventory/${itemId}`));
      setForm({
        name: item.name || "", category: item.category || "seed",
        quantity: item.quantity?.toString() || "", unit: item.unit || "kg",
        threshold: (item.threshold ?? item.alert_threshold ?? "")?.toString() || "",
      });
    } catch { /* ignore */ }
  };

  const handleSubmit = async () => {
    if (!form.name || !form.quantity || !form.threshold) {
      toast.error("Please fill all required fields"); return;
    }
    setLoading(true);
    try {
      const body = {
        name: form.name, category: form.category, quantity: parseFloat(form.quantity),
        unit: form.unit, alert_threshold: parseFloat(form.threshold),
      };
      if (isEdit) {
        await apiClient.put(apiClient.farmPath(`/inventory/${itemId}`), body);
        toast.success("Item updated successfully");
      } else {
        await apiClient.post(apiClient.farmPath("/inventory"), body);
        toast.success("Item added successfully");
      }
      navigate("/inventory");
    } catch (err: any) { toast.error(err.message || "Failed"); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <button onClick={() => navigate(-1)} className="text-sm font-semibold mb-4 border-none bg-transparent cursor-pointer" style={{ color: colors.primary }}>← Back</button>
      <Card>
        <h1 className="text-lg font-bold mb-1" style={{ color: colors.gray[900] }}>{isEdit ? "Edit" : "Add"} Inventory Item</h1>
        <p className="text-sm mb-5" style={{ color: colors.gray[500] }}>{isEdit ? "Update" : "Add"} farm resource details</p>

        <Input label="Item Name *" value={form.name} onChange={(e) => setForm({ ...form, name: (e.target as HTMLInputElement).value })} placeholder="e.g., Wheat Seeds, Urea Fertilizer" />
        <div className="mt-3"><Select label="Category *" options={CATEGORIES} value={form.category} onValueChange={(v) => setForm({ ...form, category: v })} /></div>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <Input label="Quantity *" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: (e.target as HTMLInputElement).value })} type="number" placeholder="0.0" />
          <Select label="Unit *" options={UNITS} value={form.unit} onValueChange={(v) => setForm({ ...form, unit: v })} />
        </div>
        <div className="mt-3">
          <Input label="Low Stock Threshold *" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: (e.target as HTMLInputElement).value })} type="number" placeholder="Alert when stock falls below this level" />
          <p className="text-xs mt-1" style={{ color: colors.gray[500] }}>You'll receive an alert when stock falls below this level</p>
        </div>
        <div className="flex gap-3 mt-6">
          <Button title="Cancel" variant="outline" onPress={() => navigate(-1)} className="flex-1" />
          <Button title={isEdit ? "Update Item" : "Add Item"} onPress={handleSubmit} loading={loading} className="flex-1" />
        </div>
      </Card>
    </div>
  );
}
