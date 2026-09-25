const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');
const prisma = new PrismaClient();

// Get websites for a specific client
exports.getByClient = async (req, res) => {
  try {
    const { clientId } = req.params;
    const websites = await prisma.website.findMany({
      where: { clientId }
    });
    res.json(websites);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch websites' });
  }
};

exports.create = async (req, res) => {
  try {
    const { clientId, domain } = req.body;
    
    // Check if client exists
    const client = await prisma.client.findUnique({ where: { id: clientId } });
    if (!client) {
      return res.status(404).json({ error: 'Client not found' });
    }

    // Generate a unique API key for the website widget
    const apiKey = crypto.randomBytes(32).toString('hex');

    const newWebsite = await prisma.website.create({
      data: {
        clientId,
        domain,
        apiKey
      }
    });

    res.status(201).json(newWebsite);
  } catch (error) {
    console.error('Create website error:', error);
    res.status(500).json({ error: 'Failed to create website' });
  }
};

exports.update = async (req, res) => {
  try {
    const { id } = req.params;
    const { domain, isActive } = req.body;
    const website = await prisma.website.update({
      where: { id },
      data: { domain, isActive }
    });
    res.json(website);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update website' });
  }
};

exports.delete = async (req, res) => {
  try {
    await prisma.website.delete({ where: { id: req.params.id } });
    res.json({ message: 'Website deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete website' });
  }
};
