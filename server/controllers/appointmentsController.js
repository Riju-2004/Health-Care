const db = require('../models');

// ...existing code...

async function getAppointmentsByDoctor(doctorName) {
    try {
        const appointments = await db.Appointment.findAll({
            where: { Select_doctor: doctorName }
        });
        return appointments;
    } catch (error) {
        throw new Error('Failed to fetch appointments');
    }
}

module.exports = {
    // ...existing exports...
    getAppointmentsByDoctor,
};
