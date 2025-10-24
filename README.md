# SMS Sender Daemon

A Python daemon service that sends SMS messages using a connected USB modem/dongle. It monitors a MySQL database for pending messages and sends them via the **python-gsmmodem library** with **full multipart SMS support**.

## ✨ Features

### Core Functionality
- **Multipart SMS Support**: Long messages (up to thousands of characters) automatically split and reassembled on recipient's phone
- **Professional Library**: Uses python-gsmmodem-new for reliable modem communication
- **Smart Encoding**: Auto-detects GSM7 (160 chars) vs UCS2/Unicode (70 chars)
- **PDU Mode**: Proper concatenation headers for multipart messages
- Automatic polling of MySQL database for pending SMS messages
- Support for any AT-command compatible GSM/3G/4G modem

### Reliability
- **Retry logic**: Automatically retries failed messages up to 3 times
- **Rotating file logging**: Production-ready logging with DEBUG mode
- **Error handling**: Comprehensive exception handling and status tracking
- **Database health**: Connection monitoring and auto-reconnect
- **Unsolicited message filtering**: Handles modems that send status updates

### Queue Management
- Database-backed message queue
- Status tracking (pending → sent/failed)
- Attempt counter with configurable retries
- Error message logging for troubleshooting
- Diagnostic tools included

### Architecture
- **Modular design**: Clean separation into lib modules
- **Maintainable**: Professional modem wrapper class
- **Testable**: Each component can be tested independently
- **Reusable**: Library modules can be used in other projects
- **Well-documented**: Comprehensive inline documentation

## 📋 Requirements

- Python 3.6 or higher
- USB GSM modem/dongle (tested with Huawei E303S)
- MySQL/MariaDB database
- SIM card installed in modem (PIN disabled recommended)

## 🚀 Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd "SMS Sender"
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

The main dependencies are:
- `python-gsmmodem-new` - Professional GSM modem library
- `mysql-connector-python` - MySQL database connector
- `pyserial` - Serial port communication

3. Configure the application:
   - Edit `config.py` with your database credentials and serial port settings

4. Set up the database:
```sql
CREATE DATABASE smsd;
USE smsd;

CREATE TABLE outbox (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient VARCHAR(255) NOT NULL,
    phone_number VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    attempts INT DEFAULT 3,
    sent_at DATETIME NULL,
    error_message VARCHAR(255) NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_attempts (attempts),
    INDEX idx_created_at (created_at),
    INDEX idx_phone_number (phone_number)
);
```

## Configuration

Edit the `config.py` file to set:

- **MySQL Configuration:**
  - `MYSQL_HOST`: Database server address (default: `127.0.0.1`)
  - `MYSQL_USER`: Database username
  - `MYSQL_PASSWORD`: Database password
  - `MYSQL_DATABASE`: Database name (default: `smsd`)

- **Serial Port Configuration:**
  - `SERIAL_PORT`: COM port for Windows (e.g., `COM5`) or device path for Linux (e.g., `/dev/ttyUSB0`)
  - `SERIAL_BAUD`: Baud rate (default: `115200`)

- **Daemon Settings:**
  - `POLL_INTERVAL`: Time in seconds between database checks (default: `3`)

## Usage

### Verify Modem Setup (First Time)

Before running the daemon, verify your modem is properly configured:

```bash
python identify.py
```

This will display:
- Device and connection info
- Modem manufacturer, model, and firmware
- IMEI and SIM card details
- Network registration and signal strength
- SMS capabilities
- Configuration status

**Example output:**
```
Device               : COM6
Manufacturer         : Huawei
Model                : E303S
Firmware             : 21.157.31.00.850
IMEI                 : 868988011210173
SIM IMSI             : 413027072222336
Signal Strength      : Excellent (25)
Network Operator     : "Dialog"

✓ ALL CHECKS PASSED!
Your modem is properly configured and ready to send SMS.
```

### Starting the Daemon

```bash
python sms_sender.py
```

The daemon will log all activity to `logs/service.log`.

### Viewing Logs

**View recent logs:**
```bash
python view_logs.py
```

**Follow logs in real-time:**
```bash
python view_logs.py --tail
```

**View errors only:**
```bash
python view_logs.py --errors
```

See [LOGGING.md](LOGGING.md) for complete logging documentation.

### Utility Scripts


**Discover Connected Modem:**
```bash
python unidentify.py
```
Interactive script to quickly check connected modem by checking every serial ports.

## Service Installation

To run the SMS daemon as a system service that starts automatically:

**Linux:**
```bash
chmod +x install.sh
sudo bash install.sh
sudo systemctl start sms-daemon
sudo systemctl enable sms-daemon  # Auto-start on boot
```

**Windows:**
```cmd
REM Run as Administrator
install-windows.bat
net start SMSDaemon
```

See [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) for complete installation guide, troubleshooting, and service management.

### Sending SMS

Insert a message into the database:

```sql
INSERT INTO outbox (recipient, phone_number, message, status, attempts) 
VALUES ('John Doe', '+1234567890', 'Hello from SMS Daemon!', 'pending', 3);
```

The daemon will automatically detect and send the message. If sending fails, it will retry up to 3 times before marking it as failed.

### Checking Status

```sql
-- View all messages
SELECT * FROM outbox ORDER BY created_at DESC;

-- View pending messages
SELECT * FROM outbox WHERE status='pending';

-- View sent messages
SELECT * FROM outbox WHERE status='sent';

-- View failed messages (exhausted all retry attempts)
SELECT * FROM outbox WHERE status='failed';

-- View messages that will be retried (still have attempts)
SELECT id, recipient, phone_number, message, attempts, error_message 
FROM outbox 
WHERE status='pending' AND attempts < 3
ORDER BY created_at DESC;
```

