import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  borderLeftColor?: string;
  style?: React.CSSProperties;
}

export default function Card({ children, className = "", borderLeftColor, style }: CardProps) {
  return (
    <div
      className={`bg-white rounded-xl p-4 shadow-sm ${className}`}
      style={{
        ...(borderLeftColor ? { borderLeft: `4px solid ${borderLeftColor}` } : {}),
        ...style,
      }}
    >
      {children}
    </div>
  );
}
