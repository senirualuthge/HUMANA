const express = require('express');
const router = express.Router();
const knowledgeController = require('./knowledge.controller');
const authMiddleware = require('../../core/middleware/authMiddleware');

router.use(authMiddleware);

router.get('/client/:clientId', knowledgeController.getByClient);
router.post('/', knowledgeController.create);
router.put('/:id', knowledgeController.update);
router.delete('/:id', knowledgeController.delete);

module.exports = router;
