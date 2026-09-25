import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Analytics from './pages/Analytics';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
        <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-xl leading-none">A</span>
            </div>
            <span className="text-xl font-bold text-gray-800 tracking-tight">AI Digital Human</span>
          </div>
          <div className="flex items-center space-x-6">
            <a href="/analytics" className="text-blue-600 font-medium pb-1 border-b-2 border-blue-600">Analytics</a>
            <a href="#" className="text-gray-500 hover:text-gray-900 font-medium">Knowledge Base</a>
            <a href="#" className="text-gray-500 hover:text-gray-900 font-medium">Settings</a>
            <button className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded-md font-medium text-sm transition-colors">
              User Profile
            </button>
          </div>
        </nav>
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/analytics" replace />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
