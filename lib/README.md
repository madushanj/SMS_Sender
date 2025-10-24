# SMS Sender Library Modules

This directory contains modular components for the SMS Sender daemon.

## Module Structure

```
lib/
├── __init__.py         # Package initialization and exports
├── encoding.py         # Message encoding and analysis
├── pdu.py             # PDU format creation
├── modem.py           # Modem communication
└── database.py        # Database operations
```

## Modules

### `encoding.py` - Message Encoding and Analysis

Handles character encoding detection and message preparation.

**Functions:**
- `is_gsm7_compatible(text)` - Check if text uses GSM 7-bit charset
- `calculate_sms_parts(text)` - Calculate SMS parts needed
- `split_message(text, chars_per_part)` - Split long messages

**Character Limits:**
- GSM7: 160 chars (single) / 153 chars per part (multipart)
- UCS2: 70 chars (single) / 67 chars per part (multipart)

### `pdu.py` - PDU Format Creation

Creates Protocol Data Units for SMS transmission.

**Functions:**
- `encode_gsm7(text)` - Encode text to GSM 7-bit format
- `encode_gsm7_with_padding(text, padding_bits)` - GSM7 with UDH padding
- `encode_phone_number(phone)` - Encode phone number for PDU
- `create_pdu(phone, text, ref_num, part_num, total_parts)` - Create complete PDU

**PDU Features:**
- Supports both GSM7 and UCS2 encoding
- Automatic concatenation headers (UDH) for multipart
- International and national phone number formats

### `modem.py` - Modem Communication

Handles all serial communication with the GSM modem.

**Functions:**
- `send_sms_pdu(ser, pdu_hex, tpdu_len, modem_timeout)` - Send single PDU
- `send_sms(ser, number, text, modem_timeout)` - Send SMS (auto multipart)

**Features:**
- Automatic multipart detection and splitting
- PDU mode (AT+CMGF=0) for reliability
- Response parsing and error detection
- Configurable timeouts

### `database.py` - Database Operations

Manages MySQL database interactions for message queue.

**Functions:**
- `connect_database(config)` - Connect to MySQL with proper settings
- `process_pending_sms(cursor, db, ser, send_sms_func, modem_timeout)` - Process message queue

**Features:**
- Automatic retry logic (3 attempts)
- Status management (pending → sent/failed)
- Error message logging
- Connection health monitoring

## Usage Example

```python
from lib.modem import send_sms
from lib.database import connect_database, process_pending_sms
import serial

# Connect to modem
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)

# Send single SMS
response = send_sms(ser, "+1234567890", "Hello, World!", modem_timeout=3)

# Or process database queue
db_config = {
    'host': 'localhost',
    'user': 'sms_user',
    'password': 'password',
    'database': 'sms_db'
}

db, cursor = connect_database(db_config)
cursor = process_pending_sms(cursor, db, ser, send_sms, 3)
```

## Import Shortcuts

The `__init__.py` file provides convenient imports:

```python
from lib import send_sms, calculate_sms_parts, create_pdu
```

## Dependencies

- **pyserial** - Serial communication with modem
- **mysql-connector-python** - MySQL database access
- **Python 3.7+** - Standard library features

## Error Handling

All modules use the 'SMSDaemon' logger for consistent logging:

```python
import logging
logger = logging.getLogger('SMSDaemon')
```

Log levels:
- DEBUG: Detailed modem responses, PDU data
- INFO: Message send status, connection events
- WARNING: Retry attempts, reconnections
- ERROR: Failed messages, exceptions
- CRITICAL: Fatal errors (startup failures)
