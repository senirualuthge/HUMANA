/**
 * AI Digital Human Avatar Widget
 * Embed on any website with:
 *   <script src="https://cdn.yourdomain.com/avatar.js" data-api-key="YOUR_API_KEY"></script>
 *
 * The widget connects to the backend WebSocket for streaming AI responses,
 * logs events, and can perform DOM actions based on AI instructions.
 */
(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────────────────────
  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const API_KEY = currentScript.getAttribute('data-api-key');
  const BACKEND_URL = currentScript.getAttribute('data-backend-url') || 'https://api.yourdomain.com';
  const WS_URL = BACKEND_URL.replace(/^http/, 'ws') + '/chat?apiKey=' + API_KEY;
  const EVENTS_URL = BACKEND_URL + '/events';
  const AVATAR_NAME = currentScript.getAttribute('data-avatar-name') || 'Aria';
  const AVATAR_COLOR = currentScript.getAttribute('data-avatar-color') || '#6C63FF';

  if (!API_KEY) {
    console.error('[AvatarWidget] Missing data-api-key attribute.');
    return;
  }

  // ─── State ────────────────────────────────────────────────────────────────────
  let ws = null;
  let isOpen = false;
  let isTyping = false;
  let reconnectTimer = null;

  // ─── Styles ───────────────────────────────────────────────────────────────────
  const styles = `
    #aw-launcher {
      position: fixed; bottom: 24px; right: 24px;
      width: 60px; height: 60px; border-radius: 50%;
      background: ${AVATAR_COLOR}; color: #fff;
      font-size: 28px; display: flex; align-items: center; justify-content: center;
      cursor: pointer; box-shadow: 0 8px 32px rgba(0,0,0,0.22);
      z-index: 999998; transition: transform 0.2s, box-shadow 0.2s;
      border: none; outline: none;
    }
    #aw-launcher:hover { transform: scale(1.08); box-shadow: 0 12px 36px rgba(0,0,0,0.28); }

    #aw-widget {
      position: fixed; bottom: 96px; right: 24px;
      width: 360px; max-height: 560px;
      display: flex; flex-direction: column;
      background: #fff; border-radius: 18px;
      box-shadow: 0 16px 56px rgba(0,0,0,0.2);
      z-index: 999999; overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      opacity: 0; pointer-events: none; transform: translateY(24px);
      transition: opacity 0.25s, transform 0.25s;
    }
    #aw-widget.aw-open { opacity: 1; pointer-events: all; transform: translateY(0); }

    #aw-header {
      background: ${AVATAR_COLOR}; color: #fff;
      padding: 16px 20px; display: flex; align-items: center; gap: 12px;
    }
    #aw-avatar-icon {
      width: 38px; height: 38px; border-radius: 50%;
      background: rgba(255,255,255,0.25);
      display: flex; align-items: center; justify-content: center; font-size: 20px;
    }
    #aw-header-info { flex: 1; }
    #aw-header-name { font-weight: 700; font-size: 15px; }
    #aw-header-status { font-size: 12px; opacity: 0.85; margin-top: 2px; }
    #aw-close-btn {
      background: rgba(255,255,255,0.18); border: none; color: #fff;
      width: 30px; height: 30px; border-radius: 50%; cursor: pointer; font-size: 18px;
      display: flex; align-items: center; justify-content: center;
    }

    #aw-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 10px;
      scroll-behavior: smooth;
    }
    .aw-msg {
      max-width: 85%; padding: 10px 14px; border-radius: 14px;
      font-size: 14px; line-height: 1.5; animation: awFadeIn 0.2s ease;
    }
    .aw-msg.aw-user {
      background: ${AVATAR_COLOR}; color: #fff;
      align-self: flex-end; border-bottom-right-radius: 4px;
    }
    .aw-msg.aw-bot {
      background: #f1f1f1; color: #222;
      align-self: flex-start; border-bottom-left-radius: 4px;
    }
    .aw-msg.aw-typing { opacity: 0.7; }

    #aw-input-row {
      display: flex; padding: 12px 14px; gap: 8px; border-top: 1px solid #f0f0f0;
    }
    #aw-input {
      flex: 1; border: 1px solid #e0e0e0; border-radius: 24px;
      padding: 10px 16px; font-size: 14px; outline: none;
      transition: border-color 0.2s;
    }
    #aw-input:focus { border-color: ${AVATAR_COLOR}; }
    #aw-send-btn {
      background: ${AVATAR_COLOR}; color: #fff; border: none;
      border-radius: 50%; width: 40px; height: 40px;
      cursor: pointer; font-size: 18px;
      display: flex; align-items: center; justify-content: center;
      transition: opacity 0.2s;
    }
    #aw-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    @keyframes awFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  `;

  // ─── DOM Construction ─────────────────────────────────────────────────────────
  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = styles;
    document.head.appendChild(style);
  }

  function buildWidget() {
    const launcher = document.createElement('button');
    launcher.id = 'aw-launcher';
    launcher.setAttribute('aria-label', 'Open AI Assistant');
    launcher.innerHTML = '🤖';

    const widget = document.createElement('div');
    widget.id = 'aw-widget';
    widget.setAttribute('role', 'dialog');
    widget.setAttribute('aria-label', `${AVATAR_NAME} AI Chat`);
    widget.innerHTML = `
      <div id="aw-header">
        <div id="aw-avatar-icon">🤖</div>
        <div id="aw-header-info">
          <div id="aw-header-name">${AVATAR_NAME}</div>
          <div id="aw-header-status">Online · Ready to help</div>
        </div>
        <button id="aw-close-btn" aria-label="Close chat">✕</button>
      </div>
      <div id="aw-messages" aria-live="polite"></div>
      <div id="aw-input-row">
        <input id="aw-input" type="text" placeholder="Type a message…" aria-label="Chat message" autocomplete="off" />
        <button id="aw-send-btn" aria-label="Send message">➤</button>
      </div>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(widget);

    // Events
    launcher.addEventListener('click', toggleWidget);
    widget.querySelector('#aw-close-btn').addEventListener('click', closeWidget);
    widget.querySelector('#aw-send-btn').addEventListener('click', sendMessage);
    widget.querySelector('#aw-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
  }

  // ─── Widget State Management ──────────────────────────────────────────────────
  function toggleWidget() {
    isOpen ? closeWidget() : openWidget();
  }

  function openWidget() {
    isOpen = true;
    document.getElementById('aw-widget').classList.add('aw-open');
    document.getElementById('aw-input').focus();
    document.getElementById('aw-launcher').innerHTML = '✕';
    connectWS();
    logEvent('widget_open');

    // Show welcome message if empty
    const msgs = document.getElementById('aw-messages');
    if (!msgs.children.length) {
      appendMessage('bot', `Hi! I'm ${AVATAR_NAME}. How can I help you today? 👋`);
    }
  }

  function closeWidget() {
    isOpen = false;
    document.getElementById('aw-widget').classList.remove('aw-open');
    document.getElementById('aw-launcher').innerHTML = '🤖';
    logEvent('widget_close');
  }

  // ─── WebSocket Connection ─────────────────────────────────────────────────────
  function connectWS() {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;

    clearTimeout(reconnectTimer);
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      document.getElementById('aw-header-status').textContent = 'Online · Ready to help';
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
      } catch (e) {
        console.warn('[AvatarWidget] Could not parse WS message', e);
      }
    };

    ws.onerror = () => {
      document.getElementById('aw-header-status').textContent = 'Reconnecting…';
    };

    ws.onclose = () => {
      if (isOpen) {
        reconnectTimer = setTimeout(connectWS, 3000);
      }
    };
  }

  function handleWSMessage(msg) {
    if (msg.type === 'status' && msg.content === 'typing') {
      showTypingIndicator();
    } else if (msg.type === 'chunk') {
      appendChunkToLatestBotMessage(msg.content);
    } else if (msg.type === 'done') {
      removeTypingIndicator();
      enableInput();
      executeDomActions(msg.domActions);
    } else if (msg.type === 'error') {
      removeTypingIndicator();
      appendMessage('bot', '⚠️ Sorry, something went wrong. Please try again.');
      enableInput();
    }
  }

  // ─── Chat UI Helpers ──────────────────────────────────────────────────────────
  let currentBotBubble = null;

  function sendMessage() {
    const input = document.getElementById('aw-input');
    const text = input.value.trim();
    if (!text || isTyping) return;

    appendMessage('user', text);
    input.value = '';
    disableInput();
    currentBotBubble = null;
    logEvent('message_sent', { messageLength: text.length });

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'chat', content: text }));
    } else {
      appendMessage('bot', '⚠️ Connection lost. Reconnecting…');
      enableInput();
      connectWS();
    }
  }

  function appendMessage(role, text) {
    const msgs = document.getElementById('aw-messages');
    const bubble = document.createElement('div');
    bubble.className = `aw-msg aw-${role}`;
    bubble.textContent = text;
    msgs.appendChild(bubble);
    msgs.scrollTop = msgs.scrollHeight;
    if (role === 'bot') currentBotBubble = bubble;
    return bubble;
  }

  function appendChunkToLatestBotMessage(chunk) {
    if (!currentBotBubble) {
      removeTypingIndicator();
      currentBotBubble = appendMessage('bot', '');
    }
    currentBotBubble.textContent += chunk;
    const msgs = document.getElementById('aw-messages');
    msgs.scrollTop = msgs.scrollHeight;
  }

  function showTypingIndicator() {
    isTyping = true;
    if (!document.getElementById('aw-typing')) {
      const msgs = document.getElementById('aw-messages');
      const bubble = document.createElement('div');
      bubble.id = 'aw-typing';
      bubble.className = 'aw-msg aw-bot aw-typing';
      bubble.textContent = '● ● ●';
      msgs.appendChild(bubble);
      msgs.scrollTop = msgs.scrollHeight;
    }
  }

  function removeTypingIndicator() {
    const el = document.getElementById('aw-typing');
    if (el) el.remove();
    isTyping = false;
  }

  function disableInput() {
    document.getElementById('aw-input').disabled = true;
    document.getElementById('aw-send-btn').disabled = true;
  }

  function enableInput() {
    document.getElementById('aw-input').disabled = false;
    document.getElementById('aw-send-btn').disabled = false;
    document.getElementById('aw-input').focus();
  }

  // ─── DOM Actions (scroll to element, highlight element) ───────────────────────
  function executeDomActions(actions) {
    if (!actions || !Array.isArray(actions)) return;
    actions.forEach(action => {
      try {
        if (action.type === 'scroll') {
          const el = document.querySelector(action.selector);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            logEvent('dom_scroll', { selector: action.selector });
          }
        } else if (action.type === 'highlight') {
          const el = document.querySelector(action.selector);
          if (el) {
            const original = el.style.outline;
            el.style.outline = `3px solid ${AVATAR_COLOR}`;
            el.style.outlineOffset = '4px';
            setTimeout(() => { el.style.outline = original; }, 3000);
            logEvent('dom_highlight', { selector: action.selector });
          }
        }
      } catch (err) {
        console.warn('[AvatarWidget] DOM action failed:', err);
      }
    });
  }

  // ─── Event Logging ────────────────────────────────────────────────────────────
  function logEvent(type, data = {}) {
    try {
      fetch(EVENTS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': API_KEY
        },
        body: JSON.stringify({ type, data }),
        keepalive: true
      }).catch(() => {}); // Silently fail — events are non-critical
    } catch (e) {}
  }

  // ─── Init ─────────────────────────────────────────────────────────────────────
  function init() {
    injectStyles();
    buildWidget();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
