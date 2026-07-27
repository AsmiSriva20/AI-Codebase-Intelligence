import { useState } from 'react';
import { buttonStyle, inputStyle, FONT } from '../constants/ui';
import { apiFetch } from '../api/client';
import Spinner from './Spinner';

export default function ChatDrawer({ onClose, activeTheme }) {
  const [chatQuery, setChatQuery] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hi! Ask me anything about this codebase.' },
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim() || chatLoading) return;

    const userMessage = chatQuery;
    setChatQuery('');
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const response = await apiFetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `Server error (${response.status})`);
      }

      const aiReply = data.answer || data.response || data.result || JSON.stringify(data);
      setChatMessages((prev) => [...prev, { role: 'assistant', content: aiReply }]);
    } catch (err) {
      console.error('Error asking LLM:', err);
      setChatMessages((prev) => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div style={{
      position: 'absolute',
      bottom: '16px',
      left: '16px',
      width: '360px',
      height: '460px',
      backgroundColor: activeTheme.surface,
      border: `1px solid ${activeTheme.border}`,
      borderRadius: '12px',
      boxShadow: activeTheme.shadowMd,
      zIndex: 100,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: FONT.sans,
    }}>
      <div style={{ padding: '12px 16px', backgroundColor: activeTheme.surfaceAlt, borderBottom: `1px solid ${activeTheme.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: '12.5px', color: activeTheme.text }}>Codebase AI Assistant</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: activeTheme.textMuted, cursor: 'pointer', fontSize: '14px' }}>✕</button>
      </div>

      <div style={{ flexGrow: 1, padding: '14px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {chatMessages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              padding: '8px 12px',
              borderRadius: '10px',
              backgroundColor: msg.role === 'user' ? activeTheme.accent : activeTheme.surfaceAlt,
              border: msg.role === 'user' ? 'none' : `1px solid ${activeTheme.border}`,
              color: msg.role === 'user' ? activeTheme.accentContrast : activeTheme.text,
              fontSize: '0.8rem',
              lineHeight: '1.45',
              whiteSpace: 'pre-wrap',
            }}
          >
            {msg.content}
          </div>
        ))}
        {chatLoading && (
          <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '7px', fontSize: '0.75rem', color: activeTheme.textFaint, fontStyle: 'italic' }}>
            <Spinner size={13} color={activeTheme.textFaint} />
            Searching vector DB &amp; generating response…
          </div>
        )}
      </div>

      <form onSubmit={handleSendChat} style={{ padding: '10px', borderTop: `1px solid ${activeTheme.border}`, display: 'flex', gap: '6px' }}>
        <input
          type="text"
          placeholder="Ask anything about the code…"
          value={chatQuery}
          onChange={(e) => setChatQuery(e.target.value)}
          style={inputStyle(activeTheme, { flexGrow: 1 })}
        />
        <button type="submit" disabled={chatLoading} style={buttonStyle(activeTheme, 'primary', { opacity: chatLoading ? 0.7 : 1, cursor: chatLoading ? 'wait' : 'pointer' })}>
          Send
        </button>
      </form>
    </div>
  );
}
