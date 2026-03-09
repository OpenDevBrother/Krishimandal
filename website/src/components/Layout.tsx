import { useEffect, useState, type ReactNode } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Home, FileText, Package, Bell, User, BookOpen } from "lucide-react";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import Header from "./Header";
import Chatbot from "./Chatbot";
import DigitalTwinSidebar from "./DigitalTwinSidebar";
import VoiceAssistant from "./VoiceAssistant";

const NAV_ITEMS = [
  { path: "/", label: "Home", icon: Home },
  { path: "/schemes", label: "Schemes", icon: FileText },
  { path: "/learn", label: "Learn", icon: BookOpen },
  { path: "/inventory", label: "Inventory", icon: Package },
  { path: "/notifications", label: "Alerts", icon: Bell },
  { path: "/profile", label: "Profile", icon: User },
];

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnread = async () => {
    try {
      const path = apiClient.farmPath("/notifications/unread-count");
      const data = await apiClient.get<{ unread_count: number }>(path);
      setUnreadCount(data.unread_count);
    } catch {
      // ignore
    }
  };

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <div className="flex flex-1 flex-col md:flex-row">
        {/* Sidebar - desktop */}
        <nav className="hidden md:flex flex-col w-56 bg-white border-r border-gray-200 py-4">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex items-center gap-3 px-5 py-3 text-sm font-semibold transition-colors border-none cursor-pointer ${
                  active
                    ? "bg-[#E8F5E9] text-[#2D5F2E] border-r-3 border-[#2D5F2E]"
                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
                }`}
                style={active ? { borderRight: `3px solid ${colors.primary}`, backgroundColor: colors.primaryLight, color: colors.primary } : { background: "transparent" }}
              >
                <Icon size={20} />
                <span>{item.label}</span>
                {item.label === "Alerts" && unreadCount > 0 && (
                  <span className="ml-auto text-xs text-white rounded-full w-5 h-5 flex items-center justify-center" style={{ backgroundColor: colors.red[500] }}>
                    {unreadCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-auto pb-20 md:pb-4">
          {children}
        </main>

        {/* Bottom nav - mobile */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex justify-around py-2 z-50">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className="flex flex-col items-center gap-0.5 py-1 px-2 border-none cursor-pointer relative"
                style={{ background: "transparent", color: active ? colors.primary : colors.gray[400] }}
              >
                <Icon size={22} />
                <span className="text-[11px] font-semibold">{item.label}</span>
                {item.label === "Alerts" && unreadCount > 0 && (
                  <span
                    className="absolute -top-0.5 right-0 text-[10px] text-white rounded-full w-4 h-4 flex items-center justify-center"
                    style={{ backgroundColor: colors.red[500] }}
                  >
                    {unreadCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
      <VoiceAssistant />
      <Chatbot />
      <DigitalTwinSidebar />
    </div>
  );
}
