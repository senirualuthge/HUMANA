const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// GET /admin/health — basic health check
exports.health = async (req, res) => {
  try {
    // Ping DB
    await prisma.$queryRaw`SELECT 1`;
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      database: 'connected'
    });
  } catch (error) {
    res.status(503).json({
      status: 'error',
      database: 'disconnected',
      error: error.message
    });
  }
};

// GET /admin/overview — aggregate stats across all clients
exports.overview = async (req, res) => {
  try {
    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);

    const [totalClients, activeClients, totalWebsites, monthlyUsage] = await Promise.all([
      prisma.client.count(),
      prisma.client.count({ where: { status: 'active' } }),
      prisma.website.count(),
      prisma.usageLog.aggregate({
        _count: { id: true },
        _sum: { tokensUsed: true },
        where: { timestamp: { gte: startOfMonth } }
      })
    ]);

    res.json({
      totalClients,
      activeClients,
      totalWebsites,
      thisMonth: {
        requests: monthlyUsage._count.id,
        tokensUsed: monthlyUsage._sum.tokensUsed || 0
      }
    });
  } catch (error) {
    console.error('Admin overview error:', error);
    res.status(500).json({ error: 'Failed to fetch admin overview' });
  }
};

// GET /admin/clients — paginated list of all clients
exports.listAllClients = async (req, res) => {
  try {
    const { page = 1, limit = 20 } = req.query;
    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [clients, total] = await Promise.all([
      prisma.client.findMany({
        skip,
        take: parseInt(limit),
        include: { _count: { select: { websites: true } } },
        orderBy: { createdAt: 'desc' }
      }),
      prisma.client.count()
    ]);

    res.json({
      clients,
      pagination: {
        total,
        page: parseInt(page),
        limit: parseInt(limit),
        totalPages: Math.ceil(total / parseInt(limit))
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to list clients' });
  }
};
