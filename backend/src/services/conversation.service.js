const WebSocket = require('ws');
const { PrismaClient } = require('@prisma/client');
const OpenAI = require('openai');
const { logUsage, checkTokenLimits } = require('./usage.service');

const prisma = new PrismaClient();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

/**
 * generateStream — called by the WebSocket handler.
 * Fetches the client's knowledge base, builds a prompt, streams the response
 * from OpenAI back to the caller via onChunk / onComplete callbacks.
 *
 * @param {string} clientId - DB ID of the client website
 * @param {string} userMessage - The user's chat message
 * @param {function} onChunk - Called with each streamed text delta
 * @param {function} onComplete - Called with the full accumulated reply when done
 */
const generateStream = async (clientId, userMessage, onChunk, onComplete) => {
  try {
    // 0. Enforce Token Limits
    const isWithinLimits = await checkTokenLimits(clientId);
    if (!isWithinLimits) {
      const msg = "Sorry, the business has exceeded its AI usage limits. Please try again later.";
      onChunk(msg);
      return onComplete(msg);
    }
    // 1. Load knowledge base for this client
    const knowledgeItems = await prisma.knowledgeItem.findMany({
      where: { clientId }
    });
    const knowledgeContext = knowledgeItems.length > 0
      ? knowledgeItems.map(item => item.content).join('\n\n')
      : 'No knowledge base configured.';

    // 2. Build system prompt
    const systemPrompt = `You are a helpful AI assistant for a business website.
Answer questions using ONLY the information provided in the knowledge base below.
If the answer is not in the knowledge base, say: "I don't have that information. Would you like to speak with a human agent?"
Do not guess or invent answers.

--- KNOWLEDGE BASE ---
${knowledgeContext}
--- END KNOWLEDGE BASE ---`;

    // 3. Stream from OpenAI
    let fullText = '';
    const stream = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      stream: true,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage }
      ]
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) {
        fullText += delta;
        onChunk(delta);
      }
    }

    // 4. Log usage (approximate tokens — OpenAI doesn't stream total tokens easily)
    const estimatedTokens = Math.ceil((systemPrompt.length + userMessage.length + fullText.length) / 4);
    await logUsage(clientId, 'tokens', estimatedTokens).catch(e =>
      console.warn('Usage log warning:', e.message)
    );

    onComplete(fullText);
  } catch (error) {
    console.error('ConversationService Error:', error);
    const errorMsg = 'Sorry, an error occurred while processing your request. Please try again.';
    onChunk(errorMsg);
    onComplete(errorMsg);
  }
};

module.exports = { generateStream };
