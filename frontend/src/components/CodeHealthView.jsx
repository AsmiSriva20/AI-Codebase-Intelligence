import { useMemo, useState } from 'react';
import {
  ShieldAlert, Search, ExternalLink, ChevronDown, ChevronRight,
  Lightbulb, PackageSearch, RefreshCw, FolderSearch,
} from 'lucide-react';
import { inputStyle, labelStyle, buttonStyle, FONT } from '../constants/ui';
import { SEVERITY_ORDER, SEVERITY_LABEL, severityColor, severitySoft } from '../constants/severity';

const RISK_WEIGHT = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
const CATEGORIES = ['all', 'security', 'quality'];

function riskScore(findings) {
  return findings.reduce((sum, f) => sum + (RISK_WEIGHT[f.severity] || 0), 0);
}

function StatCard({ theme, severity, count, active, onClick }) {
  const isTotal = severity === 'total';
  const color = isTotal ? theme.accent : severityColor(theme, severity);
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        padding: '12px 16px',
        borderRadius: '10px',
        minWidth: '92px',
        cursor: 'pointer',
        background: active ? severitySoft(theme, isTotal ? 'medium' : severity) : theme.surface,
        border: `1px solid ${active ? color : theme.border}`,
        textAlign: 'left',
      }}
    >
      <span style={{ fontSize: '22px', fontWeight: 800, color, fontFamily: FONT.mono, lineHeight: 1 }}>{count}</span>
      <span style={{ fontSize: '11px', fontWeight: 600, color: theme.textMuted, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
        {isTotal ? 'Total' : SEVERITY_LABEL[severity]}
      </span>
    </button>
  );
}

function SolutionBox({ theme, solution }) {
  if (!solution) return null;
  return (
    <div style={{
      display: 'flex',
      gap: '7px',
      marginTop: '6px',
      padding: '7px 10px',
      borderRadius: '6px',
      background: theme.successSoft,
      border: `1px solid ${theme.success}33`,
    }}>
      <Lightbulb size={13} color={theme.success} style={{ flexShrink: 0, marginTop: '1px' }} />
      <span style={{ fontSize: '11.5px', color: theme.text, lineHeight: 1.5 }}>{solution}</span>
    </div>
  );
}

function FindingRow({ theme, finding }) {
  return (
    <div style={{ display: 'flex', gap: '10px', padding: '10px 0', borderTop: `1px solid ${theme.border}` }}>
      <span style={{
        flexShrink: 0, width: '7px', height: '7px', borderRadius: '50%', marginTop: '6px',
        background: severityColor(theme, finding.severity),
      }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '12.5px', color: theme.text, fontWeight: 600 }}>{finding.message}</span>
          <span style={{ fontSize: '10.5px', color: theme.textFaint, fontFamily: FONT.mono, flexShrink: 0 }}>
            {finding.category} · L{finding.line}
          </span>
        </div>
        {finding.snippet && (
          <code style={{
            display: 'block', marginTop: '5px', fontSize: '11px', fontFamily: FONT.mono,
            color: theme.textMuted, background: theme.surfaceAlt, border: `1px solid ${theme.border}`,
            borderRadius: '5px', padding: '5px 7px', overflowX: 'auto', whiteSpace: 'pre',
          }}>
            {finding.snippet}
          </code>
        )}
        <SolutionBox theme={theme} solution={finding.solution} />
      </div>
    </div>
  );
}

function FileFindingsCard({ theme, path, findings, onNavigateToFile, defaultOpen }) {
  const [open, setOpen] = useState(!!defaultOpen);
  const worst = findings.reduce((acc, f) => {
    const rank = SEVERITY_ORDER.indexOf(f.severity);
    return rank < acc.rank ? { rank, severity: f.severity } : acc;
  }, { rank: Infinity, severity: 'info' }).severity;

  return (
    <div style={{
      borderRadius: '10px',
      border: `1px solid ${theme.border}`,
      background: theme.surface,
      marginBottom: '10px',
      overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '9px',
          padding: '11px 14px', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
        }}
      >
        {open ? <ChevronDown size={14} color={theme.textFaint} /> : <ChevronRight size={14} color={theme.textFaint} />}
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0, background: severityColor(theme, worst) }} />
        <span style={{
          flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          fontSize: '12.5px', fontFamily: FONT.mono, color: theme.text, fontWeight: 600,
        }}>
          {path}
        </span>
        <span style={{
          fontSize: '11px', color: theme.textMuted, flexShrink: 0, fontFamily: FONT.mono,
          background: theme.surfaceAlt, borderRadius: '5px', padding: '2px 7px',
        }}>
          {findings.length} finding{findings.length === 1 ? '' : 's'}
        </span>
        <span
          role="button"
          tabIndex={0}
          onClick={(e) => { e.stopPropagation(); onNavigateToFile(path); }}
          title="Open file in Architecture Graph"
          style={{ color: theme.accent, flexShrink: 0, display: 'flex', cursor: 'pointer' }}
        >
          <ExternalLink size={14} />
        </span>
      </button>
      {open && (
        <div style={{ padding: '0 14px 12px 31px' }}>
          {findings.map((f, i) => <FindingRow key={i} theme={theme} finding={f} />)}
        </div>
      )}
    </div>
  );
}

