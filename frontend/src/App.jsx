import { useState, useCallback } from 'react';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import CodeHealthView from './components/CodeHealthView';
import ChatDrawer from './components/ChatDrawer';
import AppHeader from './components/AppHeader';
import ProjectSummaryModal from './components/ProjectSummaryModal';
import HomePage from './components/HomePage';
import { THEMES, DEFAULT_THEME } from './constants/themes';
import { FONT } from './constants/ui';
import { apiFetch, API_BASE_URL } from './api/client';

function App() {
  const [themeKey, setThemeKey] = useState(DEFAULT_THEME);
  const [view, setView] = useState('graph');
  const [chatOpen, setChatOpen] = useState(false);
  const [focusFile, setFocusFile] = useState(null);

  // A saved backend repository does not mean this visitor chose to open it.
  const [screen, setScreen] = useState('home');

  const [issuesReport, setIssuesReport] = useState(null);
  const [depReport, setDepReport] = useState(null);
  const [architectureHealth, setArchitectureHealth] = useState(null);
  const [healthScore, setHealthScore] = useState(null);

  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const activeTheme = THEMES[themeKey];

  const [healthResetKey, setHealthResetKey] = useState(0);

  const refreshIssues = useCallback(async () => {
    setHealthResetKey((k) => k + 1);
    try {
      // These endpoints persist report fragments into the same branch row, so
      // request them in order rather than racing the first report creation.
      const issuesRes = await apiFetch('/issues');
      const depRes = await apiFetch('/dependency-report');
      const architectureHealthRes = await apiFetch('/architecture-health');
      const healthScoreRes = await apiFetch('/health-score');
      setIssuesReport(await issuesRes.json());
      setDepReport(await depRes.json());
      setArchitectureHealth(await architectureHealthRes.json());
      setHealthScore(await healthScoreRes.json());
    } catch (err) {
      console.error('Failed to load issues/dependency report:', err);
    }
  }, []);

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
    + (depReport?.vulnerable_count || 0)
    + (architectureHealth?.summary?.layer_violations || 0)
    + (architectureHealth?.summary?.circular_dependencies || 0);

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
            key={healthResetKey}
            activeTheme={activeTheme}
            issuesReport={issuesReport}
            depReport={depReport}
            architectureHealth={architectureHealth}
            healthScore={healthScore}
            onNavigateToFile={goToFileInGraph}
            onRefresh={refreshIssues}
          />
        </div>
      </div>

      {chatOpen && (
        <ChatDrawer
          onClose={() => setChatOpen(false)}
          activeTheme={activeTheme}
          onNavigateToFile={(path) => { goToFileInGraph(path); setChatOpen(false); }}
        />
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
