document.getElementById('prescription-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const prescriptionData = {};
    formData.forEach((value, key) => {
        if (key !== 'doctor_id') { // Exclude doctor_id
            prescriptionData[key] = value;
        }
    });

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(prescriptionData),
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('message').innerText = 'Prescription saved successfully.';
            document.getElementById('pdf_path').value = data.pdf_path;
            document.getElementById('sendButton').disabled = false;
        } else {
            document.getElementById('message').innerText = 'Failed to save prescription.';
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('message').innerText = 'An error occurred while saving the prescription.';
    }
});

document.getElementById('sendButton').addEventListener('click', async function() {
    const pdfPath = document.getElementById('pdf_path').value;
    if (!pdfPath) {
        document.getElementById('message').innerText = 'Prescription not saved yet.';
        return;
    }

    try {
        const response = await fetch(`/send-prescription`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pdf_path: pdfPath }),
        });
        if (response.ok) {
            document.getElementById('message').innerText = 'Prescription sent successfully.';
        } else {
            const errorData = await response.json();
            console.error('Error response:', errorData);
            document.getElementById('message').innerText = 'Failed to send prescription.';
        }
    } catch (error) {
        console.error('Fetch error:', error);
        document.getElementById('message').innerText = 'An error occurred while sending the prescription.';
    }
});
