const express = require('express');
const router = express.Router();
const eventsController = require('./events.controller');
const authMiddleware = require('../../core/middleware/authMiddleware');
const apiKeyMiddleware = require('../../core/middleware/apiKeyMiddleware');

// Widget logs events using API key
router.post('/', apiKeyMiddleware, eventsController.logEvent);

// Dashboard reads events using JWT
router.get('/website/:websiteId', authMiddleware, eventsController.getWebsiteEvents);

module.exports = router;
