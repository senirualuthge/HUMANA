const express = require('express');
const router = express.Router();
const billingController = require('./billing.controller');

// Create checkout session
router.post('/create-checkout', express.json(), billingController.createCheckoutSession);

module.exports = router;
