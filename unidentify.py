#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modem Auto-Detection Tool
Automatically scans all available serial ports to find the GSM modem/dongle,
displays its information, and optionally updates the config.py with the correct port.

Usage: python unidentify.py
"""

import serial
import serial.tools.list_ports
import time
import sys
import platform
import re

# For Windows console UTF-8 support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


def detect_os():
    """Detect the operating system."""
    system = platform.system()
    if system == 'Windows':
        return 'Windows'
    elif system == 'Linux':
        return 'Linux'
    elif system == 'Darwin':
        return 'macOS'
    else:
        return system


def get_available_ports(os_type):
    """Get list of available serial ports based on OS."""
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        return []
    
    # Filter and format ports based on OS
    available_ports = []
    for port in ports:
        port_info = {
            'device': port.device,
            'description': port.description,
            'hwid': port.hwid,
            'manufacturer': port.manufacturer if hasattr(port, 'manufacturer') else 'Unknown',
            'product': port.product if hasattr(port, 'product') else 'Unknown',
            'vid': port.vid if hasattr(port, 'vid') else None,
            'pid': port.pid if hasattr(port, 'pid') else None,
        }
        available_ports.append(port_info)
    
    return available_ports


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
        
        return '\n'.join(lines) if lines else 'OK'
    
    except Exception as e:
        return f'Error: {e}'


def parse_response(response, prefix=''):
    """Parse AT command response and extract value."""
    if 'Error' in response:
        return None
    
    lines = response.split('\n')
    for line in lines:
        if prefix and line.startswith(prefix):
            # Extract value after prefix
            value = line[len(prefix):].strip()
            # Remove quotes if present
            return value.strip('"').strip()
        elif not prefix and line and line not in ['OK', 'ERROR']:
            return line.strip('"').strip()
    
    return None


def test_modem_on_port(port_device, baud_rates=[9600, 115200, 19200, 57600]):
    """
    Test if a modem is connected to the specified port.
    Tries multiple baud rates.
    
    Returns: dict with modem info if found, None otherwise
    """
    for baud in baud_rates:
        try:
            # Try to open the port
            ser = serial.Serial(port_device, baud, timeout=1)
            time.sleep(0.5)
            
            # Test basic AT command
            response = send_at_command(ser, 'AT', wait_time=0.5)
            
            if 'OK' in response or response == 'OK' or response == '':
                # This looks like a modem! Get more info
                modem_info = {
                    'port': port_device,
                    'baud': baud,
                    'manufacturer': 'Unknown',
                    'model': 'Unknown',
                    'firmware': 'Unknown',
                    'imei': 'Unknown',
                    'sim_status': 'Unknown'
                }
                
                # Get manufacturer
                resp = send_at_command(ser, 'AT+CGMI')
                manufacturer = parse_response(resp)
                if manufacturer:
                    modem_info['manufacturer'] = manufacturer
                
                # Get model
                resp = send_at_command(ser, 'AT+CGMM')
                model = parse_response(resp)
                if model:
                    modem_info['model'] = model
                
                # Get firmware
                resp = send_at_command(ser, 'AT+CGMR')
                firmware = parse_response(resp)
                if firmware:
                    modem_info['firmware'] = firmware
                
                # Get IMEI
                resp = send_at_command(ser, 'AT+GSN')
                imei = parse_response(resp)
                if not imei:
                    resp = send_at_command(ser, 'AT+CGSN')
                    imei = parse_response(resp)
                if imei:
                    modem_info['imei'] = imei
                
                # Get SIM status
                resp = send_at_command(ser, 'AT+CPIN?')
                sim_status = parse_response(resp, '+CPIN: ')
                if sim_status:
                    modem_info['sim_status'] = sim_status
                
                ser.close()
                return modem_info
            
            ser.close()
            
        except (serial.SerialException, OSError) as e:
            # Port is not accessible or not a modem
            continue
        except Exception as e:
            # Other errors, skip this port
            continue
    
    return None


def scan_for_modems(os_type):
    """Scan all available ports for GSM modems."""
    print("=" * 70)
    print("MODEM AUTO-DETECTION TOOL")
    print("=" * 70)
    print()
    print(f"Operating System     : {os_type}")
    print()
    
    # Get available ports
    print("Scanning for available serial ports...")
    ports = get_available_ports(os_type)
    
    if not ports:
        print("[!] No serial ports found on this system.")
        print()
        print("Troubleshooting:")
        print("  - Check if the modem/dongle is plugged in")
        print("  - Check if drivers are installed (especially on Windows)")
        print("  - Try a different USB port")
        return None
    
    print(f"[OK] Found {len(ports)} serial port(s)")
    print()
    
    # Display found ports
    print("-" * 70)
    print("AVAILABLE SERIAL PORTS")
    print("-" * 70)
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port['device']}")
        print(f"   Description  : {port['description']}")
        if port['manufacturer'] != 'Unknown':
            print(f"   Manufacturer : {port['manufacturer']}")
        if port['product'] != 'Unknown':
            print(f"   Product      : {port['product']}")
        if port['vid'] and port['pid']:
            print(f"   VID:PID      : {port['vid']:04X}:{port['pid']:04X}")
        print()
    
    # Test each port for modem
    print("-" * 70)
    print("TESTING PORTS FOR GSM MODEM")
    print("-" * 70)
    print()
    
    found_modems = []
    
    for port in ports:
        print(f"Testing {port['device']}...", end=' ')
        sys.stdout.flush()
        
        modem_info = test_modem_on_port(port['device'])
        
        if modem_info:
            print("[MODEM FOUND!]")
            found_modems.append(modem_info)
        else:
            print("[Not a modem]")
    
    print()
    
    return found_modems


def display_modem_info(modem_info):
    """Display detailed information about the found modem."""
    print("=" * 70)
    print("MODEM DETAILS")
    print("=" * 70)
    print()
    print(f"Port                 : {modem_info['port']}")
    print(f"Baud Rate            : {modem_info['baud']}")
    print(f"Manufacturer         : {modem_info['manufacturer']}")
    print(f"Model                : {modem_info['model']}")
    print(f"Firmware             : {modem_info['firmware']}")
    print(f"IMEI                 : {modem_info['imei']}")
    print(f"SIM Status           : {modem_info['sim_status']}")
    print()


def update_config_file(port, baud):
    """Update the config.py file with the correct port and baud rate."""
    try:
        # Read the current config file
        with open('config.py', 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Update SERIAL_PORT
        config_content = re.sub(
            r"SERIAL_PORT = ['\"].*?['\"]",
            f"SERIAL_PORT = '{port}'",
            config_content
        )
        
        # Update SERIAL_BAUD
        config_content = re.sub(
            r"SERIAL_BAUD = \d+",
            f"SERIAL_BAUD = {baud}",
            config_content
        )
        
        # Write the updated config back
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return True
    except Exception as e:
        print(f"[X] Error updating config.py: {e}")
        return False


def main():
    """Main function."""
    # Detect OS
    os_type = detect_os()
    
    # Scan for modems
    found_modems = scan_for_modems(os_type)
    
    if not found_modems:
        print("=" * 70)
        print("[X] NO GSM MODEM FOUND")
        print("=" * 70)
        print()
        print("No GSM modem/dongle was detected on any serial port.")
        print()
        print("Troubleshooting:")
        print("  1. Check if the modem is properly connected")
        print("  2. Install necessary drivers (especially on Windows)")
        print("  3. Try unplugging and replugging the modem")
        print("  4. Check if another program is using the modem")
        print("  5. Try running this script with administrator/sudo privileges")
        print()
        return
    
    # Display found modems
    print("=" * 70)
    print(f"FOUND {len(found_modems)} GSM MODEM(S)")
    print("=" * 70)
    print()
    
    if len(found_modems) == 1:
        # Only one modem found
        modem = found_modems[0]
        display_modem_info(modem)
        
        # Ask user if they want to update config
        print("-" * 70)
        response = input("Update config.py with this modem? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            if update_config_file(modem['port'], modem['baud']):
                print()
                print("[OK] config.py has been updated successfully!")
                print()
                print(f"SERIAL_PORT = '{modem['port']}'")
                print(f"SERIAL_BAUD = {modem['baud']}")
                print()
                print("You can now run: python identify.py")
                print("Or start the daemon: python sms_sender.py")
            else:
                print()
                print("[!] Failed to update config.py")
                print("Please manually update the following values:")
                print(f"  SERIAL_PORT = '{modem['port']}'")
                print(f"  SERIAL_BAUD = {modem['baud']}")
        else:
            print()
            print("Config.py was not updated.")
            print("To use this modem, manually set:")
            print(f"  SERIAL_PORT = '{modem['port']}'")
            print(f"  SERIAL_BAUD = {modem['baud']}")
    
    else:
        # Multiple modems found
        print("Multiple GSM modems detected:")
        print()
        
        for i, modem in enumerate(found_modems, 1):
            print(f"{i}. {modem['port']} - {modem['manufacturer']} {modem['model']}")
            print(f"   IMEI: {modem['imei']}")
            print(f"   SIM Status: {modem['sim_status']}")
            print()
        
        print("-" * 70)
        try:
            choice = input(f"Which modem would you like to use? (1-{len(found_modems)}, or 0 to cancel): ").strip()
            choice_num = int(choice)
            
            if choice_num == 0:
                print()
                print("Operation cancelled.")
                return
            
            if 1 <= choice_num <= len(found_modems):
                selected_modem = found_modems[choice_num - 1]
                print()
                display_modem_info(selected_modem)
                
                print("-" * 70)
                response = input("Update config.py with this modem? (y/n): ").strip().lower()
                
                if response == 'y' or response == 'yes':
                    if update_config_file(selected_modem['port'], selected_modem['baud']):
                        print()
                        print("[OK] config.py has been updated successfully!")
                        print()
                        print(f"SERIAL_PORT = '{selected_modem['port']}'")
                        print(f"SERIAL_BAUD = {selected_modem['baud']}")
                        print()
                        print("You can now run: python identify.py")
                        print("Or start the daemon: python sms_sender.py")
                    else:
                        print()
                        print("[!] Failed to update config.py")
                        print("Please manually update the following values:")
                        print(f"  SERIAL_PORT = '{selected_modem['port']}'")
                        print(f"  SERIAL_BAUD = {selected_modem['baud']}")
                else:
                    print()
                    print("Config.py was not updated.")
            else:
                print()
                print("[!] Invalid choice.")
        
        except ValueError:
            print()
            print("[!] Invalid input.")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
