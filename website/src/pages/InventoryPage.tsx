import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Pencil, Trash2, AlertTriangle, TrendingUp, TrendingDown, Package } from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import Select from "../components/Select";
import { colors } from "../constants/theme";

interface InventoryItem {
  id: string; name: string; category: string; quantity: number;
  unit: string; threshold: number; last_updated?: string;
}

const CATEGORIES = [
  { value: "all", label: "All Items" }, { value: "seed", label: "Seeds" },
  { value: "fertilizer", label: "Fertilizer" }, { value: "pesticide", label: "Pesticides" },
  { value: "harvest", label: "Harvest Stock" }, { value: "equipment", label: "Equipment" },
];
const CAT_ICONS: Record<string, string> = { seed: "🌱", fertilizer: "🧪", pesticide: "🛡️", harvest: "🌾", equipment: "🔧" };
const CAT_COLORS: Record<string, { bg: string; text: string }> = {
  seed: { bg: colors.green[100], text: colors.green[700] },
  fertilizer: { bg: colors.blue[100], text: colors.blue[700] },
  pesticide: { bg: colors.red[100], text: colors.red[700] },
  harvest: { bg: colors.yellow[200], text: colors.amber[700] },
  equipment: { bg: colors.purple[100], text: colors.purple[700] },
};

