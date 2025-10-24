#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modem Identification Tool
Identifies and displays information about the connected modem/dongle.
Run this before starting the daemon to verify your setup is correct.

Usage: python identify.py
"""

import serial
import time
import sys
from config import SERIAL_PORT, SERIAL_BAUD

# For Windows console UTF-8 support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

def send_at_command(ser, command, wait_time=1.0):
    """Send AT command and return response."""
    try:
        # Clear any existing data
        ser.flushInput()
        ser.flushOutput()
        
        # Send command
        ser.write((command + '\r').encode())
        time.sleep(wait_time)
        
        # Read response
        response = b''
        while ser.in_waiting > 0:
            response += ser.read(ser.in_waiting)
            time.sleep(0.1)
        
        # Decode and clean response
        response_str = response.decode('utf-8', errors='ignore')
        # Remove echo of command and clean up
        lines = [line.strip() for line in response_str.split('\n') if line.strip()]
        # Remove the command echo and OK
        lines = [line for line in lines if line != command and line != 'OK' and line != '']
        
        return '\n'.join(lines) if lines else 'Unknown'
    
    except Exception as e:
        return f'Error: {e}'

def parse_response(response, prefix=''):
    """Parse AT command response and extract value."""
    if 'Error' in response:
        return response
    
    lines = response.split('\n')
    for line in lines:
        if prefix and line.startswith(prefix):
            # Extract value after prefix
            value = line[len(prefix):].strip()
            # Remove quotes if present
            return value.strip('"').strip()
        elif not prefix and line and line not in ['OK', 'ERROR']:
            return line.strip('"').strip()
    
    return 'Unknown'

def identify_modem():
    """Identify and display modem information."""
    print("=" * 70)
    print("MODEM IDENTIFICATION TOOL")
    print("=" * 70)
    print()
    
    # Try to connect to modem
    print(f"Connecting to {SERIAL_PORT} at {SERIAL_BAUD} baud...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)
        time.sleep(0.5)
        print("[OK] Connected successfully!")
        print()
    except serial.SerialException as e:
        print(f"[X] Error: Cannot open serial port {SERIAL_PORT}")
        print(f"  {e}")
        print()
        print("Troubleshooting:")
        print("  - Check if the modem is connected")
        print("  - Verify the COM port in config.py")
        print("  - Close any other programs using the modem")
        print("  - Try unplugging and replugging the modem")
        sys.exit(1)
    except Exception as e:
        print(f"[X] Error: {e}")
        sys.exit(1)
    
    print("-" * 70)
    print("DEVICE INFORMATION")
    print("-" * 70)
    
    # Device/Port
    print(f"Device               : {SERIAL_PORT}")
    print(f"Baud Rate            : {SERIAL_BAUD}")
    
    # Test basic communication
    print()
    print("Testing modem communication...")
    response = send_at_command(ser, 'AT', wait_time=0.5)
    if 'OK' in response or response == '':
        print("[OK] Modem responding to AT commands")
    else:
        print("[!] Warning: Modem may not be responding properly")
    
    print()
    print("-" * 70)
    print("MODEM INFORMATION")
    print("-" * 70)
    
    # Manufacturer
    response = send_at_command(ser, 'AT+CGMI')
    manufacturer = parse_response(response)
    print(f"Manufacturer         : {manufacturer}")
    
    # Model
    response = send_at_command(ser, 'AT+CGMM')
    model = parse_response(response)
    print(f"Model                : {model}")
    
    # Firmware Version
    response = send_at_command(ser, 'AT+CGMR')
    firmware = parse_response(response)
    print(f"Firmware             : {firmware}")
    
    # IMEI (Device Serial Number)
    response = send_at_command(ser, 'AT+GSN')
    imei = parse_response(response)
    if not imei or imei == 'Unknown':
        response = send_at_command(ser, 'AT+CGSN')
        imei = parse_response(response)
    print(f"IMEI                 : {imei}")
    
    print()
    print("-" * 70)
    print("SIM CARD INFORMATION")
    print("-" * 70)
    
    # Check if SIM is ready
    response = send_at_command(ser, 'AT+CPIN?')
    sim_status = parse_response(response, '+CPIN: ')
    print(f"SIM Status           : {sim_status}")
    
    if 'READY' in sim_status:
        # SIM IMSI (International Mobile Subscriber Identity)
        response = send_at_command(ser, 'AT+CIMI', wait_time=1.5)
        imsi = parse_response(response)
        print(f"SIM IMSI             : {imsi}")
        
        # SIM Card ID (ICCID)
        response = send_at_command(ser, 'AT+CCID')
        if 'Unknown' in response or 'Error' in response:
            response = send_at_command(ser, 'AT+ICCID')
        iccid = parse_response(response, '+CCID: ')
        if iccid == 'Unknown':
            iccid = parse_response(response, '+ICCID: ')
        print(f"SIM ICCID            : {iccid}")
        
        # Phone Number (if available)
        response = send_at_command(ser, 'AT+CNUM')
        phone = parse_response(response, '+CNUM: ')
        if phone != 'Unknown' and phone:
            print(f"Phone Number         : {phone}")
        else:
            print(f"Phone Number         : Not stored on SIM")
    else:
        print()
        if 'SIM PIN' in sim_status:
            print("[!] WARNING: SIM card requires PIN!")
            print("  Please unlock the SIM card before using the daemon.")
        elif 'SIM PUK' in sim_status:
            print("[X] ERROR: SIM card is PUK locked!")
            print("  You must unlock the SIM using PUK code.")
        else:
            print("[!] WARNING: SIM card not ready!")
            print("  Check if SIM card is properly inserted.")
    
    print()
    print("-" * 70)
    print("NETWORK INFORMATION")
    print("-" * 70)
    
    # Network Registration Status
    response = send_at_command(ser, 'AT+CREG?', wait_time=1.5)
    reg_status = parse_response(response, '+CREG: ')
    
    # Parse registration status
    if reg_status != 'Unknown':
        parts = reg_status.split(',')
        if len(parts) >= 2:
            status_code = parts[1].strip()
            status_map = {
                '0': 'Not registered, not searching',
                '1': 'Registered, home network',
                '2': 'Not registered, searching',
                '3': 'Registration denied',
                '4': 'Unknown',
                '5': 'Registered, roaming'
            }
            reg_status_text = status_map.get(status_code, f'Status code: {status_code}')
            print(f"Registration         : {reg_status_text}")
        else:
            print(f"Registration         : {reg_status}")
    else:
        print(f"Registration         : Unknown")
    
    # Signal Quality
    response = send_at_command(ser, 'AT+CSQ')
    signal = parse_response(response, '+CSQ: ')
    if signal != 'Unknown' and ',' in signal:
        rssi = signal.split(',')[0].strip()
        try:
            rssi_num = int(rssi)
            if rssi_num == 99:
                signal_text = "No signal"
            elif rssi_num >= 20:
                signal_text = f"Excellent ({rssi})"
            elif rssi_num >= 15:
                signal_text = f"Good ({rssi})"
            elif rssi_num >= 10:
                signal_text = f"Fair ({rssi})"
            elif rssi_num >= 5:
                signal_text = f"Poor ({rssi})"
            else:
                signal_text = f"Very poor ({rssi})"
            print(f"Signal Strength      : {signal_text}")
        except:
            print(f"Signal Strength      : {signal}")
    else:
        print(f"Signal Strength      : Unknown")
    
    # Operator
    response = send_at_command(ser, 'AT+COPS?', wait_time=2.0)
    operator = parse_response(response, '+COPS: ')
    if operator != 'Unknown' and ',' in operator:
        parts = operator.split(',')
        if len(parts) >= 3:
            op_name = parts[2].strip().strip('"')
            print(f"Network Operator     : {op_name}")
        else:
            print(f"Network Operator     : {operator}")
    else:
        print(f"Network Operator     : Unknown")
    
    print()
    print("-" * 70)
    print("SMS CAPABILITIES")
    print("-" * 70)
    
    # Set SMS to text mode and check
    send_at_command(ser, 'AT+CMGF=1', wait_time=0.5)
    response = send_at_command(ser, 'AT+CMGF?')
    sms_mode = parse_response(response, '+CMGF: ')
    mode_text = "Text mode" if sms_mode == '1' else "PDU mode" if sms_mode == '0' else sms_mode
    print(f"SMS Mode             : {mode_text}")
    
    # SMS Service Center
    response = send_at_command(ser, 'AT+CSCA?', wait_time=1.0)
    sms_center = parse_response(response, '+CSCA: ')
    if sms_center != 'Unknown':
        print(f"SMS Service Center   : {sms_center}")
    
    print()
    print("=" * 70)
    print("CONFIGURATION STATUS")
    print("=" * 70)
    print()
    
    # Overall status check
    issues = []
    warnings = []
    
    if 'Error' in manufacturer or manufacturer == 'Unknown':
        issues.append("Cannot communicate with modem")
    
    if 'READY' not in sim_status:
        if 'PIN' in sim_status:
            issues.append("SIM card is PIN locked")
        else:
            issues.append("SIM card not ready")
    
    if 'Unknown' in imsi or 'Error' in imsi:
        warnings.append("Cannot read SIM IMSI")
    
    if reg_status == 'Unknown' or '0' in reg_status or '3' in reg_status:
        warnings.append("Not registered to network")
    
    if 'No signal' in str(signal_text) if 'signal_text' in locals() else True:
        warnings.append("No network signal")
    
    if issues:
        print("[X] ISSUES FOUND:")
        for issue in issues:
            print(f"  • {issue}")
        print()
        print("Please fix these issues before running the SMS daemon.")
    elif warnings:
        print("[!] WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
        print()
        print("The daemon may not work properly until these are resolved.")
    else:
        print("[OK] ALL CHECKS PASSED!")
        print()
        print("Your modem is properly configured and ready to send SMS.")
        print("You can now run: python sms_sender.py")
    
    print()
    print("=" * 70)
    
    # Close serial connection
    ser.close()

if __name__ == "__main__":
    try:
        identify_modem()
    except KeyboardInterrupt:
        print("\n\nIdentification cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
