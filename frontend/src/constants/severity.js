export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

export const SEVERITY_LABEL = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

export function severityColor(theme, severity) {
  if (severity === 'critical' || severity === 'high') return theme.danger;
  if (severity === 'medium') return theme.warning;
  return theme.textFaint;
}

export function severitySoft(theme, severity) {
  if (severity === 'critical' || severity === 'high') return theme.dangerSoft;
  if (severity === 'medium') return theme.warningSoft;
  return theme.surfaceAlt;
}

// Highest-priority severity in a findings array, or null if empty.
export function topSeverity(findings) {
  if (!findings || findings.length === 0) return null;
  let best = null;
  let bestRank = Infinity;
  for (const f of findings) {
    const rank = SEVERITY_ORDER.indexOf(f.severity);
    if (rank !== -1 && rank < bestRank) {
      bestRank = rank;
      best = f.severity;
    }
  }
  return best;
}
