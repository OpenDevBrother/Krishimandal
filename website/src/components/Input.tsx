import { colors } from "../constants/theme";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement> {
  label?: string;
  error?: string;
  multiline?: boolean;
  numberOfLines?: number;
}

export default function Input({ label, error, multiline, numberOfLines, style, ...props }: InputProps) {
  const inputStyle: React.CSSProperties = {
    backgroundColor: colors.gray[50],
    border: `1px solid ${error ? colors.red[500] : colors.gray[200]}`,
    borderRadius: "8px",
    padding: "12px 14px",
    fontSize: "15px",
    color: colors.gray[900],
    width: "100%",
    outline: "none",
    ...(style as React.CSSProperties),
  };

  return (
    <div className="mb-1">
      {label && (
        <label className="block text-sm font-semibold mb-1.5" style={{ color: colors.gray[700] }}>
          {label}
        </label>
      )}
      {multiline ? (
        <textarea
          rows={numberOfLines || 3}
          style={inputStyle}
          {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
        />
      ) : (
        <input style={inputStyle} {...(props as React.InputHTMLAttributes<HTMLInputElement>)} />
      )}
      {error && (
        <p className="text-xs mt-1" style={{ color: colors.red[500] }}>
          {error}
        </p>
      )}
    </div>
  );
}
