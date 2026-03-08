import { useState, useEffect } from "react";
import { Bell, FileText, Package, TrendingUp, DollarSign, Calendar } from "lucide-react";
import toast from "react-hot-toast";
import { apiClient } from "../services/api";
import Card from "../components/Card";
import Badge from "../components/Badge";
import Button from "../components/Button";
import { colors } from "../constants/theme";

interface Notification { id: string; type: string; title: string; message: string; created_at?: string; read: boolean; }

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => { fetchNotifications(); }, []);

  const fetchNotifications = async () => {
    try {
      const data = await apiClient.get<any[]>(apiClient.farmPath("/notifications"));
      setNotifications(data.map((n: any) => ({ ...n, id: String(n.id), read: n.read ?? n.is_read ?? false })).filter((n) => !n.read));
    } catch { /* ignore */ }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: string) => {
    switch (type) {
      case "scheme": return <FileText size={20} color={colors.blue[600]} />;
      case "subsidy": return <DollarSign size={20} color={colors.green[600]} />;
      case "inventory": return <Package size={20} color={colors.orange[600]} />;
      case "crop": return <TrendingUp size={20} color={colors.purple[600]} />;
      case "application": return <Calendar size={20} color={colors.cyan[600]} />;
      default: return <Bell size={20} color={colors.gray[500]} />;
    }
  };

  const handleMarkAsRead = async (id: string) => {
    try {
      await apiClient.put(apiClient.farmPath(`/notifications/${id}/read`));
      fetchNotifications();
    } catch (err: any) { toast.error(err.message || "Failed"); }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.put(apiClient.farmPath("/notifications/read-all"));
      fetchNotifications();
      toast.success("All notifications marked as read");
    } catch (err: any) { toast.error(err.message || "Failed"); }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: colors.gray[900] }}>Notifications</h1>
          <p className="text-sm" style={{ color: colors.gray[500] }}>Stay updated with alerts and reminders</p>
        </div>
        {unreadCount > 0 && <Badge label={`${unreadCount} New`} bgColor={colors.red[500]} textColor={colors.white} />}
      </div>

      {unreadCount > 0 && (
        <div className="flex justify-end mb-3">
          <Button title="Mark All as Read" variant="ghost" size="sm" onPress={handleMarkAllRead} />
        </div>
      )}

      {notifications.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center py-10">
            <Bell size={48} color={colors.gray[300]} />
            <p className="text-base font-semibold mt-3" style={{ color: colors.gray[700] }}>No Notifications</p>
            <p className="text-sm mt-1" style={{ color: colors.gray[500] }}>You're all caught up! Check back later for updates.</p>
          </div>
        </Card>
      ) : (
        notifications.map((notif) => (
          <Card
            key={notif.id}
            borderLeftColor={!notif.read ? colors.primary : undefined}
            className={`mb-3 ${notif.read ? "opacity-70" : ""}`}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{getIcon(notif.type)}</div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-sm font-semibold flex-1 truncate" style={{ color: colors.gray[800] }}>{notif.title}</span>
                  {!notif.read && <Badge label="New" bgColor={colors.primary} textColor={colors.white} />}
                </div>
                <p className="text-sm mb-1.5" style={{ color: colors.gray[500] }}>{notif.message}</p>
                {notif.created_at && <p className="text-[11px]" style={{ color: colors.gray[400] }}>{new Date(notif.created_at).toLocaleString()}</p>}
                {!notif.read && <Button title="Mark as Read" variant="ghost" size="sm" onPress={() => handleMarkAsRead(notif.id)} className="mt-1.5" />}
              </div>
            </div>
          </Card>
        ))
      )}

      <Card className="mt-1" style={{ backgroundColor: colors.blue[50] }}>
        <div className="flex items-start gap-3">
          <Bell size={20} color={colors.blue[600]} />
          <div>
            <p className="text-sm font-semibold mb-1" style={{ color: colors.blue[900] }}>Notification Channels</p>
            <p className="text-xs leading-relaxed" style={{ color: colors.blue[700] }}>
              You'll receive alerts via in-app notifications, SMS, and WhatsApp for important updates like scheme deadlines, subsidy disbursements, and low inventory alerts.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
