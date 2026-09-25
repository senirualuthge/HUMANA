const { PrismaClient } = require('@prisma/client');
const OpenAI = require('openai');
const { logUsage } = require('../../services/usage.service');

const prisma = new PrismaClient();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

exports.chat = async (req, res) => {
  try {
    const { message } = req.body;
    const { website } = req;
    const clientId = website.clientId;

    if (!message) {
      return res.status(400).json({ error: 'message is required' });
    }

    // 1. Fetch Knowledge Base for this client
    const knowledgeItems = await prisma.knowledgeItem.findMany({
      where: { clientId }
    });

    const knowledgeContext = knowledgeItems.length > 0
      ? knowledgeItems.map(item => `${item.title ? `**${item.title}**\n` : ''}${item.content}`).join('\n\n')
      : 'No knowledge base configured.';

    // 2. Build system prompt
    const systemPrompt = `You are a helpful AI assistant for a business website.
Answer questions using ONLY the information provided in the knowledge base below.
If the answer is not in the knowledge base, say: "I don't have that information, but I can connect you with our team."

--- KNOWLEDGE BASE ---
${knowledgeContext}
--- END KNOWLEDGE BASE ---`;

    // 3. Call OpenAI
    const aiResponse = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: message }
      ]
    });

    const reply = aiResponse.choices[0].message.content;
    const tokensUsed = aiResponse.usage.total_tokens;

    // 4. Log usage (messages + tokens)
    await logUsage(clientId, 'messages', 1);
    await logUsage(clientId, 'tokens', tokensUsed);

    res.json({ reply, tokensUsed });
  } catch (error) {
    console.error('AI chat error:', error);
    res.status(500).json({ error: 'Failed to process AI chat request' });
  }
};
