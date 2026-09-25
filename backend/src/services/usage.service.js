const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

/**
 * Log a usage entry.
 * Matches the Prisma UsageLog model: { clientId, metric, value }
 *
 * @param {string} clientId - The client that made the request
 * @param {string} metric   - 'messages' | 'tokens' | 'voice_seconds'
 * @param {number} value    - Number of units consumed
 */
const logUsage = async (clientId, metric, value = 1) => {
  try {
    return await prisma.usageLog.create({
      data: { clientId, metric, value }
    });
  } catch (error) {
    console.error('Error logging usage:', error.message);
    // Non-fatal — don't propagate
  }
};

const checkTokenLimits = async (clientId) => {
  try {
    const client = await prisma.client.findUnique({ where: { id: clientId } });
    if (!client) return false;

    if (client.plan === 'enterprise') return true;

    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    const usageLogs = await prisma.usageLog.findMany({
      where: {
        clientId,
        metric: 'tokens',
        timestamp: { gte: startOfMonth }
      }
    });

    const totalTokens = usageLogs.reduce((acc, log) => acc + log.value, 0);

    const limits = {
      free: 10000,
      starter: 50000,
      pro: 500000
    };

    const limit = limits[client.plan || 'free'] || limits['free'];
    return totalTokens < limit;
  } catch (error) {
    console.error('CheckTokenLimits error:', error.message);
    return false; // safe fail
  }
};

module.exports = { logUsage, checkTokenLimits };
