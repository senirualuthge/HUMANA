const express = require('express');
const router = express.Router();
const usageController = require('./usage.controller');
const authMiddleware = require('../../core/middleware/authMiddleware');

router.use(authMiddleware);

// GET /usage/client/:clientId?period=month
router.get('/client/:clientId', usageController.getClientUsage);

// GET /usage/client/:clientId/logs?metric=messages&limit=50&page=1
router.get('/client/:clientId/logs', usageController.getClientUsageLogs);

module.exports = router;
