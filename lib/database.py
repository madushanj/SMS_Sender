"""
Database Operations Module

Handles all database interactions for the SMS sender daemon.
"""

import logging
import mysql.connector
import time

# Get logger
logger = logging.getLogger('SMSDaemon')


def process_pending_sms_v2(cursor, db, modem):
    """
    Fetch and send pending SMS messages using python-gsmmodem library.
    
    Args:
        cursor: MySQL cursor
        db: MySQL database connection
        modem: ModemSMS instance from lib.modem_gsmlib
    
    Returns:
        cursor: Updated cursor (may be new instance)
    """
    # Ensure database connection is alive and refresh cursor
    try:
        db.ping(reconnect=True)
        db.rollback()  # Roll back any uncommitted transaction
        try:
            cursor.close()
        except:
            pass
        cursor = db.cursor(dictionary=True)
    except Exception as e:
        logger.error(f"Database connection refresh failed: {e}")
        try:
            cursor = db.cursor(dictionary=True)
        except:
            return cursor
    
    # Get pending messages that still have attempts remaining
    try:
        query = "SELECT * FROM outbox WHERE status='pending' AND attempts > 0 ORDER BY id LIMIT 5"
        logger.debug(f"Executing query: {query}")
        cursor.execute(query)
        messages = cursor.fetchall()
        logger.debug(f"Query returned {len(messages)} row(s)")
    except Exception as e:
        logger.error(f"Failed to fetch pending messages: {e}")
        return cursor
    
    if messages:
        logger.debug(f"Found {len(messages)} pending message(s)")
        for msg in messages:
            logger.debug(f"  - ID: {msg['id']}, Phone: {msg['phone_number']}, Status: {msg['status']}, Attempts: {msg['attempts']}")
    else:
        logger.debug("No pending messages found in this cycle")
    
    for msg in messages:
        msg_id = msg['id']
        phone = msg['phone_number']
        recipient = msg['recipient']
        text = msg['message']
        attempts_left = msg['attempts']
        
        logger.info(f"Sending SMS {msg_id} -> {recipient} ({phone}) [Attempts left: {attempts_left}]")
        
        send_start = time.time()
        try:
            # Use the new modem library - it handles multipart automatically
            success, result_msg = modem.send_sms(phone, text)
            send_duration = time.time() - send_start
            
            if success:
                cursor.execute(
                    "UPDATE outbox SET status='sent', sent_at=NOW(), updated_at=NOW() WHERE id=%s",
                    (msg_id,)
                )
                logger.info(f"[OK] SMS {msg_id} sent successfully to {phone} (took {send_duration:.1f}s)")
            else:
                # SMS failed, decrement attempts
                new_attempts = attempts_left - 1
                
                if new_attempts <= 0:
                    # No more attempts, mark as failed
                    cursor.execute(
                        "UPDATE outbox SET status='failed', attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                        (new_attempts, result_msg[:255], msg_id)
                    )
                    logger.error(f"[FAIL] SMS {msg_id} FAILED - No attempts remaining. Error: {result_msg}")
                else:
                    # Still have attempts, keep as pending
                    cursor.execute(
                        "UPDATE outbox SET attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                        (new_attempts, result_msg[:255], msg_id)
                    )
                    logger.warning(f"[RETRY] SMS {msg_id} failed - {new_attempts} attempts remaining. Error: {result_msg}")
            
            db.commit()

        except Exception as e:
            # Exception occurred, decrement attempts
            logger.exception(f"Exception sending SMS {msg_id}: {e}")
            new_attempts = attempts_left - 1
            
            if new_attempts <= 0:
                # No more attempts, mark as failed
                cursor.execute(
                    "UPDATE outbox SET status='failed', attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                    (new_attempts, str(e)[:255], msg_id)
                )
                logger.error(f"[FAIL] SMS {msg_id} FAILED - No attempts remaining (Exception)")
            else:
                # Still have attempts, keep as pending
                cursor.execute(
                    "UPDATE outbox SET attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                    (new_attempts, str(e)[:255], msg_id)
                )
                logger.warning(f"[RETRY] SMS {msg_id} error - {new_attempts} attempts remaining (Exception)")
            
            db.commit()
    
    # Return the cursor (might be a new one)
    return cursor



