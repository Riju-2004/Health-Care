const express = require('express');
const bodyParser = require('body-parser');
const doctorRoutes = require('./routes/doctorRoutes');

const app = express();

app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

app.use('/', doctorRoutes); // Ensure the routes are correctly registered

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});