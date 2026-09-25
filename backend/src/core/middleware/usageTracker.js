const { PrismaClient } = require('@prisma/client');
const { logUsage } = require('../../services/usage.service');
const prisma = new PrismaClient();

// This middleware checks usage limits BEFORE allowing a request
const checkUsageLimits = async (req, res, next) => {
  try {
    const { website } = req;
    if (!website) {
      return res.status(401).json({ error: 'Unauthorized: No website context found.' });
    }

    const client = await prisma.client.findUnique({
      where: { id: website.clientId }
    });

    if (!client || client.status !== 'active') {
      return res.status(403).json({ error: 'Forbidden: Client account is inactive or missing.' });
    }

    // Define request limit per plan
    const requestLimits = {
      enterprise: 100000,
      pro: 10000,
      starter: 1000
    };
    const requestLimit = requestLimits[client.plan] || 1000;

    // Check how many messages used this month
    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    const usageResult = await prisma.usageLog.aggregate({
      _sum: { value: true },
      where: {
        clientId: website.clientId,
        metric: 'messages',
        createdAt: { gte: startOfMonth }
      }
    });

    if ((usageResult._sum.value || 0) >= requestLimit) {
      return res.status(429).json({ error: 'Usage limit exceeded for current billing cycle.' });
    }

    next();
  } catch (error) {
    console.error('Usage check error:', error);
    res.status(500).json({ error: 'Failed to verify usage limits' });
  }
};

module.exports = { checkUsageLimits, logUsage };
