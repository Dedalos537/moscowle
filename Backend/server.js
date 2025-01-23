const express = require("express");
const nodemailer = require("nodemailer");
const bodyParser = require("body-parser");
const cors = require("cors");
const dotenv = require("dotenv");

dotenv.config();

const app = express();

// Middleware
app.use(bodyParser.json());
app.use(cors());

// Configurar transporte de nodemailer con credenciales de cPanel
const transporter = nodemailer.createTransport({
    host: "informes@centrojuanpabloii.com", // Cambia por el host SMTP de tu cPanel
    port: 465, // Puerto SSL (o 587 para TLS)
    secure: true, // true para SSL
    auth: {
        user: "informes@centrojuanpabloii.com", // Tu correo en cPanel
        pass: process.env.EMAIL_PASSWORD, // Contraseña del correo
    },
});

// Ruta para enviar correos
app.post("/send-email", async (req, res) => {
    const { userEmail } = req.body;

    try {
        // Correo para el administrador
        await transporter.sendMail({
            from: '"Centro Juan Pablo II" <informes@centrojuanpabloii.com>',
            to: "informes@centrojuanpabloii.com",
            subject: "Nuevo contacto desde el formulario",
            text: `El usuario ${userEmail} quiere ponerse en contacto con nosotros.`,
        });

        // Correo de confirmación para el usuario
        await transporter.sendMail({
            from: '"Centro Juan Pablo II" <informes@centrojuanpabloii.com>',
            to: userEmail,
            subject: "Confirmación de recepción",
            text: "Gracias por contactarnos. Hemos recibido tu mensaje y te responderemos pronto.",
        });

        res.status(200).json({ message: "Correos enviados correctamente" });
    } catch (error) {
        console.error("Error al enviar correos:", error);
        res.status(500).json({ message: "Error al enviar los correos" });
    }
});

// Iniciar el servidor
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`Servidor escuchando en el puerto ${PORT}`);
});
