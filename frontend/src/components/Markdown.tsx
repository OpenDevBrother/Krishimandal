import React from "react";
import { StyleSheet, Linking } from "react-native";
import MarkdownDisplay from "react-native-markdown-display";
import { colors } from "../constants/theme";

interface MarkdownProps {
  children: string;
  fontSize?: number;
  color?: string;
}

/**
 * Pre-processes raw text to handle common LaTeX/math patterns
 * before passing to the markdown renderer.
 */
function preprocessText(text: string): string {
  let result = text;

  // Strip LaTeX display math blocks: \[ ... \] → plain text
  result = result.replace(/\\\[(.+?)\\\]/gs, (_, inner) => {
    return cleanLatex(inner);
  });

  // Strip LaTeX inline math: \( ... \) → plain text
  result = result.replace(/\\\((.+?)\\\)/g, (_, inner) => {
    return cleanLatex(inner);
  });

  // Strip $$ ... $$ display math
  result = result.replace(/\$\$(.+?)\$\$/gs, (_, inner) => {
    return cleanLatex(inner);
  });

  // Strip $ ... $ inline math
  result = result.replace(/\$(.+?)\$/g, (_, inner) => {
    return cleanLatex(inner);
  });

  return result;
}

/**
 * Converts common LaTeX math into readable plain text.
 */
function cleanLatex(tex: string): string {
  let s = tex.trim();

  // \text{...} → content
  s = s.replace(/\\text\{([^}]*)\}/g, "$1");
  // \textbf{...} → **content**
  s = s.replace(/\\textbf\{([^}]*)\}/g, "**$1**");
  // \textit{...} → _content_
  s = s.replace(/\\textit\{([^}]*)\}/g, "_$1_");
  // \mathbf{...} → content
  s = s.replace(/\\mathbf\{([^}]*)\}/g, "$1");

  // Fractions: \frac{a}{b} → a/b
  s = s.replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, "$1/$2");

  // Superscript: x^{2} → x^2, x^2 → x^2
  s = s.replace(/\^{([^}]*)}/g, "^$1");

  // Subscript: x_{i} → x_i
  s = s.replace(/_{([^}]*)}/g, "_$1");

  // \sqrt{x} → sqrt(x)
  s = s.replace(/\\sqrt\{([^}]*)\}/g, "sqrt($1)");

  // \times → x
  s = s.replace(/\\times/g, "x");

  // \cdot → .
  s = s.replace(/\\cdot/g, ".");

  // \pm → +/-
  s = s.replace(/\\pm/g, "+/-");

  // \approx → ~
  s = s.replace(/\\approx/g, "~");

  // \leq, \geq, \neq
  s = s.replace(/\\leq/g, "<=");
  s = s.replace(/\\geq/g, ">=");
  s = s.replace(/\\neq/g, "!=");

  // \% → %
  s = s.replace(/\\%/g, "%");

  // Common units/symbols
  s = s.replace(/\\degree/g, "°");
  s = s.replace(/\\circ/g, "°");
  s = s.replace(/\\infty/g, "infinity");

  // Greek letters
  s = s.replace(/\\alpha/g, "alpha");
  s = s.replace(/\\beta/g, "beta");
  s = s.replace(/\\gamma/g, "gamma");
  s = s.replace(/\\delta/g, "delta");
  s = s.replace(/\\mu/g, "mu");
  s = s.replace(/\\sigma/g, "sigma");
  s = s.replace(/\\pi/g, "pi");

  // \left, \right — just remove
  s = s.replace(/\\left/g, "");
  s = s.replace(/\\right/g, "");

  // \, \; \! \quad — spacing → single space
  s = s.replace(/\\[,;!]\s*/g, " ");
  s = s.replace(/\\quad/g, " ");

  // Remove remaining backslash commands: \xxx → xxx
  s = s.replace(/\\([a-zA-Z]+)/g, "$1");

  // Clean up braces
  s = s.replace(/[{}]/g, "");

  // Collapse whitespace
  s = s.replace(/\s+/g, " ").trim();

  return s;
}

export default function Markdown({
  children,
  fontSize = 13,
  color = colors.gray[800],
}: MarkdownProps) {
  const processed = preprocessText(children || "");

  const mdStyles = StyleSheet.create({
    body: { fontSize, color, lineHeight: fontSize * 1.5 },
    paragraph: { marginTop: 0, marginBottom: 6 },
    strong: { fontWeight: "700" },
    em: { fontStyle: "italic" },
    heading1: { fontSize: fontSize + 3, fontWeight: "bold", marginTop: 8, marginBottom: 4, color: colors.gray[900] },
    heading2: { fontSize: fontSize + 2, fontWeight: "bold", marginTop: 6, marginBottom: 4, color: colors.gray[900] },
    heading3: { fontSize: fontSize + 1, fontWeight: "600", marginTop: 4, marginBottom: 2, color: colors.gray[900] },
    bullet_list: { marginTop: 0, marginBottom: 6 },
    ordered_list: { marginTop: 0, marginBottom: 6 },
    list_item: { marginBottom: 2 },
    code_inline: {
      fontSize: fontSize - 1,
      backgroundColor: colors.gray[100],
      color: colors.gray[700],
      paddingHorizontal: 4,
      paddingVertical: 1,
      borderRadius: 3,
    },
    fence: {
      fontSize: fontSize - 1,
      backgroundColor: colors.gray[100],
      color: colors.gray[700],
      padding: 8,
      borderRadius: 6,
      marginVertical: 4,
    },
    link: { color: colors.primary, textDecorationLine: "underline" as const },
    blockquote: {
      backgroundColor: colors.gray[50],
      borderLeftWidth: 3,
      borderLeftColor: colors.primary,
      paddingLeft: 10,
      paddingVertical: 4,
      marginVertical: 4,
    },
    hr: { backgroundColor: colors.gray[200], height: 1, marginVertical: 8 },
    table: { borderWidth: 1, borderColor: colors.gray[200], borderRadius: 4 },
    th: { padding: 6, backgroundColor: colors.gray[50] },
    td: { padding: 6 },
    tr: { borderBottomWidth: 1, borderColor: colors.gray[200] },
  });

  return (
    <MarkdownDisplay
      style={mdStyles}
      onLinkPress={(url: string) => {
        Linking.openURL(url);
        return false;
      }}
    >
      {processed}
    </MarkdownDisplay>
  );
}
