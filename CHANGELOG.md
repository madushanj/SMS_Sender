# Changelog

## [1.1.0] – 2025-10-09

### 🚀 Major Features

* **Multipart SMS Support (Concatenated Messages)**
  * Long messages now automatically split and sent as multipart SMS
  * Recipients receive messages as a single, seamless text (no visible "(1/3)" markers)
  * Uses **PDU mode with UDH** (User Data Header) for proper concatenation
  * All message parts linked with reference numbers for automatic reassembly
  
* **Smart Encoding Detection**
  * **GSM7**: Standard text (160 chars single / 153 chars per part)
  * **UCS2**: Unicode/Arabic/Emoji text (70 chars single / 67 chars per part)
  * Automatic encoding selection based on message content
  * Properly handles GSM7 extended characters (^{}[~]|€)

* **PDU Mode Implementation**
  * Switched from text mode to PDU mode for better reliability
  * Supports proper message concatenation headers
  * Better compatibility with all network operators

### 🐛 Bug Fixes

* Fixed issue where long messages were marked as "sent" but not received
* Fixed problem where multipart messages arrived as separate texts
* Fixed missing first part in multipart messages

---

## [1.0.0] – 2025-10-07

### 🚀 Features

* **SMS Sending Engine**

  * Sends SMS using **AT commands** over a serial connection to a GSM modem
  * Queues and processes messages from a **MySQL database**

* **Retry Logic**

  * Messages are retried up to **3 times** if sending fails
  * New `attempts` field tracks how many retries remain

* **Status Handling**

  * Statuses include `pending`, `sent`, and `failed`
  * `failed` replaces the older `error` status for consistency

* **Schema Design**
  Updated database schema supports:

  * `recipient` – name of the SMS recipient
  * `phone_number` – replaces `destination`
  * `error_message` – replaces `error_msg`, max length 255 characters
  * `updated_at` – timestamp for auditing
  * `attempts` – number of remaining retry attempts

* **Error Handling**

  * Improved error message logging
  * Robust database connection management
  * Messages only marked as failed after all retries are exhausted

### 🛠 Configuration

* Configuration settings moved into a dedicated `config.py` file for clarity and modularity

### 📦 Utility Scripts

* `identify.py` – Identify the modem and print device information.