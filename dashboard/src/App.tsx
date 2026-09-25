import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import './App.css';

const mockChartData = [
  { name: 'Mon', messages: 1200, tokens: 2400 },
  { name: 'Tue', messages: 3000, tokens: 1398 },
  { name: 'Wed', messages: 2000, tokens: 9800 },
  { name: 'Thu', messages: 2780, tokens: 3908 },
  { name: 'Fri', messages: 1890, tokens: 4800 },
  { name: 'Sat', messages: 2390, tokens: 3800 },
  { name: 'Sun', messages: 3490, tokens: 4300 },
];

const mockClients = [
  { id: '1', name: 'Acme Corp', apiKey: 'sk-acme-...', status: 'Active' },
  { id: '2', name: 'Global Widgets', apiKey: 'sk-gw-...', status: 'Inactive' },
  { id: '3', name: 'Nexus Tech', apiKey: 'sk-nxt-...', status: 'Active' },
];

function IconAnalytics() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="m19 9-5 5-4-4-3 3" />
    </svg>
  );
}

function IconData() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6c0 1.6 4 3 8 3s8-1.4 8-3-4-3-8-3-8 1.4-8 3" />
      <path d="M4 6v12c0 1.6 4 3 8 3s8-1.4 8-3V6" />
      <path d="M4 12c0 1.6 4 3 8 3s8-1.4 8-3" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip glass-panel">
        <p className="tooltip-label">{label}</p>
        <p className="tooltip-item gradient-text-primary">Messages: {payload[0].value}</p>
        <p className="tooltip-item gradient-text-secondary">Tokens: {payload[1].value}</p>
      </div>
    );
  }
  return null;
};

