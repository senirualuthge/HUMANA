const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Get usage summary for a client
exports.getClientUsage = async (req, res) => {
  try {
    const { clientId } = req.params;
    const { period } = req.query; // 'day' | 'month'

    const startDate = new Date();
    if (period === 'day') {
      startDate.setHours(0, 0, 0, 0);
    } else {
      startDate.setDate(1);
      startDate.setHours(0, 0, 0, 0);
    }

    const [messages, tokens, voiceSeconds] = await Promise.all([
      prisma.usageLog.aggregate({
        _sum: { value: true },
        where: { clientId, metric: 'messages', createdAt: { gte: startDate } }
      }),
      prisma.usageLog.aggregate({
        _sum: { value: true },
        where: { clientId, metric: 'tokens', createdAt: { gte: startDate } }
      }),
      prisma.usageLog.aggregate({
        _sum: { value: true },
        where: { clientId, metric: 'voice_seconds', createdAt: { gte: startDate } }
      })
    ]);

    res.json({
      clientId,
      period: period || 'month',
      since: startDate,
      messages: messages._sum.value || 0,
      tokens: tokens._sum.value || 0,
      voiceSeconds: voiceSeconds._sum.value || 0
    });
  } catch (error) {
    console.error('Usage fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch usage data' });
  }
};

// Get raw usage logs for a client (paginated)
exports.getClientUsageLogs = async (req, res) => {
  try {
    const { clientId } = req.params;
    const { limit = 50, page = 1, metric } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const logs = await prisma.usageLog.findMany({
      where: { clientId, ...(metric && { metric }) },
      take: parseInt(limit),
      skip,
      orderBy: { createdAt: 'desc' }
    });

    res.json(logs);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch usage logs' });
  }
};
