const express = require('express');
const router = express.Router();
const aiController = require('./ai.controller');
const apiKeyMiddleware = require('../../core/middleware/apiKeyMiddleware');
const { checkUsageLimits } = require('../../core/middleware/usageTracker');

// Protect AI routes with API Key AND Usage limit check
router.use(apiKeyMiddleware);
router.use(checkUsageLimits);

router.post('/chat', aiController.chat);

module.exports = router;
