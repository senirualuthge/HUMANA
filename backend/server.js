require('dotenv').config();
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const app = express();
app.use(cors());

// Webhook must use express.raw to preserve raw buffer for Stripe verification
const billingController = require('./src/modules/billing/billing.controller');
app.post('/billing/webhook', express.raw({ type: 'application/json' }), billingController.handleWebhook);

app.use(express.json());

const authRoutes = require('./src/modules/auth/auth.routes');
const clientRoutes = require('./src/modules/clients/clients.routes');
const websiteRoutes = require('./src/modules/websites/websites.routes');
const knowledgeRoutes = require('./src/modules/knowledge/knowledge.routes');
const aiRoutes = require('./src/modules/ai/ai.routes');
const usageRoutes = require('./src/modules/usage/usage.routes');
const eventsRoutes = require('./src/modules/events/events.routes');
const billingRoutes = require('./src/modules/billing/billing.routes');
const adminRoutes = require('./src/modules/admin/admin.routes');

const { apiLimiter, authLimiter } = require('./src/core/middleware/rateLimiter');
app.use(apiLimiter);

app.use('/auth', authLimiter, authRoutes);
app.use('/clients', clientRoutes);
app.use('/websites', websiteRoutes);
app.use('/knowledge', knowledgeRoutes);
app.use('/ai', aiRoutes);
app.use('/usage', usageRoutes);
app.use('/events', eventsRoutes);
app.use('/admin', adminRoutes);
app.use('/billing', billingRoutes);

const server = http.createServer(app);
const wss = new WebSocket.Server({ server, path: '/chat' });

// Websocket connection handling
wss.on('connection', async (ws, req) => {
  const urlParams = new URLSearchParams(req.url.split('?')[1]);
  const apiKey = urlParams.get('apiKey');

  if (!apiKey) {
    ws.close(1008, 'API Key required');
    return;
  }

  // Verify API Key against the websites table
  let website;
  try {
    website = await prisma.website.findUnique({
      where: { apiKey },
      include: { client: true }
    });
    if (!website || !website.isActive || website.client.status !== 'active') {
      ws.close(1008, 'Invalid or inactive API Key');
      return;
    }

    // Domain validation check
    const origin = req.headers.origin || req.headers.host;
    if (origin && website.domain !== '*' && !origin.includes(website.domain)) {
      console.warn(`Origin mismatch. Expected: ${website.domain}, Received: ${origin}`);
      ws.close(1008, 'Unauthorized Domain');
      return;
    }
  } catch (error) {
    console.error('WS auth DB error:', error.message);
    ws.close(1011, 'Internal server error during authentication');
    return;
  }

  ws.on('message', async (message) => {
    console.error('Received WS message:', message ? message.toString() : 'empty');
    try {
      const parsed = JSON.parse(message.toString());
      
      if (parsed.type === 'chat') {
        ws.send(JSON.stringify({ type: 'status', content: 'typing' }));

        const { generateStream } = require('./src/services/conversation.service');
        await generateStream(website.clientId, parsed.content, 
          (chunk) => {
            ws.send(JSON.stringify({ type: 'chunk', content: chunk }));
          },
          (fullResponse) => {
            ws.send(JSON.stringify({ type: 'done', content: fullResponse }));
          }
        );
      }
    } catch (e) {
      console.error('WS Error:', e);
      ws.send(JSON.stringify({ type: 'error', message: 'Internal Server Error' }));
    }
  });

});

app.get('/api/health', (req, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 8000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
