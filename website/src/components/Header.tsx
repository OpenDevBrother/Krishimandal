import { Leaf } from "lucide-react";
import { colors } from "../constants/theme";

export default function Header() {
  return (
    <div
      className="px-4 py-3 flex items-center gap-2.5"
      style={{ backgroundColor: colors.primary }}
    >
      <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
        <Leaf size={20} color={colors.white} />
      </div>
      <span className="text-xl font-bold text-white">KrishiMandal</span>
    </div>
  );
}
