import React, { useEffect, useState } from 'react';
import axios from 'axios';

const DoctorDashboard = () => {
    const [appointments, setAppointments] = useState([]);

    useEffect(() => {
        const fetchAppointments = async () => {
            try {
                const response = await axios.get('/api/appointments/doctor-dashboard');
                setAppointments(response.data);
            } catch (error) {
                console.error('Failed to fetch appointments', error);
            }
        };

        fetchAppointments();
    }, []);

    const viewPrescription = async (appointmentId) => {
        try {
            const response = await axios.get(`/api/view-prescription/${appointmentId}`);
            if (response.data.disease_name) {
                alert(`Prescription:\nDisease: ${response.data.disease_name}\nMedication: ${response.data.medication_name}\nDosage: ${response.data.dosage}\nFrequency: ${response.data.frequency}\nDuration: ${response.data.duration}`);
            } else {
                alert('No prescription found.');
            }
        } catch (error) {
            console.error('Error fetching prescription:', error);
        }
    };

    return (
        <div>
            <h1>Doctor Dashboard</h1>
            <ul>
                {appointments.map(appointment => (
                    <li key={appointment.id}>
                        {appointment.details}
                        <button onClick={() => viewPrescription(appointment.id)}>View Prescription</button>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default DoctorDashboard;
