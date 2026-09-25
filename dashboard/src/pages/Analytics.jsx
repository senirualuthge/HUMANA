import React, { useEffect, useState } from 'react';
import MessagesChart from '../components/charts/MessagesChart';
import TokensChart from '../components/charts/TokensChart';
import TopQuestions from '../components/TopQuestions';
import { Activity, Zap, Users, MessageSquare } from 'lucide-react';

export default function Analytics() {
  const [data, setData] = useState({
    messageData: [],
    tokenData: [],
    questions: [],
    stats: { totalMessages: 0, activeUsers: 0, avgResponseTime: '0ms' }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In the future: fetch('/api/analytics')
    // Simulating data load for now
    setTimeout(() => {
      setData({
        messageData: [
          { date: 'Nov 1', count: 45 },
          { date: 'Nov 2', count: 52 },
          { date: 'Nov 3', count: 38 },
          { date: 'Nov 4', count: 65 },
          { date: 'Nov 5', count: 88 },
          { date: 'Nov 6', count: 49 },
          { date: 'Nov 7', count: 95 },
        ],
        tokenData: [
          { date: 'Nov 1', tokens: 12000 },
          { date: 'Nov 2', tokens: 15400 },
          { date: 'Nov 3', tokens: 9000 },
          { date: 'Nov 4', tokens: 21000 },
          { date: 'Nov 5', tokens: 28000 },
          { date: 'Nov 6', tokens: 11500 },
          { date: 'Nov 7', tokens: 32000 },
        ],
        questions: [
          { text: "What is the pricing plan?", count: 156 },
          { text: "How do I install the widget?", count: 89 },
          { text: "Can I customize the avatar?", count: 64 },
          { text: "Do you support multiple languages?", count: 42 },
          { text: "Where is the data stored?", count: 28 },
        ],
        stats: {
          totalMessages: 432,
          activeUsers: 89,
          avgResponseTime: '1.2s'
        }
      });
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto min-h-screen bg-gray-50">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Overview</h1>
        <p className="text-gray-500">Monitor your digital human's performance and usage.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded shadow border-l-4 border-blue-500">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100 text-blue-600 mr-4">
              <MessageSquare size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-500 font-medium">Total Messages</p>
              <h3 className="text-2xl font-bold text-gray-900">{data.stats.totalMessages}</h3>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded shadow border-l-4 border-green-500">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 text-green-600 mr-4">
              <Users size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-500 font-medium">Active Users</p>
              <h3 className="text-2xl font-bold text-gray-900">{data.stats.activeUsers}</h3>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded shadow border-l-4 border-yellow-500">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100 text-yellow-600 mr-4">
              <Zap size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-500 font-medium">Avg Response Time</p>
              <h3 className="text-2xl font-bold text-gray-900">{data.stats.avgResponseTime}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <MessagesChart data={data.messageData} />
          <TokensChart data={data.tokenData} />
        </div>
        <div className="lg:col-span-1">
          <TopQuestions questions={data.questions} />
        </div>
      </div>
    </div>
  );
}