## Retry Mechanism

The daemon includes an intelligent retry system:

1. **Default Attempts**: Each message starts with 3 attempts
2. **Auto-Retry**: If sending fails, the daemon automatically retries on the next poll cycle
3. **Attempt Tracking**: Each failed attempt decrements the counter
4. **Final Status**: When attempts reach 0, the message is marked as 'failed'

### Retry Flow

```
Message Created (attempts=3, status='pending')
    ↓
First Attempt Fails → attempts=2, status='pending', error logged
    ↓
Second Attempt Fails → attempts=1, status='pending', error logged
    ↓
Third Attempt Fails → attempts=0, status='failed', error logged
```

### Manual Retry

To manually retry a failed message, reset its attempts:

```sql
-- Retry a specific failed message
UPDATE outbox 
SET status='pending', attempts=3, error_message=NULL 
WHERE id=123;

-- Retry all failed messages
UPDATE outbox 
SET status='pending', attempts=3, error_message=NULL 
WHERE status='failed';
```

## Finding Your Serial Port

### Windows
1. Open Device Manager
2. Expand "Ports (COM & LPT)"
3. Look for your modem (e.g., "USB Serial Port (COM5)")

### Linux
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# or
dmesg | grep tty
```

## Troubleshooting

### Connection Issues

1. **Serial port not found:**
   - Check if the modem is properly connected
   - Verify the correct COM port in `config.py`
   - On Linux, ensure you have permission: `sudo usermod -a -G dialout $USER`

2. **Database connection failed:**
   - Verify MySQL is running
   - Check credentials in `config.py`
   - Ensure the database exists

3. **SMS not sending:**
   - Check if the SIM card is inserted and not PIN-locked
   - Verify the modem has network signal
   - Check modem response in the console output

### Testing the Modem

You can test your modem with a serial terminal (e.g., PuTTY, minicom):

```
AT                    # Should respond: OK
AT+CMGF=1            # Set text mode: OK
AT+CMGS="+1234567890" # Start SMS
> Your message here  # Type message
Ctrl+Z               # Send (0x1A)
```

## Running as a Service

### Windows (using NSSM)

```bash
nssm install SMSDaemon "C:\Python39\python.exe" "D:\Projects\17. Sapix\SMS Sender\sms_sender.py"
nssm start SMSDaemon
```

### Linux (systemd)

Create `/etc/systemd/system/sms-daemon.service`:

```ini
[Unit]
Description=SMS Sender Daemon
After=network.target mysql.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/SMS Sender
ExecStart=/usr/bin/python3 /path/to/SMS Sender/sms_sender.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl enable sms-daemon
sudo systemctl start sms-daemon
sudo systemctl status sms-daemon
```

## 🏗️ Architecture

The SMS Sender is built with a **modular architecture** for maintainability and reusability.

### Project Structure

```
SMS Sender/
├── sms_sender.py          # Main daemon script (150 lines)
├── config.py              # Configuration settings
├── lib/                   # Library modules
│   ├── __init__.py        # Package exports
│   ├── encoding.py        # Message encoding & analysis
│   ├── pdu.py            # PDU format creation
│   ├── modem.py          # Modem communication
│   └── database.py       # Database operations
├── db/
│   └── schema.sql        # Database schema
└── logs/
    └── service.log       # Application logs
```

### Library Modules

#### 📦 `lib/encoding.py`
- Character encoding detection (GSM7 vs UCS2)
- Message part calculation
- Smart message splitting

#### 📦 `lib/pdu.py`
- PDU (Protocol Data Unit) creation
- GSM 7-bit encoding
- Phone number encoding
- Concatenation headers (UDH)

#### 📦 `lib/modem.py`
- Serial modem communication
- PDU mode SMS sending
- Automatic multipart handling
- Response parsing

#### 📦 `lib/database.py`
- MySQL connection management
- Message queue processing
- Retry logic implementation
- Status tracking

### Multipart SMS

Long messages are automatically split and sent with concatenation headers:

**Character Limits:**
- **GSM7**: 160 chars (single) / 153 chars per part (multipart)
- **UCS2** (Unicode/Arabic/Emoji): 70 chars (single) / 67 chars per part (multipart)

**How it works:**
1. Message analyzed for encoding type
2. If needed, split into parts
3. Each part sent with UDH (User Data Header)
4. Recipient's phone automatically combines parts into one message

**Example:**
```
Message: 300 characters
→ Split into 2 parts (153 chars each)
→ Part 1: PDU with UDH (ref=42, part=1/2)
→ Part 2: PDU with UDH (ref=42, part=2/2)
→ Recipient sees: One seamless 300-character message
```

For detailed architecture diagrams, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Documentation

- **[REFACTORING.md](REFACTORING.md)** - Code refactoring details
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture diagrams
- **[MULTIPART_UPDATE.md](MULTIPART_UPDATE.md)** - Multipart SMS implementation
- **[lib/README.md](lib/README.md)** - Library module documentation
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

### Using Library Modules

The library modules can be imported and used independently:

```python
from lib.modem import send_sms
from lib.encoding import calculate_sms_parts
import serial

# Send SMS directly
ser = serial.Serial('COM5', 115200)
response = send_sms(ser, "+1234567890", "Hello, World!")

# Analyze message
parts, limit, encoding = calculate_sms_parts("Your long message here...")
print(f"Will send as {parts} SMS using {encoding}")
```

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions, please open an issue on the repository.