def process_pending_sms(cursor, db, ser, send_sms_func, modem_timeout=3):
    """
    Fetch and send pending SMS messages with retry logic.
    
    Args:
        cursor: MySQL cursor
        db: MySQL database connection
        ser: Serial connection to modem
        send_sms_func: Function to call for sending SMS
        modem_timeout: Modem response timeout
    
    Returns:
        cursor: Updated cursor (may be new instance)
    """
    # Ensure database connection is alive and refresh cursor
    try:
        db.ping(reconnect=True)
        # Start a fresh transaction to avoid stale reads
        db.rollback()  # Roll back any uncommitted transaction
        # Close old cursor and create fresh one to avoid caching
        try:
            cursor.close()
        except:
            pass
        cursor = db.cursor(dictionary=True)
    except Exception as e:
        logger.error(f"Database connection refresh failed: {e}")
        # Try to create new cursor anyway
        try:
            cursor = db.cursor(dictionary=True)
        except:
            return cursor
    
    # Get pending messages that still have attempts remaining
    try:
        query = "SELECT * FROM outbox WHERE status='pending' AND attempts > 0 ORDER BY id LIMIT 5"
        logger.debug(f"Executing query: {query}")
        cursor.execute(query)
        messages = cursor.fetchall()
        logger.debug(f"Query returned {len(messages)} row(s)")
    except Exception as e:
        logger.error(f"Failed to fetch pending messages: {e}")
        return cursor
    
    if messages:
        logger.debug(f"Found {len(messages)} pending message(s)")
        for msg in messages:
            logger.debug(f"  - ID: {msg['id']}, Phone: {msg['phone_number']}, Status: {msg['status']}, Attempts: {msg['attempts']}")
    else:
        logger.debug("No pending messages found in this cycle")
    
    for msg in messages:
        msg_id = msg['id']
        phone = msg['phone_number']
        recipient = msg['recipient']
        text = msg['message']
        attempts_left = msg['attempts']
        
        logger.info(f"Sending SMS {msg_id} -> {recipient} ({phone}) [Attempts left: {attempts_left}]")
        
        import time
        send_start = time.time()
        try:
            resp = send_sms_func(ser, phone, text, modem_timeout)
            send_duration = time.time() - send_start
            logger.debug(f"Modem full response for SMS {msg_id}: {repr(resp.strip())}")

            # Check if SMS was sent successfully
            # For multipart SMS, we need to check if all parts succeeded
            # Success indicators: +CMGS: (with message ID) or just OK
            # Failure indicators: ERROR, +CMS ERROR, timeout with no response
            is_success = False
            error_msg = None
            
            # Clean up the response for checking
            resp_clean = resp.strip().upper()
            
            # Count success and error indicators (important for multipart)
            cmgs_count = resp_clean.count('+CMGS:')
            ok_count = resp_clean.count('OK')
            error_count = resp_clean.count('ERROR')
            
            if '+CMGS:' in resp_clean and error_count == 0:
                # Definitive success - modem returned message ID(s) and no errors
                is_success = True
                logger.debug(f"Success: {cmgs_count} +CMGS found in response, no errors")
            elif error_count > 0 or '+CMS ERROR:' in resp_clean:
                # Definitive failure - actual error from modem
                is_success = False
                error_msg = resp.strip()[:255]
                logger.debug(f"Failure: {error_count} ERROR(s) found - {error_msg}")
            elif 'OK' in resp_clean and len(resp_clean) > 2:
                # OK with some content - likely success
                is_success = True
                logger.debug("Success: OK found in response with content")
            elif len(resp.strip()) == 0:
                # Empty response - modem didn't respond
                # Behavior controlled by config (imported in main)
                # For now, assume failure on timeout
                is_success = False
                error_msg = f"No response from modem (timeout after {modem_timeout}s)"
                logger.debug("Failure: Empty response (timeout)")
            else:
                # Response received but ambiguous - check length
                if len(resp.strip()) > 5:
                    # Got substantial response, likely success
                    is_success = True
                    logger.debug(f"Success: Substantial response ({len(resp)} chars), assuming sent")
                else:
                    # Very short response - ambiguous
                    is_success = False
                    error_msg = f"Ambiguous modem response: {resp.strip()[:50]}"
                    logger.debug(f"Failure: Ambiguous - {error_msg}")
            
            if is_success:
                cursor.execute(
                    "UPDATE outbox SET status='sent', sent_at=NOW(), updated_at=NOW() WHERE id=%s",
                    (msg_id,)
                )
                logger.info(f"[OK] SMS {msg_id} sent successfully to {phone} (took {send_duration:.1f}s)")
            else:
                # SMS failed, decrement attempts
                new_attempts = attempts_left - 1
                final_error = error_msg or resp.strip()[:255] or "Unknown error"
                
                if new_attempts <= 0:
                    # No more attempts, mark as failed
                    cursor.execute(
                        "UPDATE outbox SET status='failed', attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                        (new_attempts, final_error, msg_id)
                    )
                    logger.error(f"[FAIL] SMS {msg_id} FAILED - No attempts remaining. Error: {final_error}")
                else:
                    # Still have attempts, keep as pending
                    cursor.execute(
                        "UPDATE outbox SET attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                        (new_attempts, final_error, msg_id)
                    )
                    logger.warning(f"[RETRY] SMS {msg_id} failed - {new_attempts} attempts remaining. Error: {final_error}")
            
            db.commit()

        except Exception as e:
            # Exception occurred, decrement attempts
            logger.exception(f"Exception sending SMS {msg_id}: {e}")
            new_attempts = attempts_left - 1
            
            if new_attempts <= 0:
                # No more attempts, mark as failed
                cursor.execute(
                    "UPDATE outbox SET status='failed', attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                    (new_attempts, str(e)[:255], msg_id)
                )
                logger.error(f"[FAIL] SMS {msg_id} FAILED - No attempts remaining (Exception)")
            else:
                # Still have attempts, keep as pending
                cursor.execute(
                    "UPDATE outbox SET attempts=%s, error_message=%s, updated_at=NOW() WHERE id=%s",
                    (new_attempts, str(e)[:255], msg_id)
                )
                logger.warning(f"[RETRY] SMS {msg_id} error - {new_attempts} attempts remaining (Exception)")
            
            db.commit()
    
    # Return the cursor (might be a new one)
    return cursor


def connect_database(config):
    """
    Connect to MySQL database with proper configuration.
    
    Args:
        config: Database configuration dictionary
    
    Returns:
        tuple: (connection, cursor)
    """
    db = mysql.connector.connect(**config, autocommit=False)
    
    # Set isolation level to READ COMMITTED to avoid stale reads
    cursor = db.cursor()
    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    cursor.close()
    
    cursor = db.cursor(dictionary=True)
    logger.info(f"Connected to MySQL database '{config['database']}' at {config['host']}")
    
    return db, cursor
