export const RADIUS = 8;
export const RADIUS_LG = 12;

export const FONT = {
  sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  mono: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
};

export function inputStyle(theme, extra = {}) {
  return {
    padding: '8px 12px',
    borderRadius: RADIUS,
    border: `1px solid ${theme.border}`,
    backgroundColor: theme.bg,
    color: theme.text,
    fontSize: '13px',
    fontFamily: FONT.sans,
    outline: 'none',
    ...extra,
  };
}

export function buttonStyle(theme, variant = 'secondary', extra = {}) {
  const base = {
    padding: '8px 14px',
    borderRadius: RADIUS,
    fontSize: '13px',
    fontWeight: 500,
    fontFamily: FONT.sans,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    lineHeight: 1,
    transition: 'background-color 0.15s ease, border-color 0.15s ease, opacity 0.15s ease, color 0.15s ease',
    whiteSpace: 'nowrap',
  };

  if (variant === 'primary') {
    return {
      ...base,
      backgroundColor: theme.accent,
      border: `1px solid ${theme.accent}`,
      color: theme.accentContrast,
      ...extra,
    };
  }

  if (variant === 'ghost') {
    return {
      ...base,
      backgroundColor: 'transparent',
      border: '1px solid transparent',
      color: theme.textMuted,
      ...extra,
    };
  }

  // secondary (default)
  return {
    ...base,
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    color: theme.text,
    ...extra,
  };
}

export function panelStyle(theme, extra = {}) {
  return {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: RADIUS_LG,
    ...extra,
  };
}

export function labelStyle(theme, extra = {}) {
  return {
    fontSize: '11px',
    fontWeight: 600,
    color: theme.textFaint,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    ...extra,
  };
}
