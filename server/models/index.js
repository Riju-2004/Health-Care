const { Sequelize, DataTypes } = require('sequelize');
const sequelize = new Sequelize('sqlite::memory:');

const User = sequelize.define('User', {
    username: {
        type: DataTypes.STRING,
        allowNull: false
    },
    password: {
        type: DataTypes.STRING,
        allowNull: false
    },
    email: {
        type: DataTypes.STRING,
        allowNull: false
    },
    full_name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    phone_number: {
        type: DataTypes.STRING,
        allowNull: true
    },
    gender: {
        type: DataTypes.STRING,
        allowNull: true
    },
    blood_group: {
        type: DataTypes.STRING,
        allowNull: true
    }
}, {
    tableName: 'users'
});

const Appointment = sequelize.define('Appointment', {
    user_id: {
        type: DataTypes.INTEGER,
        allowNull: false
    },
    doctor_id: {
        type: DataTypes.INTEGER,
        allowNull: false
    },
    date: {
        type: DataTypes.DATE,
        allowNull: false
    },
    time: {
        type: DataTypes.TIME,
        allowNull: false
    }
}, {
    tableName: 'appointments'
});

const Prescription = sequelize.define('Prescription', {
    appointment_id: {
        type: DataTypes.INTEGER,
        allowNull: false
    },
    patient_id: {
        type: DataTypes.INTEGER,
        allowNull: false
    },
    patient_name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    patient_email: {
        type: DataTypes.STRING,
        allowNull: false
    },
    patient_phone: {
        type: DataTypes.STRING,
        allowNull: false
    },
    patient_gender: {
        type: DataTypes.STRING,
        allowNull: false
    },
    patient_blood: {
        type: DataTypes.STRING,
        allowNull: false
    },
    patient_age: {
        type: DataTypes.INTEGER,
        allowNull: false
    },
    disease_name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    medication_name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    dosage: {
        type: DataTypes.STRING,
        allowNull: false
    },
    frequency: {
        type: DataTypes.STRING,
        allowNull: false
    },
    duration: {
        type: DataTypes.STRING,
        allowNull: false
    },
    pdf_path: {
        type: Sequelize.STRING,
        allowNull: true,
    }
}, {
    tableName: 'prescriptions'
});

Prescription.associate = models => {
    Prescription.belongsTo(models.Appointment, { foreignKey: 'appointment_id' });
    Prescription.belongsTo(models.User, { foreignKey: 'patient_id' });
};

module.exports = {
    User,
    Appointment,
    Prescription
};
