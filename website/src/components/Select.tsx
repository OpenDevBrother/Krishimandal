import { colors } from "../constants/theme";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  options: SelectOption[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
}

export default function Select({
  label,
  options,
  value,
  onValueChange,
  placeholder = "Select...",
}: SelectProps) {
  return (
    <div className="mb-1">
      {label && (
        <label className="block text-sm font-semibold mb-1.5" style={{ color: colors.gray[700] }}>
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        className="w-full cursor-pointer"
        style={{
          backgroundColor: colors.gray[50],
          border: `1px solid ${colors.gray[200]}`,
          borderRadius: "8px",
          padding: "12px 14px",
          fontSize: "15px",
          color: value ? colors.gray[900] : colors.gray[400],
          outline: "none",
          appearance: "auto",
        }}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
