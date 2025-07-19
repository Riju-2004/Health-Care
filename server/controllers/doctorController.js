const db = require('../models');
const path = require('path');
const fs = require('fs');
const { SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, colors } = require('reportlab');
const { send_email } = require('../utils/emailUtils'); // Ensure you have a utility function for sending emails
const { generatePrescriptionPDF } = require('../../main'); // Import the function

async function renderPrescriptionForm(req, res) {
    const { appointment_id } = req.params;
    const appointment = await db.Appointment.findOne({ where: { id: appointment_id } });
    if (!appointment) {
        return res.render('write-prescription', { error: 'Appointment not found' });
    }

    const patient = await db.User.findOne({ 
        where: { id: appointment.user_id },
        attributes: ['full_name', 'email', 'phone_number', 'gender', 'blood_group'] // Ensure these fields are retrieved
    });

    if (patient) {
        console.log('Patient:', patient);
        res.render('write-prescription', { appointment, patient });
    } else {
        res.render('write-prescription', { error: 'Patient not found' });
    }
}

async function writePrescription(req, res) {
    const { appointment_id } = req.params;
    const { patient_name, patient_email, patient_phone, patient_gender, patient_blood, patient_age, disease_name, medication_name, dosage, frequency, duration } = req.body;

    console.log('Received prescription data:', req.body);

    try {
        const pdfPath = await generatePrescriptionPDF({
            appointment_id,
            patient_name,
            patient_email,
            patient_phone,
            patient_gender,
            patient_blood,
            patient_age,
            disease_name,
            medication_name,
            dosage,
            frequency,
            duration
        });

        const prescription = await db.Prescription.create({
            appointment_id,
            patient_name,
            patient_email,
            patient_phone,
            patient_gender,
            patient_blood,
            patient_age,
            disease_name,
            medication_name,
            dosage,
            frequency,
            duration,
            pdf_path: pdfPath
        });

        console.log(`Prescription saved with ID: ${prescription.id}`);
        res.json({ success: true, pdf_path: pdfPath });
    } catch (error) {
        console.error('Error saving prescription:', error);
        res.status(500).json({ success: false, error: 'Failed to save prescription' });
    }
}

async function sendPrescriptionEmail(req, res) {
    const { pdf_path } = req.body;

    try {
        const prescription = await db.Prescription.findOne({ where: { pdf_path: pdf_path } });
        if (prescription) {
            await send_email(prescription.patient_email, "Your Prescription", "Please find attached your prescription.", pdf_path);
            res.render('write-prescription', { success: true, message: 'Prescription sent successfully.' });
        } else {
            res.status(404).json({ error: 'Prescription not found' });
        }
    } catch (error) {
        console.error('Error sending prescription email:', error);
        res.status(500).json({ error: 'Failed to send prescription email' });
    }
}

async function viewPrescription(req, res) {
    const { appointment_id } = req.params;
    try {
        const prescription = await db.Prescription.findOne({ where: { appointment_id: appointment_id } });
        if (prescription) {
            res.sendFile(prescription.pdf_path);
        } else {
            res.status(404).json({ error: 'Prescription not found' });
        }
    } catch (error) {
        console.error('Error fetching prescription:', error);
        res.status(500).json({ error: 'Failed to fetch prescription' });
    }
}

module.exports = {
    renderPrescriptionForm,
    writePrescription,
    sendPrescriptionEmail,
    viewPrescription
};