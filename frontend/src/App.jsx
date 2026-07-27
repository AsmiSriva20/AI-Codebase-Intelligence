import { useState, useCallback, useEffect } from 'react';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import CodeHealthView from './components/CodeHealthView';
import ChatDrawer from './components/ChatDrawer';
import AppHeader from './components/AppHeader';
import ProjectSummaryModal from './components/ProjectSummaryModal';
import HomePage from './components/HomePage';
import Spinner from './components/Spinner';
import { THEMES, DEFAULT_THEME } from './constants/themes';
import { FONT } from './constants/ui';
import { apiFetch, API_BASE_URL } from './api/client';

function App() {
  const [themeKey, setThemeKey] = useState(DEFAULT_THEME);
  const [view, setView] = useState('graph');
  const [chatOpen, setChatOpen] = useState(false);
  const [focusFile, setFocusFile] = useState(null);

  // 'boot' (checking /status) -> 'home' (no repo loaded yet) -> 'dashboard'.
  const [screen, setScreen] = useState('boot');

  const [issuesReport, setIssuesReport] = useState(null);
  const [depReport, setDepReport] = useState(null);

  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const activeTheme = THEMES[themeKey];

  const [healthResetKey, setHealthResetKey] = useState(0);

  const refreshIssues = useCallback(async () => {
    setHealthResetKey((k) => k + 1);
    try {
      const [issuesRes, depRes] = await Promise.all([
        apiFetch('/issues'),
        apiFetch('/dependency-report'),
      ]);
      setIssuesReport(await issuesRes.json());
      setDepReport(await depRes.json());
    } catch (err) {
      console.error('Failed to load issues/dependency report:', err);
    }
  }, []);

  // Once on mount: ask the backend whether a repo is already loaded (e.g. this
  // is a page refresh, or the backend rehydrated its last build from Postgres
  // on restart) so returning users land straight on the dashboard instead of
  // seeing the import screen again.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch('/status');
        const data = await res.json();
        if (cancelled) return;
        if (data.repo_loaded) {
          setScreen('dashboard');
          refreshIssues();
        } else {
          setScreen('home');
        }
      } catch (err) {
        console.error('Failed to check backend status:', err);
        if (!cancelled) setScreen('home');
      }
    })();
    return () => { cancelled = true; };
  }, [refreshIssues]);

  const goToFileInGraph = useCallback((path) => {
    setFocusFile(path);
    setView('graph');
  }, []);

  const generateSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const res = await apiFetch('/summary');
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setSummaryText(data.summary);
    } catch (err) {
      setSummaryError(err.message === 'Failed to fetch'
        ? `Could not reach the backend at ${API_BASE_URL}. Is the server running?`
        : err.message);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const openSummary = useCallback(() => {
    setSummaryOpen(true);
    if (!summaryText && !summaryLoading) generateSummary();
  }, [summaryText, summaryLoading, generateSummary]);

  const handleRepoLoadedFromHome = useCallback(() => {
    setScreen('dashboard');
    refreshIssues();
  }, [refreshIssues]);

  const attentionCount = (issuesReport?.summary?.critical || 0)
    + (issuesReport?.summary?.high || 0)
    + (depReport?.vulnerable_count || 0);

  if (screen === 'boot') {
    return (
      <div style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: activeTheme.bg,
      }}>
        <Spinner size={22} color={activeTheme.textFaint} />
      </div>
    );
  }

  if (screen === 'home') {
    return (
      <div style={{ width: '100vw', height: '100vh', backgroundColor: activeTheme.bg }}>
        <HomePage
          activeTheme={activeTheme}
          themeKey={themeKey}
          setThemeKey={setThemeKey}
          onRepoLoaded={handleRepoLoadedFromHome}
        />
      </div>
    );
  }

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: activeTheme.bg,
      fontFamily: FONT.sans,
    }}>
      <AppHeader
        activeTheme={activeTheme}
        themeKey={themeKey}
        setThemeKey={setThemeKey}
        view={view}
        setView={setView}
        chatOpen={chatOpen}
        setChatOpen={setChatOpen}
        attentionCount={attentionCount}
        onOpenSummary={openSummary}
      />

      <div style={{ flexGrow: 1, minHeight: 0, position: 'relative' }}>
        {/* Both views stay mounted so switching tabs doesn't reset graph pan/zoom or health filters. */}
        <div style={{ display: view === 'graph' ? 'block' : 'none', width: '100%', height: '100%' }}>
          <ArchitectureDiagram
            activeTheme={activeTheme}
            issuesReport={issuesReport}
            focusFile={focusFile}
            onConsumeFocusFile={() => setFocusFile(null)}
            onRepositoryChanged={() => { refreshIssues(); setSummaryText(null); setSummaryError(null); }}
          />
        </div>
        <div style={{ display: view === 'health' ? 'block' : 'none', width: '100%', height: '100%', overflow: 'hidden' }}>
          <CodeHealthView
            activeTheme={activeTheme}
            issuesReport={issuesReport}
            depReport={depReport}
            onNavigateToFile={goToFileInGraph}
            onRefresh={refreshIssues}
            resetKey={healthResetKey}
          />
        </div>
      </div>

      {chatOpen && (
        <ChatDrawer onClose={() => setChatOpen(false)} activeTheme={activeTheme} />
      )}

      {summaryOpen && (
        <ProjectSummaryModal
          activeTheme={activeTheme}
          onClose={() => setSummaryOpen(false)}
          summary={summaryText}
          loading={summaryLoading}
          error={summaryError}
          onGenerate={generateSummary}
        />
      )}
    </div>
  );
}

export default App;