function DependencyCard({ theme, dep }) {
  const vulnerable = dep.vulnerability_ids?.length > 0;
  return (
    <div style={{
      borderRadius: '10px',
      border: `1px solid ${vulnerable ? theme.danger + '55' : theme.border}`,
      background: theme.surface,
      padding: '11px 14px',
      marginBottom: '8px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '9px', flexWrap: 'wrap' }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0, background: vulnerable ? theme.danger : theme.success }} />
        <span style={{ fontSize: '12.5px', fontFamily: FONT.mono, color: theme.text, fontWeight: 600 }}>{dep.name}</span>
        <span style={{ fontSize: '11px', color: theme.textFaint, fontFamily: FONT.mono }}>{dep.version || '—'}</span>
        <span style={{ fontSize: '10px', color: theme.textFaint, marginLeft: 'auto' }}>{dep.ecosystem}</span>
      </div>
      {vulnerable && (
        <>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
            {dep.vulnerability_ids.map((id) => (
              <a
                key={id}
                href={`https://osv.dev/vulnerability/${encodeURIComponent(id)}`}
                target="_blank"
                rel="noreferrer"
                style={{
                  fontSize: '10.5px', fontWeight: 700, color: theme.danger, background: theme.dangerSoft,
                  borderRadius: '5px', padding: '2px 7px', textDecoration: 'none',
                  display: 'inline-flex', alignItems: 'center', gap: '3px',
                }}
              >
                {id} <ExternalLink size={9} />
              </a>
            ))}
          </div>
          <SolutionBox theme={theme} solution={dep.solution} />
        </>
      )}
    </div>
  );
}

export default function CodeHealthView({ activeTheme: theme, issuesReport, depReport, onNavigateToFile, onRefresh }) {
  const [tab, setTab] = useState('code');
  const [severityFilter, setSeverityFilter] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [search, setSearch] = useState('');

  const summary = issuesReport?.summary || {};
  const totalFindings = issuesReport?.total_findings ?? 0;
  const totalFiles = issuesReport?.total_files_scanned ?? 0;
  const dependencies = depReport?.dependencies || [];
  const vulnerableDeps = dependencies.filter((d) => d.vulnerability_ids?.length > 0);
  const otherDeps = dependencies.filter((d) => !(d.vulnerability_ids?.length > 0));

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase();
    const byFile = issuesReport?.by_file || {};
    const groups = Object.entries(byFile)
      .map(([path, findings]) => {
        const filtered = findings.filter((f) => {
          if (severityFilter && f.severity !== severityFilter) return false;
          if (categoryFilter !== 'all' && f.category !== categoryFilter) return false;
          if (q && !(path.toLowerCase().includes(q) || f.message.toLowerCase().includes(q))) return false;
          return true;
        });
        return { path, findings: filtered };
      })
      .filter((g) => g.findings.length > 0);

    groups.sort((a, b) => riskScore(b.findings) - riskScore(a.findings));
    return groups;
  }, [issuesReport, severityFilter, categoryFilter, search]);

  const hasRepo = totalFiles > 0;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      overflowY: 'auto',
      backgroundColor: theme.bg,
      fontFamily: FONT.sans,
      color: theme.text,
    }}>
      <div style={{ maxWidth: '980px', margin: '0 auto', padding: '28px 24px 60px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px', fontWeight: 700 }}>
              <ShieldAlert size={19} color={theme.danger} />
              Code Health &amp; Security
            </h2>
            <p style={{ fontSize: '12.5px', color: theme.textMuted, marginTop: '4px' }}>
              {hasRepo
                ? `${totalFiles} files scanned · ${totalFindings} findings · ${dependencies.length} dependencies`
                : 'Import a repository from the Architecture Graph tab to run a scan.'}
            </p>
          </div>
          {onRefresh && (
            <button onClick={onRefresh} style={buttonStyle(theme, 'secondary')}>
              <RefreshCw size={13} />
              Re-scan
            </button>
          )}
        </div>

        {!hasRepo ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px',
            padding: '60px 20px', color: theme.textMuted, border: `1px dashed ${theme.border}`, borderRadius: '12px',
          }}>
            <FolderSearch size={28} color={theme.textFaint} />
            <p style={{ fontSize: '13px' }}>Nothing to analyze yet.</p>
          </div>
        ) : (
          <>
            {/* Stat cards */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
              <StatCard theme={theme} severity="total" count={totalFindings} active={severityFilter === null} onClick={() => setSeverityFilter(null)} />
              {SEVERITY_ORDER.map((sev) => (
                <StatCard
                  key={sev}
                  theme={theme}
                  severity={sev}
                  count={summary[sev] || 0}
                  active={severityFilter === sev}
                  onClick={() => setSeverityFilter(severityFilter === sev ? null : sev)}
                />
              ))}
            </div>

            {/* Sub-tabs */}
            <div style={{ display: 'flex', borderBottom: `1px solid ${theme.border}`, marginBottom: '16px' }}>
              {[
                { key: 'code', label: `Code Findings (${totalFindings})` },
                { key: 'deps', label: `Dependencies (${depReport?.vulnerable_count ?? 0} vulnerable)` },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  style={{
                    padding: '9px 16px', border: 'none', background: 'transparent',
                    color: tab === t.key ? theme.accent : theme.textMuted,
                    fontWeight: 600, fontSize: '12.5px', fontFamily: FONT.sans, cursor: 'pointer',
                    borderBottom: tab === t.key ? `2px solid ${theme.accent}` : '2px solid transparent',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === 'code' && (
              <>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
                  <div style={{ position: 'relative', flexGrow: 1, minWidth: '220px' }}>
                    <Search size={14} color={theme.textFaint} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
                    <input
                      type="text"
                      placeholder="Search by file or message…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      style={inputStyle(theme, { width: '100%', paddingLeft: '30px' })}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '4px', padding: '3px', borderRadius: '8px', background: theme.surfaceAlt, border: `1px solid ${theme.border}` }}>
                    {CATEGORIES.map((c) => (
                      <button
                        key={c}
                        onClick={() => setCategoryFilter(c)}
                        style={{
                          padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                          background: categoryFilter === c ? theme.surface : 'transparent',
                          color: categoryFilter === c ? theme.text : theme.textMuted,
                          fontSize: '11.5px', fontWeight: 600, fontFamily: FONT.sans, textTransform: 'capitalize',
                        }}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredGroups.length === 0 ? (
                  <p style={{ fontSize: '12.5px', color: theme.textMuted, padding: '20px 4px' }}>
                    No findings match the current filters.
                  </p>
                ) : (
                  <div>
                    {filteredGroups.map((g, i) => (
                      <FileFindingsCard
                        key={g.path}
                        theme={theme}
                        path={g.path}
                        findings={g.findings}
                        onNavigateToFile={onNavigateToFile}
                        defaultOpen={i === 0}
                      />
                    ))}
                  </div>
                )}
              </>
            )}

            {tab === 'deps' && (
              <>
                {depReport?.manifests?.length > 0 && (
                  <p style={{ fontSize: '11.5px', color: theme.textFaint, marginBottom: '14px' }}>
                    Parsed from {depReport.manifests.join(', ')}
                  </p>
                )}
                {dependencies.length === 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: theme.textMuted, fontSize: '12.5px', padding: '20px 4px' }}>
                    <PackageSearch size={16} />
                    No dependency manifest found in this repository.
                  </div>
                ) : (
                  <>
                    {vulnerableDeps.length > 0 && (
                      <>
                        <span style={labelStyle(theme)}>Vulnerable</span>
                        <div style={{ marginTop: '8px', marginBottom: '18px' }}>
                          {vulnerableDeps.map((d, i) => <DependencyCard key={i} theme={theme} dep={d} />)}
                        </div>
                      </>
                    )}
                    <span style={labelStyle(theme)}>All dependencies</span>
                    <div style={{ marginTop: '8px' }}>
                      {otherDeps.map((d, i) => <DependencyCard key={i} theme={theme} dep={d} />)}
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
