const db = require('../models');
const bcrypt = require('bcrypt');

const loginAdmin = async (req, res) => {
    const { username, password, role } = req.body;
    try {
        const user = await db.User.findOne({ where: { username, role } });
        if (!user) {
            return res.status(400).json({ message: 'Invalid credentials.' });
        }
        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.status(400).json({ message: 'Invalid credentials.' });
        }
        req.session.userId = user.id;
        req.session.username = user.username;
        req.session.role = user.role;
        res.status(200).json({ message: 'Login successful.' });
    } catch (error) {
        console.error('Error during login:', error);
        res.status(500).json({ message: 'An error occurred during login. Please try again.' });
    }
};

module.exports = {
    // ...existing exports...
    loginAdmin,
};