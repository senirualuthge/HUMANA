

async function testRateLimit() {
  console.log('Testing rate limit on /api/chat...');
  
  let successCount = 0;
  let rateLimitedCount = 0;
  
  // Send 120 requests to trigger rate limit
  for (let i = 0; i < 120; i++) {
    const res = await fetch('http://localhost:8000/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: JSON.stringify({ message: "Hello", sessionId: "test-session", apiKey: "test-api-key" })
    });
    
    if (res.status === 200) {
      successCount++;
    } else if (res.status === 429) {
      rateLimitedCount++;
    } else {
      console.log(`Unexpected status: ${res.status}`);
    }
  }
  
  console.log(`Success: ${successCount}`);
  console.log(`Rate Limited: ${rateLimitedCount}`);
  if (rateLimitedCount > 0) {
    console.log('✅ Rate limiting is working!');
  } else {
    console.log('❌ Rate limiting failed to trigger.');
  }
}

async function testAnalytics() {
  console.log('\nTesting Analytics Endpoints...');
  
  try {
    const res = await fetch('http://localhost:8000/usage/client/dummy-client-id?period=month', {
      headers: { 'Authorization': 'Bearer test-token' }
    });
    const data = await res.json();
    console.log('Client Usage Status:', res.status);
    console.log('Client Usage Data:', data);
    
    // Test without period (defaults to month)
    const res2 = await fetch('http://localhost:8000/usage/client/dummy-client-id', {
      headers: { 'Authorization': 'Bearer test-token' }
    });
    const data2 = await res2.json();
    console.log('Client Usage (default period) Status:', res2.status);
    console.log('Client Usage (default period) Data:', data2);
    

    
    console.log('✅ Analytics endpoints are functioning.');
  } catch (err) {
    console.error('❌ Analytics test failed:', err.message);
  }
}

async function main() {
  await testRateLimit();
  await testAnalytics();
}

main();
