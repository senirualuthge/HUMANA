const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Middleware to authenticate external requests using API Key
const apiKeyMiddleware = async (req, res, next) => {
  const apiKey = req.headers['x-api-key'] || req.query.apiKey;

  if (!apiKey) {
    return res.status(401).json({ error: 'Unauthorized: API Key is required' });
  }

  try {
    // Determine the origin website
    const website = await prisma.website.findUnique({
      where: { apiKey },
      include: { client: true }
    });

    if (!website || !website.isActive || website.client.status !== 'active') {
      return res.status(401).json({ error: 'Unauthorized: Invalid or inactive API Key' });
    }

    // Attach website and client info to req for downstream usage
    req.website = website;
    req.client = website.client;

    next();
  } catch (error) {
    console.error('API Key validation error:', error);
    return res.status(500).json({ error: 'Internal server error during authentication' });
  }
};

module.exports = apiKeyMiddleware;
