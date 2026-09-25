const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY || 'sk_test_fake');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const PLANS = {
  starter: { priceId: process.env.STRIPE_STARTER_PRICE || 'price_123', name: 'starter' },
  pro: { priceId: process.env.STRIPE_PRO_PRICE || 'price_456', name: 'pro' },
  enterprise: { priceId: process.env.STRIPE_ENTERPRISE_PRICE || 'price_789', name: 'enterprise' }
};

const createCheckoutSession = async (req, res) => {
  try {
    const { planId, clientId } = req.body;
    const plan = PLANS[planId];
    
    if (!plan) return res.status(400).json({ error: 'Invalid plan selected' });
    
    // Validating client existence
    const client = await prisma.client.findUnique({ where: { id: clientId } });
    if (!client) return res.status(404).json({ error: 'Client not found' });

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [{ price: plan.priceId, quantity: 1 }],
      mode: 'subscription',
      client_reference_id: clientId,
      success_url: `${process.env.FRONTEND_URL || 'http://localhost:5173'}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.FRONTEND_URL || 'http://localhost:5173'}/dashboard?cancel=true`,
    });
    
    res.json({ id: session.id, url: session.url });
  } catch (err) {
    console.error('Stripe Checkout session error:', err);
    res.status(500).json({ error: 'Checkout Session creation failed' });
  }
};

const handleWebhook = async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    // req.body should be the raw buffer here
    event = stripe.webhooks.constructEvent(
      req.body, 
      sig, 
      process.env.STRIPE_WEBHOOK_SECRET || 'whsec_fake'
    );
  } catch (err) {
    console.error('Stripe Webhook Error:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  // Handle the webhook event
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    const clientId = session.client_reference_id;
    
    if (clientId) {
      await prisma.client.update({
        where: { id: clientId },
        data: {
          plan: 'pro', // In a real app we'd map the session's plan properly
          status: 'active'
        }
      });
      console.log(`[Billing] Upgraded client ${clientId} active subscription plan.`);
    }
  }

  res.json({received: true});
};

module.exports = { createCheckoutSession, handleWebhook };
