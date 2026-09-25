(function () {
  const scriptTag = document.currentScript;
  const apiKey = scriptTag?.getAttribute('data-api-key') || 'test-api-key';
  const backendUrl = scriptTag?.getAttribute('data-backend-url') || 'ws://localhost:8000/chat';

  // State
  let ws = null;
  let isOpen = false;

  // 1. Inject Styles
  const style = document.createElement('style');
  style.innerHTML = `
    #aidigital-human-widget {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      font-family: system-ui, -apple-system, sans-serif;
    }
    #aidigital-human-trigger {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: #007bff;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      font-size: 24px;
      transition: transform 0.2s;
    }
    #aidigital-human-trigger:hover {
      transform: scale(1.05);
    }
    #aidigital-human-window {
      position: absolute;
      bottom: 80px;
      right: 0;
      width: 350px;
      height: 500px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      display: none;
      flex-direction: column;
      overflow: hidden;
    }
    #aidigital-human-window.open {
      display: flex;
    }
    #aidigital-human-header {
      background: #007bff;
      color: white;
      padding: 16px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #aidigital-human-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f8f9fa;
    }
    .message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.4;
    }
    .message.user {
      align-self: flex-end;
      background: #007bff;
      color: white;
      border-bottom-right-radius: 4px;
    }
    .message.ai {
      align-self: flex-start;
      background: white;
      color: #333;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    #aidigital-human-input-area {
      padding: 12px;
      background: white;
      border-top: 1px solid #eee;
      display: flex;
      gap: 8px;
    }
    #aidigital-human-input {
      flex: 1;
      border: 1px solid #ddd;
      border-radius: 20px;
      padding: 8px 16px;
      outline: none;
      font-size: 14px;
    }
    #aidigital-human-send {
      background: #007bff;
      color: white;
      border: none;
      border-radius: 50%;
      width: 36px;
      height: 36px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  `;
  document.head.appendChild(style);

  // 2. Build DOM elements
  const widgetHtml = `
    <div id="aidigital-human-widget">
      <div id="aidigital-human-window">
        <div id="aidigital-human-header">
          <span>AI Assistant</span>
          <span id="aidigital-human-close" style="cursor: pointer; opacity: 0.8;">&times;</span>
        </div>
        <div id="aidigital-human-messages">
          <div class="message ai">Hi there! How can I help you today?</div>
        </div>
        <div id="aidigital-human-input-area">
          <input type="text" id="aidigital-human-input" placeholder="Type your message..." />
          <button id="aidigital-human-send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>
      <div id="aidigital-human-trigger">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
    </div>
  `;

  const container = document.createElement('div');
  container.innerHTML = widgetHtml;
  document.body.appendChild(container);

  // 3. Logic & References
  const trigger = document.getElementById('aidigital-human-trigger');
  const chatWindow = document.getElementById('aidigital-human-window');
  const closeBtn = document.getElementById('aidigital-human-close');
  const inputEl = document.getElementById('aidigital-human-input');
  const sendBtn = document.getElementById('aidigital-human-send');
  const messagesDiv = document.getElementById('aidigital-human-messages');

  let currentAiMessageEl = null;

  const toggleOpen = () => {
    isOpen = !isOpen;
    if (isOpen) {
      chatWindow.classList.add('open');
      trigger.style.display = 'none';
      connectWs();
    } else {
      chatWindow.classList.remove('open');
      trigger.style.display = 'flex';
    }
  };

  trigger.addEventListener('click', toggleOpen);
  closeBtn.addEventListener('click', toggleOpen);

  const addMessage = (role, text) => {
    const el = document.createElement('div');
    el.className = `message ${role}`;
    el.innerText = text;
    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return el;
  };

  const connectWs = () => {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    
    ws = new WebSocket(`${backendUrl}?apiKey=${apiKey}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status' && data.content === 'typing') {
        currentAiMessageEl = addMessage('ai', 'Typing...');
      } else if (data.type === 'chunk' && currentAiMessageEl) {
        if (currentAiMessageEl.innerText === 'Typing...') currentAiMessageEl.innerText = '';
        currentAiMessageEl.innerText += data.content;
      } else if (data.type === 'done') {
        currentAiMessageEl = null;
      } else if (data.type === 'action') {
        // the server can emit {"type":"action", "command":"scroll", "y": 500}
        if (data.command === 'scroll') {
          window.scrollTo({ top: data.y, behavior: 'smooth' });
        } else if (data.command === 'highlight' && data.selector) {
          const el = document.querySelector(data.selector);
          if (el) {
            el.style.border = '2px solid red';
            setTimeout(() => el.style.border = '', 3000);
          }
        }
      }
    };
    ws.onerror = () => {
      addMessage('ai', 'Could not connect to the server.');
    };
  };

  const sendMessage = () => {
    const text = inputEl.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    addMessage('user', text);
    
    // Minimal semantic contextualization: extract page URL/Title
    const contextMeta = `[Page Context: URL ${window.location.href}, Title: ${document.title}]`;

    ws.send(JSON.stringify({ 
      type: 'chat', 
      content: `${contextMeta}\n${text}` 
    }));
    
    inputEl.value = '';
  };

  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });

  const proactiveActions = () => {
    // Proactive trigger after 10 seconds if unopened
    setTimeout(() => {
      if (!isOpen) {
        trigger.style.transform = 'scale(1.2)';
        setTimeout(() => trigger.style.transform = 'scale(1)', 300);
      }
    }, 10000);

    // Provide a proactive hint/highlight
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        const hint = document.createElement('div');
        hint.style.cssText = 'position:absolute; bottom:65px; left:50%; transform:translateX(-50%); background:#333; color:#fff; padding:4px 8px; border-radius:4px; font-size:12px; pointer-events:none; opacity:0.9;';
        hint.innerText = 'Need help?';
        trigger.parentNode.appendChild(hint);
        setTimeout(() => hint.remove(), 5000);
      }
    }, 15000);
  };

  proactiveActions();

})();
