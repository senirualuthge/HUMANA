const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  let client = await prisma.client.findFirst({ where: { email: 'test@example.com' } });
  if (!client) {
    client = await prisma.client.create({
      data: {
        name: 'Test Client',
        email: 'test@example.com',
        status: 'active',
        plan: 'enterprise'
      }
    });
  }

  let website = await prisma.website.findUnique({ where: { apiKey: 'mocked-key' } });
  if (!website) {
    website = await prisma.website.create({
      data: {
        domain: 'test-website.com',
        apiKey: 'mocked-key',
        clientId: client.id
      }
    });
  }
  console.log('Test data seeded.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
