const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Log an event from the embedded widget (uses apiKeyMiddleware — req.website is available)
exports.logEvent = async (req, res) => {
  try {
    const { type, data } = req.body;
    const { website } = req;

    if (!type) {
      return res.status(400).json({ error: 'Event type is required' });
    }

    const event = await prisma.event.create({
      data: {
        clientId: website.clientId,
        websiteId: website.id,
        type,       // e.g. 'widget_open', 'widget_close', 'message_sent', 'dom_scroll'
        data: data || {}
      }
    });

    res.status(201).json({ success: true, eventId: event.id });
  } catch (error) {
    console.error('Event log error:', error);
    res.status(500).json({ error: 'Failed to log event' });
  }
};

// Get events for a website (JWT-protected dashboard route)
exports.getWebsiteEvents = async (req, res) => {
  try {
    const { websiteId } = req.params;
    const { type, limit = 100 } = req.query;

    const events = await prisma.event.findMany({
      where: {
        websiteId,
        ...(type && { type })
      },
      take: parseInt(limit),
      orderBy: { createdAt: 'desc' }
    });

    res.json(events);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch events' });
  }
};
