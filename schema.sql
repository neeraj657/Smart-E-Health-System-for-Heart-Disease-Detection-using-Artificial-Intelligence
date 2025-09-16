CREATE DATABASE heart_disease_db;

USE heart_disease_db;

CREATE TABLE users (
	id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('doctor', 'patient') NOT NULL
);

CREATE TABLE reports (
	id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    diagnosis VARCHAR(255) NOT NULL,
    diet_plan TEXT NOT NULL,
    medication_plan TEXT NOT NULL,
    progress TEXT
);

