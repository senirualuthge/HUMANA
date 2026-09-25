const { scrapeUrl } = require('./src/modules/knowledge/services/scraper');
(async () => {
  try {
    const content = await scrapeUrl('http://example.com');
    console.log('Scraper Output:\\n', content.substring(0, 100), '...');
    process.exit(0);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
