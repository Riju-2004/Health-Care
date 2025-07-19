const express = require('express');
const router = express.Router();
const { loginAdmin } = require('../controllers/adminController');

// Ensure the route for handling admin login is defined and points to the correct controller function
router.post('/login_admin', loginAdmin);

module.exports = router;