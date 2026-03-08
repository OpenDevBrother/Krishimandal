interface BadgeProps {
  label: string;
  bgColor: string;
  textColor: string;
  className?: string;
  textClassName?: string;
}

export default function Badge({ label, bgColor, textColor, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-block px-2.5 py-1 rounded-xl text-xs font-semibold ${className}`}
      style={{ backgroundColor: bgColor, color: textColor }}
    >
      {label}
    </span>
  );
}