function AnalyticsView() {
  return (
    <div className="view-container fade-in">
      <div className="view-header">
        <h2>Intelligence Analytics</h2>
        <p className="subtitle">Real-time metrics for your AI Digital Human platform.</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card glass-panel flex-row">
          <div className="stat-content">
            <span className="stat-label">Total Messages</span>
            <span className="stat-value gradient-text-primary">16,750</span>
          </div>
          <div className="stat-icon-wrapper blue-glow">
            <IconAnalytics />
          </div>
        </div>
        <div className="stat-card glass-panel flex-row">
          <div className="stat-content">
            <span className="stat-label">Tokens Consumed</span>
            <span className="stat-value gradient-text-secondary">30,506</span>
          </div>
          <div className="stat-icon-wrapper purple-glow">
            <IconData />
          </div>
        </div>
        <div className="stat-card glass-panel flex-row">
          <div className="stat-content">
            <span className="stat-label">Active Clients</span>
            <span className="stat-value text-white">2</span>
          </div>
          <div className="stat-icon-wrapper cyan-glow">
            <IconUsers />
          </div>
        </div>
      </div>

      <div className="chart-container glass-panel mt-6">
        <div className="chart-header">
          <h3>Platform Usage Over Time</h3>
        </div>
        <div style={{ width: '100%', height: 350 }}>
          <ResponsiveContainer>
            <AreaChart data={mockChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorMessages" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f2fe" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#00f2fe" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#b224ef" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#b224ef" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="name" stroke="rgba(255,255,255,0.4)" tick={{fill: 'rgba(255,255,255,0.4)'}} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" stroke="rgba(255,255,255,0.4)" tick={{fill: 'rgba(255,255,255,0.4)'}} axisLine={false} tickLine={false} />
              <YAxis yAxisId="right" orientation="right" stroke="rgba(255,255,255,0.4)" tick={{fill: 'rgba(255,255,255,0.4)'}} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }} />
              <Area yAxisId="left" type="monotone" dataKey="messages" stroke="#00f2fe" strokeWidth={3} fillOpacity={1} fill="url(#colorMessages)" />
              <Area yAxisId="right" type="monotone" dataKey="tokens" stroke="#b224ef" strokeWidth={3} fillOpacity={1} fill="url(#colorTokens)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function KnowledgeBaseView() {
  return (
    <div className="view-container fade-in">
      <div className="view-header">
        <h2>Knowledge Base Core</h2>
        <p className="subtitle">Train your Digital Human with custom organization data.</p>
      </div>

      <div className="kb-layout">
        <div className="kb-upload-card glass-panel">
          <div className="upload-icon">
            <IconData />
          </div>
          <h3>Ingest New Document</h3>
          <p className="text-secondary">Supported formats: PDF, TXT. Max size: 10MB.</p>
          <div className="file-input-wrapper mt-4">
            <input type="file" className="file-input" id="file" />
            <label htmlFor="file" className="file-input-label">Choose File</label>
          </div>
          <button className="primary-btn fluid-btn mt-4">Process & Embed via pgvector</button>
        </div>

        <div className="kb-list glass-panel">
          <div className="list-header">
            <h4>Indexed Vectors</h4>
            <span className="badge">2 Documents</span>
          </div>
          <ul className="mt-4">
            <li className="list-item">
              <div className="item-info">
                <span className="item-name">company_policies_2024.pdf</span>
                <span className="item-meta">12,450 tokens • Indexed today</span>
              </div>
              <button className="danger-btn shadow-hover">Delete</button>
            </li>
            <li className="list-item">
              <div className="item-info">
                <span className="item-name">support_faq.txt</span>
                <span className="item-meta">3,200 tokens • Indexed 2 days ago</span>
              </div>
              <button className="danger-btn shadow-hover">Delete</button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function AdminClientsView() {
  return (
    <div className="view-container fade-in">
      <div className="view-header">
        <h2>Super Admin Control Center</h2>
        <p className="subtitle">Manage multi-tenant access and API provisioning.</p>
      </div>

      <div className="glass-panel no-padding mt-4">
        <div className="table-responsive">
          <table className="clients-table">
            <thead>
              <tr>
                <th>Tenant ID</th>
                <th>Organization Name</th>
                <th>API Key (Redacted)</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {mockClients.map(c => (
                <tr key={c.id} className="table-row">
                  <td className="text-secondary">#{c.id.padStart(4, '0')}</td>
                  <td className="font-medium text-white">{c.name}</td>
                  <td><code className="api-key-box">{c.apiKey}</code></td>
                  <td>
                    <span className={`status-badge ${c.status.toLowerCase()}`}>
                      {c.status}
                    </span>
                  </td>
                  <td>
                    <button className="action-btn shadow-hover">Manage</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('analytics');

  return (
    <div className="app-layout system-theme">
      <nav className="glass-sidebar">
        <div className="logo-container">
          <div className="logo-orb"></div>
          <h1 className="logo-text">Neural<span className="gradient-text-primary">Core</span></h1>
        </div>
        
        <ul className="nav-menu mt-6">
          <li className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <IconAnalytics />
            <span>Analytics</span>
          </li>
          <li className={`nav-item ${activeTab === 'knowledge' ? 'active' : ''}`} onClick={() => setActiveTab('knowledge')}>
            <IconData />
            <span>Knowledge Base</span>
          </li>
          <li className={`nav-item ${activeTab === 'clients' ? 'active' : ''}`} onClick={() => setActiveTab('clients')}>
            <IconUsers />
            <span>Clients Admin</span>
          </li>
        </ul>

        <div className="sidebar-footer">
          <div className="system-status">
            <div className="status-dot"></div>
            <span>System Operational</span>
          </div>
        </div>
      </nav>

      <main className="main-content">
        <header className="glass-topbar">
          <div className="search-bar">
            {/* Search Placeholder */}
          </div>
          <div className="user-profile">
            <div className="avatar">A</div>
            <span className="username">Admin User</span>
          </div>
        </header>

        <div className="dashboard-content scrollbar-hide">
          {activeTab === 'analytics' && <AnalyticsView />}
          {activeTab === 'knowledge' && <KnowledgeBaseView />}
          {activeTab === 'clients' && <AdminClientsView />}
        </div>
      </main>
    </div>
  );
}

export default App;

