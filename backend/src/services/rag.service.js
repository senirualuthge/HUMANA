const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
const OpenAI = require('openai');
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const ingestContext = async (clientId, text) => {
  try {
    const response = await openai.embeddings.create({
      model: "text-embedding-ada-002",
      input: text,
    });
    const embedding = response.data[0].embedding;

    await prisma.$executeRaw`
      INSERT INTO "Document" (id, "clientId", content, embedding)
      VALUES (gen_random_uuid(), ${clientId}, ${text}, ${embedding}::vector)
    `;
    console.log("Successfully ingested document snippet.");
  } catch (error) {
    console.error("Error ingesting context:", error);
  }
};

const retrieveContext = async (clientId, query) => {
  try {
    const response = await openai.embeddings.create({
      model: "text-embedding-ada-002",
      input: query,
    });
    const queryEmbedding = response.data[0].embedding;

    const results = await prisma.$queryRaw`
      SELECT id, content, 1 - (embedding <=> ${queryEmbedding}::vector) as similarity
      FROM "Document"
      WHERE "clientId" = ${clientId}
      ORDER BY embedding <=> ${queryEmbedding}::vector
      LIMIT 3;
    `;

    return results.map(r => r.content).join("\n");
  } catch (error) {
    console.error("Error retrieving context:", error);
    return "";
  }
};

module.exports = { ingestContext, retrieveContext };
