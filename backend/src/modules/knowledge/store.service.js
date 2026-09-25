const { PrismaClient } = require('@prisma/client');
const { generateEmbedding } = require('./embed.service');

const prisma = new PrismaClient(); // Default initialization

async function storeKnowledge(clientId, type, title, content) {
  const embedding = await generateEmbedding(content);

  // Prisma 5+ pgvector insertion using raw SQL because Unsupported typings
  // However, modern Prisma has typed vector support if extensions are used!
  // Wait, the client might not have extension type generation correctly enabled unless it's configured.
  // Using $executeRaw for safety to insert vectors
  const knowledgeId = await prisma.$transaction(async (tx) => {
    // Generate UUID inside the raw or create the record first
    const record = await tx.knowledgeItem.create({
      data: {
        clientId,
        type,
        title,
        content
      }
    });

    // Update with vector
    // We stringify the array as postgres vector format '[0.1, 0.2, ...]'
    const vectorString = `[${embedding.join(',')}]`;
    await tx.$executeRaw`UPDATE "KnowledgeItem" SET embedding = ${vectorString}::vector WHERE id = ${record.id}`;

    return record.id;
  });

  return knowledgeId;
}

async function updateKnowledge(id, title, content, type) {
  const data = {};
  if (title) data.title = title;
  if (type) data.type = type;
  if (content) data.content = content;

  let item = await prisma.knowledgeItem.update({
    where: { id },
    data
  });

  if (content) {
    const embedding = await generateEmbedding(content);
    const vectorString = `[${embedding.join(',')}]`;
    await prisma.$executeRaw`UPDATE "KnowledgeItem" SET embedding = ${vectorString}::vector WHERE id = ${id}`;
  }

  return item;
}

module.exports = {
  storeKnowledge,
  updateKnowledge,
};
