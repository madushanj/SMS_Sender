"""
Configuration file for SMS Sender Daemon
Edit these values according to your setup
"""

# MySQL Database Configuration
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'root'  # Change this to your MySQL password
MYSQL_DATABASE = 'smsd'

# Serial Port Configuration
SERIAL_PORT = 'COM6'  # Windows: COM1, COM2, etc. | Linux: /dev/ttyUSB0, /dev/ttyACM0, etc.
SERIAL_BAUD = 9600  # Baud rate (common: 9600, 115200)

# Daemon Settings
POLL_INTERVAL = 20  # Time in seconds between database checks
MODEM_RESPONSE_TIMEOUT = 30  # Maximum seconds to wait for modem response (increased for multipart SMS)

# Logging Settings
LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL (Changed to DEBUG for troubleshooting)
LOG_TO_CONSOLE = True  # Set to False for pure background operation
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB per log file
LOG_BACKUP_COUNT = 10  # Keep 10 backup files
