const express = require('express');
const router = express.Router();
const adminController = require('./admin.controller');
const adminMiddleware = require('../../core/middleware/adminMiddleware');

router.use(adminMiddleware);

router.get('/health', adminController.health);
router.get('/overview', adminController.overview);
router.get('/clients', adminController.listAllClients);

module.exports = router;
