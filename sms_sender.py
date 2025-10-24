#!/usr/bin/env python3
"""
SMS Sender Daemon - Main Module

A daemon that processes pending SMS messages from a MySQL database
and sends them via a GSM modem. Supports multipart SMS with automatic
concatenation for long messages.
"""

import time
import sys
import logging
from logging.handlers import RotatingFileHandler

# Import configuration
from config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    SERIAL_PORT, SERIAL_BAUD, POLL_INTERVAL, MODEM_RESPONSE_TIMEOUT,
    LOG_LEVEL, LOG_TO_CONSOLE, LOG_MAX_BYTES, LOG_BACKUP_COUNT
)

# Import library modules
from lib.modem_gsmlib import ModemSMS
from lib.database import process_pending_sms_v2, connect_database


# MySQL Configuration
MYSQL_CONFIG = {
    'host': MYSQL_HOST,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE,
}


def setup_logging():
    """Setup rotating file logging with UTF-8 support."""
    logger = logging.getLogger('SMSDaemon')
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Create logs directory if it doesn't exist
    import os
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Rotating file handler (supports UTF-8 for Unicode characters)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'service.log'),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Optional console handler with Windows compatibility
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        
        # For Windows, set errors='replace' to avoid Unicode errors
        if sys.platform == 'win32':
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        
        logger.addHandler(console_handler)
    
    return logger


def main():
    """Main daemon loop."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("SMS Daemon Starting v2.0.0 (python-gsmmodem)")
    logger.info("=" * 60)
    
    # Connect to modem using the library
    modem = ModemSMS(SERIAL_PORT, SERIAL_BAUD, MODEM_RESPONSE_TIMEOUT)
    if not modem.connect():
        logger.critical(f"Cannot connect to modem on {SERIAL_PORT}")
        sys.exit(1)

    # Connect to MySQL
    try:
        db, cursor = connect_database(MYSQL_CONFIG)
    except Exception as e:
        logger.critical(f"Cannot connect to MySQL: {e}")
        modem.disconnect()
        sys.exit(1)

    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"Modem response timeout: {MODEM_RESPONSE_TIMEOUT} seconds")
    logger.info("Multipart SMS: Enabled (automatic via gsmmodem library)")
    
    # Check network status
    network_ok, network_msg = modem.check_network()
    if network_ok:
        logger.info(f"Network: {network_msg}")
    else:
        logger.warning(f"Network: {network_msg}")
    
    logger.info("Starting SMS daemon loop...")
    logger.info("=" * 60)
    
    loop_count = 0
    try:
        while True:
            try:
                loop_count += 1
                logger.debug(f"Poll cycle #{loop_count}")
                
                # Check and refresh database connection periodically
                if loop_count % 10 == 0:  # Every 10 cycles
                    try:
                        db.ping(reconnect=True)
                        logger.debug("Database connection verified")
                    except Exception as e:
                        logger.warning(f"Database reconnection: {e}")
                        db, cursor = connect_database(MYSQL_CONFIG)
                        logger.info("Database reconnected")
                
                # Process pending SMS with new modem implementation
                cursor = process_pending_sms_v2(cursor, db, modem)
                
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Closing connections...")
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
        modem.disconnect()
        logger.info("Shutdown complete")

        logger.info("SMS Daemon stopped")


if __name__ == "__main__":
    main()
