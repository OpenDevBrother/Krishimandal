import type { ReactNode } from "react";
import { colors } from "../constants/theme";

interface ButtonProps {
  onPress?: () => void;
  onClick?: () => void;
  title?: string;
  children?: ReactNode;
  variant?: "primary" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  fullWidth?: boolean;
  style?: React.CSSProperties;
  textStyle?: React.CSSProperties;
}

export default function Button({
  onPress,
  onClick,
  title,
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  className = "",
  fullWidth = false,
  style,
}: ButtonProps) {
  const bg =
    variant === "primary"
      ? colors.primary
      : variant === "destructive"
      ? colors.red[600]
      : "transparent";

  const border =
    variant === "outline"
      ? `1px solid ${colors.gray[300]}`
      : "none";

  const textColor =
    variant === "primary" || variant === "destructive"
      ? colors.white
      : colors.primary;

  const padV = size === "sm" ? "8px" : size === "lg" ? "16px" : "12px";
  const padH = size === "sm" ? "12px" : size === "lg" ? "24px" : "16px";
  const fontSize = size === "sm" ? "13px" : size === "lg" ? "16px" : "14px";

  return (
    <button
      onClick={onPress || onClick}
      disabled={disabled || loading}
      className={`rounded-lg flex items-center justify-center font-semibold cursor-pointer transition-opacity hover:opacity-80 ${
        disabled || loading ? "opacity-50 cursor-not-allowed" : ""
      } ${fullWidth ? "w-full" : ""} ${className}`}
      style={{
        backgroundColor: bg,
        border,
        paddingTop: padV,
        paddingBottom: padV,
        paddingLeft: padH,
        paddingRight: padH,
        fontSize,
        color: textColor,
        ...style,
      }}
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : children ? (
        children
      ) : (
        title
      )}
    </button>
  );
}