export default function InventoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [filter, setFilter] = useState("all");
  const [showUpdateDialog, setShowUpdateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [updateMode, setUpdateMode] = useState<"add" | "deduct">("add");
  const [updateQty, setUpdateQty] = useState("");

  useEffect(() => { fetchInventory(); }, []);

  const fetchInventory = async () => {
    try {
      const data = await apiClient.get<any[]>(apiClient.farmPath("/inventory"));
      setItems(data.map((item) => ({
        id: String(item.id), name: item.name, category: item.category,
        quantity: item.quantity, unit: item.unit,
        threshold: item.threshold ?? item.alert_threshold ?? 0,
        last_updated: item.last_updated || item.updated_at,
      })));
    } catch { toast.error("Could not load inventory"); }
  };

  const filteredItems = filter === "all" ? items : items.filter((i) => i.category === filter);
  const lowStock = items.filter((i) => i.quantity <= i.threshold);

  const handleUpdateQuantity = async () => {
    if (!selectedItem || !updateQty) return;
    const amount = parseFloat(updateQty);
    if (isNaN(amount) || amount <= 0) return;
    try {
      await apiClient.post(apiClient.farmPath(`/inventory/${selectedItem.id}/adjust`), {
        adjustment: updateMode === "add" ? amount : -amount,
        reason: updateMode === "add" ? "Stock added" : "Stock deducted",
      });
      toast.success(updateMode === "add" ? "Stock added" : "Stock deducted");
      setShowUpdateDialog(false); setUpdateQty(""); fetchInventory();
    } catch (err: any) { toast.error(err.message || "Failed"); }
  };

  const handleDelete = async () => {
    if (!selectedItem) return;
    try {
      await apiClient.delete(apiClient.farmPath(`/inventory/${selectedItem.id}`));
      toast.success("Item deleted"); setShowDeleteDialog(false); fetchInventory();
    } catch (err: any) { toast.error(err.message || "Failed"); }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: colors.gray[900] }}>Inventory</h1>
          <p className="text-sm" style={{ color: colors.gray[500] }}>Track your farm resources</p>
        </div>
        <Button size="sm" onPress={() => navigate("/inventory/add")}>
          <div className="flex items-center gap-1.5"><Plus size={16} color={colors.white} /><span className="text-sm font-semibold text-white">Add Item</span></div>
        </Button>
      </div>

      {lowStock.length > 0 && (
        <Card borderLeftColor={colors.red[500]} className="mb-4" style={{ backgroundColor: colors.red[50] }}>
          <div className="flex items-center gap-2 mb-2.5">
            <AlertTriangle size={20} color={colors.red[600]} />
            <span className="text-sm font-bold" style={{ color: colors.red[900] }}>Low Stock Alert</span>
          </div>
          {lowStock.map((item) => (
            <div key={item.id} className="flex justify-between bg-white p-2 rounded-lg mb-1">
              <span className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{item.name}</span>
              <span className="text-xs" style={{ color: colors.red[600] }}>{item.quantity} {item.unit} left</span>
            </div>
          ))}
        </Card>
      )}

      <Card className="mb-4">
        <Select options={CATEGORIES} value={filter} onValueChange={setFilter} placeholder="Filter by category" />
      </Card>

      {filteredItems.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-10">
            <Package size={48} color={colors.gray[300]} />
            <p className="text-base font-semibold mt-3" style={{ color: colors.gray[700] }}>No Inventory Items</p>
            <p className="text-sm mt-1" style={{ color: colors.gray[500] }}>Start tracking by adding items.</p>
            <Button onPress={() => navigate("/inventory/add")} className="mt-3">
              <div className="flex items-center gap-1.5"><Plus size={16} color={colors.white} /><span className="text-sm font-semibold text-white">Add First Item</span></div>
            </Button>
          </div>
        </Card>
      ) : (
        filteredItems.map((item) => {
          const catColor = CAT_COLORS[item.category] || CAT_COLORS.seed;
          return (
            <Card key={item.id} className="mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg shrink-0" style={{ backgroundColor: colors.primaryLight }}>
                  {CAT_ICONS[item.category] || "📦"}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{item.name}</span>
                    {item.quantity <= item.threshold && <AlertTriangle size={16} color={colors.red[600]} />}
                  </div>
                  <Badge label={item.category} bgColor={catColor.bg} textColor={catColor.text} />
                </div>
              </div>
              <div className="flex gap-4 rounded-lg p-3 mt-3" style={{ backgroundColor: colors.gray[50] }}>
                <div className="flex-1">
                  <p className="text-[11px]" style={{ color: colors.gray[500] }}>Current Stock</p>
                  <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{item.quantity} {item.unit}</p>
                </div>
                <div className="flex-1">
                  <p className="text-[11px]" style={{ color: colors.gray[500] }}>Alert Threshold</p>
                  <p className="text-sm font-semibold" style={{ color: colors.gray[800] }}>{item.threshold} {item.unit}</p>
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <Button variant="outline" size="sm" onPress={() => { setSelectedItem(item); setUpdateMode("add"); setShowUpdateDialog(true); }} className="flex-1">
                  <div className="flex items-center gap-1"><TrendingUp size={14} color={colors.primary} /><span className="text-sm font-semibold" style={{ color: colors.primary }}>Add</span></div>
                </Button>
                <Button variant="outline" size="sm" onPress={() => { setSelectedItem(item); setUpdateMode("deduct"); setShowUpdateDialog(true); }} className="flex-1">
                  <div className="flex items-center gap-1"><TrendingDown size={14} color={colors.primary} /><span className="text-sm font-semibold" style={{ color: colors.primary }}>Deduct</span></div>
                </Button>
                <Button variant="outline" size="sm" onPress={() => navigate(`/inventory/edit/${item.id}`)}>
                  <Pencil size={16} color={colors.primary} />
                </Button>
                <Button variant="outline" size="sm" onPress={() => { setSelectedItem(item); setShowDeleteDialog(true); }}>
                  <Trash2 size={16} color={colors.red[600]} />
                </Button>
              </div>
              {item.last_updated && <p className="text-[11px] mt-2.5" style={{ color: colors.gray[400] }}>Last updated: {new Date(item.last_updated).toLocaleDateString()}</p>}
            </Card>
          );
        })
      )}

      {/* Update Quantity Modal */}
      {showUpdateDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50">
          <div className="bg-white rounded-xl p-5 w-full max-w-md">
            <h2 className="text-lg font-bold mb-1" style={{ color: colors.gray[900] }}>{updateMode === "add" ? "Add Stock" : "Deduct Stock"}</h2>
            <p className="text-sm mb-4" style={{ color: colors.gray[500] }}>{updateMode === "add" ? "Add quantity to the inventory" : "Deduct quantity from the inventory"}</p>
            <Input label="Item" value={selectedItem?.name || ""} readOnly />
            <Input label="Current Quantity" value={`${selectedItem?.quantity || 0} ${selectedItem?.unit || ""}`} readOnly />
            <Input label={`Amount to ${updateMode === "add" ? "Add" : "Deduct"}`} value={updateQty} onChange={(e) => setUpdateQty((e.target as HTMLInputElement).value)} type="number" placeholder={`Enter amount in ${selectedItem?.unit || ""}`} />
            <div className="flex gap-3 mt-4">
              <Button title="Cancel" variant="outline" onPress={() => { setShowUpdateDialog(false); setUpdateQty(""); }} className="flex-1" />
              <Button title={updateMode === "add" ? "Add" : "Deduct"} onPress={handleUpdateQuantity} className="flex-1" />
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50">
          <div className="bg-white rounded-xl p-5 w-full max-w-md">
            <h2 className="text-lg font-bold mb-1" style={{ color: colors.gray[900] }}>Delete Item</h2>
            <p className="text-sm mb-4" style={{ color: colors.gray[500] }}>Are you sure you want to delete "{selectedItem?.name}"? This action cannot be undone.</p>
            <div className="flex gap-3">
              <Button title="Cancel" variant="outline" onPress={() => setShowDeleteDialog(false)} className="flex-1" />
              <Button title="Delete" variant="destructive" onPress={handleDelete} className="flex-1" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
