const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const verifyApiKey = async (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.apiKey;

  if (!apiKey) {
    return res.status(401).json({ error: 'API key required' });
  }

  try {
    const client = await prisma.client.findUnique({
      where: { apiKey }
    });

    if (!client) {
      return res.status(403).json({ error: 'Invalid API key' });
    }

    req.client = client;
    next();
  } catch (error) {
    console.error('API Key verification error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

module.exports = verifyApiKey;
