const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
const { storeKnowledge, updateKnowledge } = require('./store.service');

exports.getByClient = async (req, res) => {
  try {
    const { clientId } = req.params;
    const items = await prisma.knowledgeItem.findMany({
      where: { clientId },
      orderBy: { createdAt: 'desc' }
    });
    res.json(items);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch knowledge items' });
  }
};

exports.create = async (req, res) => {
  try {
    const { clientId, title, content, type } = req.body;

    if (!clientId || !content) {
      return res.status(400).json({ error: 'clientId and content are required' });
    }

    const client = await prisma.client.findUnique({ where: { id: clientId } });
    if (!client) {
      return res.status(404).json({ error: 'Client not found' });
    }

    const id = await storeKnowledge(clientId, type || 'text', title || 'Untitled', content);
    const newItem = await prisma.knowledgeItem.findUnique({ where: { id } });

    res.status(201).json(newItem);
  } catch (error) {
    console.error('Create knowledge error:', error);
    res.status(500).json({ error: 'Failed to create knowledge item' });
  }
};

exports.update = async (req, res) => {
  try {
    const { id } = req.params;
    const { title, content, type } = req.body;
    
    const item = await updateKnowledge(id, title, content, type);
    res.json(item);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update knowledge item' });
  }
};

exports.delete = async (req, res) => {
  try {
    await prisma.knowledgeItem.delete({ where: { id: req.params.id } });
    res.json({ message: 'Knowledge item deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete knowledge item' });
  }
};
