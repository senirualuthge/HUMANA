const WebSocket = require('ws');

async function runTest() {
  console.log("Starting End-to-End Test for WebSocket Conversation...");
  const startTime = Date.now();
  
  // Connect to the Node.js backend
  const ws = new WebSocket('ws://localhost:8000/chat?apiKey=mocked-key', {
    headers: { origin: 'http://test-website.com' }
  });

  ws.on('open', () => {
    console.log(`[${Date.now() - startTime}ms] Connected to Node.js backend`);
    setTimeout(() => {
      // Send a chat message
      const payload = {
        type: 'chat',
        content: 'Hello, what products do you sell?'
      };
      ws.send(JSON.stringify(payload));
      console.log(`[${Date.now() - startTime}ms] Sent message: ${payload.content}`);
    }, 500);
  });

  let firstChunkTime = null;

  ws.on('message', (data) => {
    const elapsed = Date.now() - startTime;
    const parsed = JSON.parse(data);
    
    if (parsed.type === 'status') {
      console.log(`[${elapsed}ms] Status: ${parsed.content}`);
    } else if (parsed.type === 'chunk') {
      if (!firstChunkTime) {
        firstChunkTime = elapsed;
        console.log(`[${elapsed}ms] First chunk received (Latency: ${firstChunkTime}ms)`);
      }
      process.stdout.write(parsed.content);
    } else if (parsed.type === 'done') {
      console.log(`\n\n[${elapsed}ms] Done! Total Time: ${elapsed}ms`);
      ws.close();
      process.exit(0);
    } else if (parsed.type === 'error') {
      console.error(`\n[${elapsed}ms] Received error: ${parsed.message}`);
      ws.close();
      process.exit(1);
    }
  });

  ws.on('close', (code, reason) => {
    console.log(`\nConnection closed: ${code} - ${reason.toString()}`);
  });

  ws.on('error', (err) => {
    console.error(`\nWebSocket Error: ${err.message}`);
    process.exit(1);
  });
}

runTest();
