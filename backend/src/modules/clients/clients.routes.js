const express = require('express');
const router = express.Router();
const clientsController = require('./clients.controller');
const authMiddleware = require('../../core/middleware/authMiddleware');

router.use(authMiddleware);

router.get('/', clientsController.getAll);
router.get('/:id', clientsController.getById);
router.post('/', clientsController.create);
router.put('/:id', clientsController.update);
router.delete('/:id', clientsController.delete);

module.exports = router;
