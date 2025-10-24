"""
Modem Communication Module

Handles all direct modem communication for sending SMS messages.
Supports both single and multipart SMS using PDU mode.
"""

import time
import random
import logging
from .encoding import calculate_sms_parts, split_message
from .pdu import create_pdu

# Get logger
logger = logging.getLogger('SMSDaemon')


def send_sms_pdu(ser, pdu_hex, tpdu_len, modem_timeout=3):
    """
    Send SMS using PDU mode.
    
    Args:
        ser: Serial connection to modem
        pdu_hex: PDU data as hex string
        tpdu_len: TPDU length
        modem_timeout: Response timeout in seconds
    
    Returns:
        str: Modem response
    """
    # Disable echo to reduce noise
    ser.write(b'ATE0\r')
    time.sleep(0.3)
    ser.flushInput()
    
    # Set PDU mode
    ser.write(b'AT+CMGF=0\r')
    time.sleep(0.3)
    ser.flushInput()
    
    # Send PDU length command
    cmd = f'AT+CMGS={tpdu_len}\r'.encode()
    ser.write(cmd)
    time.sleep(0.5)  # Wait a bit longer for prompt
    
    # Clear any unsolicited messages before sending PDU
    ser.flushInput()
    
    # Send PDU data and Ctrl+Z
    ser.write(pdu_hex.encode() + b'\x1A')
    
    # Wait a moment for modem to start processing
    time.sleep(0.5)
    # Wait a moment for modem to start processing
    time.sleep(0.5)
    
    # Wait for response (filtering out unsolicited messages)
    response_parts = []
    max_wait = modem_timeout
    start_time = time.time()
    last_data_time = time.time()
    idle_timeout = 2  # Increased to handle unsolicited messages
    got_any_data = False
    got_success = False
    
    while (time.time() - start_time) < max_wait:
        time.sleep(0.1)
        if ser.in_waiting > 0:
            chunk = ser.read_all().decode(errors='ignore')
            response_parts.append(chunk)
            last_data_time = time.time()
            got_any_data = True
            
            # Filter out unsolicited messages for logging
            filtered_chunk = chunk
            if '^RSSI:' not in chunk and '^DSFLOWRPT:' not in chunk:
                logger.debug(f"Modem chunk received: {repr(chunk)}")
            
            # Check the full response
            full_response = ''.join(response_parts)
            
            # Check for success indicators
            if '+CMGS:' in full_response:
                got_success = True
                logger.debug("Success indicator (+CMGS:) found in response")
                # Wait a bit more to capture complete response
                time.sleep(0.3)
                if ser.in_waiting > 0:
                    final_chunk = ser.read_all().decode(errors='ignore')
                    response_parts.append(final_chunk)
                break
            elif 'OK' in full_response and not got_success:
                # OK found, check if it's for our SMS or just from AT commands
                lines = full_response.split('\r\n')
                ok_count = sum(1 for line in lines if line.strip() == 'OK')
                if ok_count >= 1:  # At least one OK (could be from PDU mode + send)
                    got_success = True
                    logger.debug("Success indicator (OK) found in response")
                    # Wait a bit more to capture complete response
                    time.sleep(0.3)
                    if ser.in_waiting > 0:
                        final_chunk = ser.read_all().decode(errors='ignore')
                        response_parts.append(final_chunk)
                    break
            elif 'ERROR' in full_response or '+CMS ERROR:' in full_response:
                logger.debug("Error indicator found in response")
                break
        else:
            # No data waiting - check if we've been idle too long after getting some data
            if got_any_data and (time.time() - last_data_time) > idle_timeout:
                if got_success:
                    logger.debug(f"Got success, idle timeout ({idle_timeout}s), considering complete")
                else:
                    logger.debug(f"Idle timeout ({idle_timeout}s) after receiving data")
                break
    
    resp = ''.join(response_parts)
    elapsed = time.time() - start_time
    logger.debug(f"Response collection took {elapsed:.1f}s, got {len(resp)} chars")
    return resp


def send_sms(ser, number, text, modem_timeout=3):
    """
    Send SMS using PDU mode with multipart support.
    Messages are automatically combined by the recipient's phone.
    
    Args:
        ser: Serial connection to modem
        number: Destination phone number
        text: Message text
        modem_timeout: Response timeout in seconds
    
    Returns:
        str: Combined modem response(s)
    """
    # Calculate if message needs to be split
    num_parts, chars_per_part, encoding = calculate_sms_parts(text)
    
    logger.debug(f"Message analysis: {len(text)} chars, encoding={encoding}, parts={num_parts}, limit={chars_per_part}")
    
    # Generate a random reference number for this message (for multipart grouping)
    ref_num = random.randint(0, 255)
    
    if num_parts == 1:
        # Single SMS
        logger.debug("Sending as single SMS (PDU mode)")
        pdu_hex, tpdu_len = create_pdu(number, text, ref_num, 1, 1)
        logger.debug(f"PDU: {pdu_hex}, TPDU length: {tpdu_len}")
        return send_sms_pdu(ser, pdu_hex, tpdu_len, modem_timeout)
    else:
        # Multipart SMS - split and send each part
        logger.info(f"Sending as multipart SMS: {num_parts} parts (PDU mode with UDH)")
        message_parts = split_message(text, chars_per_part)
        
        all_responses = []
        for i, part in enumerate(message_parts, 1):
            logger.debug(f"Sending part {i}/{num_parts}: {len(part)} chars")
            pdu_hex, tpdu_len = create_pdu(number, part, ref_num, i, num_parts)
            logger.debug(f"PDU part {i}: {pdu_hex[:50]}..., TPDU length: {tpdu_len}")
            
            response = send_sms_pdu(ser, pdu_hex, tpdu_len, modem_timeout)
            all_responses.append(response)
            
            # Small delay between parts
            if i < num_parts:
                time.sleep(0.5)
        
        # Return combined responses
        combined_response = '\n'.join(all_responses)
        logger.debug(f"All {num_parts} parts sent. Combined response: {repr(combined_response)}")
        return combined_response
