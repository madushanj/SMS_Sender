-- SMS Sender Daemon Database Schema
-- Execute this script to create the required database and table

-- Create database
CREATE DATABASE IF NOT EXISTS smsd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE smsd;

-- Create outbox table for SMS messages
CREATE TABLE IF NOT EXISTS outbox (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient VARCHAR(255) NOT NULL COMMENT 'Recipient name or identifier',
    phone_number VARCHAR(255) NOT NULL COMMENT 'Phone number with country code (e.g., +1234567890)',
    message TEXT NOT NULL COMMENT 'SMS message content',
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending' COMMENT 'Message status',
    attempts INT DEFAULT 3 COMMENT 'Number of retry attempts remaining',
    sent_at DATETIME NULL COMMENT 'When the message was successfully sent',
    error_message VARCHAR(255) NULL COMMENT 'Error message if sending failed',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the record was created',
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'When the record was last updated',
    INDEX idx_status (status),
    INDEX idx_attempts (attempts),
    INDEX idx_created_at (created_at),
    INDEX idx_phone_number (phone_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SMS outbox queue with retry logic';