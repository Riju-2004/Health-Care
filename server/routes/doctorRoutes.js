const express = require('express');
const router = express.Router();
const doctorController = require('../controllers/doctorController');

router.get('/write-prescription/:appointment_id', doctorController.renderPrescriptionForm);
router.post('/write-prescription/:appointment_id', doctorController.writePrescription);
router.post('/send-prescription', doctorController.sendPrescriptionEmail);
router.get('/view-prescription/:appointment_id', doctorController.viewPrescription);

module.exports = router;