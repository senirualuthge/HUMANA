const { PrismaClient } = require('@prisma/client');
const { generateEmbedding } = require('./embed.service');

const prisma = new PrismaClient();

async function retrieveRelevantContext(clientId, userMessage, limit = 3) {
  const embedding = await generateEmbedding(userMessage);
  const vectorString = `[${embedding.join(',')}]`;

  // Use raw SQL with cosine distance `<=>` or `<->` for L2 distance
  // Assuming `<=>` for cosine distance
  const results = await prisma.$queryRaw`
    SELECT id, title, content, 1 - (embedding <=> ${vectorString}::vector) as similarity
    FROM "KnowledgeItem"
    WHERE "clientId" = ${clientId}
      AND embedding IS NOT NULL
    ORDER BY embedding <=> ${vectorString}::vector
    LIMIT ${limit}
  `;

  return results;
}

module.exports = {
  retrieveRelevantContext,
};
