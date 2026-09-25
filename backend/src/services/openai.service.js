const OpenAI = require('openai');
const openai = process.env.OPENAI_API_KEY ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY }) : null;

const generateStream = async (clientId, message, onChunk, onComplete) => {
  try {
    const { retrieveRelevantContext } = require('../modules/knowledge/retrieve.service');
    const dbResults = await retrieveRelevantContext(clientId, message);
    const context = dbResults.length > 0 ? dbResults.map(r => r.content).join('\n') : "No specific database context found. Try to help user generally.";


    if (!openai) {
      // Mocked output for local testing
      const chunks = ["Hi there! ", "This is a ", "mocked AI response ", "because no OPENAI_API_KEY ", "was provided.\n\n", "Context used: ", context, "\n\n", "If you want real AI, ", "please add evaluating API key ", "to backend/.env"];
      let fullText = "";
      for (const chunk of chunks) {
        fullText += chunk;
        onChunk(chunk);
        await new Promise(r => setTimeout(r, 100));
      }
      
      const { logUsage } = require('./usage.service');
      await logUsage(clientId, 'message', 1).catch(e => console.warn("Mocked usage log"));
      
      onComplete(fullText);
      return;
    }

    const stream = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        { role: 'system', content: `You are an AI assistant. Use this context if relevant: ${context}` },
        { role: 'user', content: message }
      ],
      stream: true,
    });

    let fullText = "";
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || "";
      fullText += content;
      onChunk(content);
    }
    
    const { logUsage } = require('./usage.service');
    await logUsage(clientId, 'message', 1).catch(e => console.warn("Mocked usage log"));

    onComplete(fullText);
  } catch (error) {
    console.error('OpenAI Error:', error);
    onChunk('Sorry, an error occurred while processing your request.');
    onComplete('Sorry, an error occurred while processing your request.');
  }
};

module.exports = { generateStream };
