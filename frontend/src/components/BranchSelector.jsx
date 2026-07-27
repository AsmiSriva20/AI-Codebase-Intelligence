import { useEffect, useState } from 'react';
import { GitBranch, ChevronDown } from 'lucide-react';
import { apiFetch } from '../api/client';
import { FONT } from '../constants/ui';
import Spinner from './Spinner';

export default function BranchSelector({ activeTheme, onBranchSwitched, refreshKey }) {
  const [branches, setBranches] = useState([]);
  const [current, setCurrent] = useState(null);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  const loadBranches = async () => {
    try {
      const res = await apiFetch('/branches');
      if (!res.ok) return;
      const data = await res.json();
      setBranches(data.branches || []);
      setCurrent(data.current || null);
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  };

  useEffect(() => {
    loadBranches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const handleSelect = async (name) => {
    setOpen(false);
    if (name === current || switching) return;
    setSwitching(true);
    try {
      const res = await apiFetch('/switch-branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setCurrent(name);
      await loadBranches();
      onBranchSwitched?.(name);
    } catch (err) {
      console.error('Failed to switch branch:', err);
    } finally {
      setSwitching(false);
    }
  };

  if (branches.length === 0) return null;

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={switching}
        title="Switch branch"
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '6px 10px', borderRadius: '7px',
          border: `1px solid ${activeTheme.border}`,
          background: activeTheme.surface,
          color: activeTheme.text,
          fontSize: '11.5px', fontFamily: FONT.mono, fontWeight: 600,
          cursor: switching ? 'default' : 'pointer',
          opacity: switching ? 0.6 : 1,
        }}
      >
        {switching ? <Spinner size={13} color={activeTheme.accent} /> : <GitBranch size={13} color={activeTheme.accent} />}
        {switching ? 'Switching…' : (current || '—')}
        <ChevronDown size={12} color={activeTheme.textFaint} />
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 20,
          minWidth: '180px', maxHeight: '260px', overflowY: 'auto',
          borderRadius: '8px', border: `1px solid ${activeTheme.border}`,
          background: activeTheme.surface, boxShadow: activeTheme.shadowMd,
        }}>
          {branches.map((b) => (
            <button
              key={b.name}
              onClick={() => handleSelect(b.name)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px',
                width: '100%', padding: '8px 10px', border: 'none',
                background: b.name === current ? activeTheme.surfaceAlt : 'transparent',
                color: activeTheme.text, fontSize: '12px', fontFamily: FONT.mono,
                cursor: 'pointer', textAlign: 'left',
              }}
            >
              <span>{b.name}</span>
              {!b.indexed_at && (
                <span style={{ fontSize: '9.5px', color: activeTheme.textFaint, fontFamily: FONT.sans }}>
                  not indexed
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
