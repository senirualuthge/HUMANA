const express = require('express');
const router = express.Router();
const websitesController = require('./websites.controller');
const authMiddleware = require('../../core/middleware/authMiddleware');

router.use(authMiddleware);

router.get('/client/:clientId', websitesController.getByClient);
router.post('/', websitesController.create);
router.put('/:id', websitesController.update);
router.delete('/:id', websitesController.delete);

module.exports = router;
