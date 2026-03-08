import React, { ReactNode } from "react";
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from "react-native";
import { colors } from "../constants/theme";

interface ButtonProps {
  onPress: () => void;
  title?: string;
  children?: ReactNode;
  variant?: "primary" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  fullWidth?: boolean;
}

export default function Button({
  onPress,
  title,
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  style,
  textStyle,
  fullWidth = false,
}: ButtonProps) {
  const bg =
    variant === "primary"
      ? colors.primary
      : variant === "destructive"
      ? colors.red[600]
      : variant === "outline"
      ? "transparent"
      : "transparent";

  const border =
    variant === "outline"
      ? { borderWidth: 1, borderColor: colors.gray[300] }
      : {};

  const textColor =
    variant === "primary" || variant === "destructive"
      ? colors.white
      : colors.primary;

  const padV = size === "sm" ? 8 : size === "lg" ? 16 : 12;
  const padH = size === "sm" ? 12 : size === "lg" ? 24 : 16;
  const fontSize = size === "sm" ? 13 : size === "lg" ? 16 : 14;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.button,
        { backgroundColor: bg, paddingVertical: padV, paddingHorizontal: padH },
        border,
        (disabled || loading) && styles.disabled,
        fullWidth && { width: "100%" },
        style,
      ]}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator size="small" color={textColor} />
      ) : children ? (
        children
      ) : (
        <Text
          style={[styles.text, { color: textColor, fontSize }, textStyle]}
        >
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  text: {
    fontWeight: "600",
  },
  disabled: {
    opacity: 0.5,
  },
});
