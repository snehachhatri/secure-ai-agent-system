
const express = require("express");
const cors = require("cors");
require("dotenv").config();

const db = require("./db");
const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
    res.send("Student Management System API is running!");
});

app.get("/test-db", async (req, res) => {
    try {
        const [rows] = await db.query("SELECT 1 AS connected");
        res.json(rows);
    } catch (error) {
        console.error("Database error:", error.message);
        res.status(500).json({
            message: "Database connection failed"
        });
    }
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
