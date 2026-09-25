const { OpenAI } = require('openai');

const openai = new OpenAI();

/**
 * Generate an embedding for a piece of text.
 * @param {string} text 
 * @returns {Promise<number[]>}
 */
async function generateEmbedding(text) {
  const result = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text.replace(/\n/g, ' '),
  });
  return result.data[0].embedding;
}

module.exports = {
  generateEmbedding,
};
