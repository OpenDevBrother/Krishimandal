import React, { ReactNode } from "react";
import { View, StyleSheet, ViewStyle } from "react-native";
import { colors } from "../constants/theme";

interface CardProps {
  children: ReactNode;
  style?: ViewStyle;
  borderLeftColor?: string;
}

export default function Card({ children, style, borderLeftColor }: CardProps) {
  return (
    <View
      style={[
        styles.card,
        borderLeftColor && { borderLeftWidth: 4, borderLeftColor },
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
});
