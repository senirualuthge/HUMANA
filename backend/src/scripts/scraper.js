const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const { storeKnowledge } = require('../modules/knowledge/store.service');

async function scrapeAndIngest(clientId, url) {
  console.log(`Starting scrape of ${url} for client ${clientId}...`);
  const browser = await puppeteer.launch({ headless: 'new' });
  
  try {
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    const html = await page.content();
    const title = await page.title() || url;
    
    const $ = cheerio.load(html);
    // Remove non-content elements
    $('script, style, noscript, iframe, img, svg, nav, footer, header').remove();
    
    const textContent = $('body').text().replace(/\s+/g, ' ').trim();
    
    if (!textContent) {
      console.log('No text content found.');
      return;
    }

    console.log(`Extracted ${textContent.length} characters of text. Generating embedding and storing...`);
    
    // In production, we'd chunk this text. For now, we take up to 8000 chars to avoid OpenAI limits.
    const chunkedText = textContent.slice(0, 8000); 
    
    const id = await storeKnowledge(
      clientId, 
      'website', 
      title, 
      `Source: ${url}\n\n${chunkedText}`
    );
    
    console.log(`Successfully ingested. Knowledge ID: ${id}`);
  } catch (err) {
    console.error(`Error scraping ${url}:`, err.message);
  } finally {
    await browser.close();
  }
}

const args = process.argv.slice(2);
if (args.length < 2) {
  console.log('Usage: node scraper.js <clientId> <url>');
  process.exit(1);
}

const [clientId, url] = args;
scrapeAndIngest(clientId, url).then(() => {
  console.log('Done.');
  process.exit(0);
}).catch(e => {
  console.error(e);
  process.exit(1);
});
