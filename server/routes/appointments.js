const express = require('express');
const router = express.Router();
const { getAppointmentsByDoctor } = require('../controllers/appointmentsController');

router.get('/doctor-dashboard', async (req, res) => {
    const doctorName = req.user.full_name; // Ensure req.user contains the logged-in user's info
    try {
        const appointments = await getAppointmentsByDoctor(doctorName);
        res.render('doctor_dashboard', { appointments, doctor: req.user });
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch appointments' });
    }
});

// Remove prescription-related routes

module.exports = router;
