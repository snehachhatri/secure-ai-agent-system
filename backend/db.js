const mysql = require("mysql2/promise");
require("dotenv").config();

console.log("DB_PASSWORD loaded:", Boolean(process.env.DB_PASSWORD));

const db = mysql.createPool({
    host: process.env.DB_HOST || "localhost",
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME || "student_management"
});

module.exports = db;