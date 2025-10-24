"""
PDU (Protocol Data Unit) Creation Module

Handles GSM 7-bit encoding and PDU format creation for SMS messages.
Supports both single and multipart SMS with concatenation headers.
"""

from .encoding import is_gsm7_compatible


def encode_gsm7(text):
    """
    Encode text to GSM 7-bit format (septets packed into octets).
    
    Args:
        text: Text to encode
    
    Returns:
        bytes: Encoded data as bytes
    """
    # GSM 7-bit character table
    gsm7_basic = (
        "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
        "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
    )
    gsm7_extended = {
        '\f': 0x0A, '^': 0x14, '{': 0x28, '}': 0x29, '\\': 0x2F,
        '[': 0x3C, '~': 0x3D, ']': 0x3E, '|': 0x40, '€': 0x65
    }
    
    # Convert to septet values
    septets = []
    for char in text:
        if char in gsm7_extended:
            septets.append(0x1B)  # ESC character
            septets.append(gsm7_extended[char])
        else:
            try:
                septets.append(gsm7_basic.index(char))
            except ValueError:
                septets.append(0x3F)  # '?' as fallback
    
    # Pack 7-bit septets into 8-bit octets
    octets = []
    shift = 0
    carry = 0
    
    for i, septet in enumerate(septets):
        if shift == 7:
            shift = 0
            carry = 0
            continue
        
        octet = ((septet << shift) | carry) & 0xFF
        octets.append(octet)
        carry = septet >> (7 - shift)
        shift += 1
        
        if i == len(septets) - 1 and carry:
            octets.append(carry)
    
    return bytes(octets)


def encode_gsm7_with_padding(text, padding_bits):
    """
    Encode GSM7 text with bit padding for UDH alignment.
    
    Args:
        text: Text to encode
        padding_bits: Number of padding bits needed
    
    Returns:
        bytes: Encoded data with padding
    """
    gsm7_basic = (
        "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
        "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
    )
    gsm7_extended = {
        '\f': 0x0A, '^': 0x14, '{': 0x28, '}': 0x29, '\\': 0x2F,
        '[': 0x3C, '~': 0x3D, ']': 0x3E, '|': 0x40, '€': 0x65
    }
    
    # Convert to septet values
    septets = []
    for char in text:
        if char in gsm7_extended:
            septets.append(0x1B)
            septets.append(gsm7_extended[char])
        else:
            try:
                septets.append(gsm7_basic.index(char))
            except ValueError:
                septets.append(0x3F)
    
    # Pack with padding
    octets = []
    shift = padding_bits
    carry = 0
    
    for i, septet in enumerate(septets):
        if shift == 7:
            shift = 0
            carry = 0
            continue
        
        octet = ((septet << shift) | carry) & 0xFF
        octets.append(octet)
        carry = septet >> (7 - shift)
        shift += 1
        
        if i == len(septets) - 1 and carry:
            octets.append(carry)
    
    return bytes(octets)


def encode_phone_number(phone):
    """
    Encode phone number for PDU format.
    
    Args:
        phone: Phone number string (can include '+' for international)
    
    Returns:
        tuple: (type_of_number, encoded_phone_bytes)
    """
    # Remove any non-digit characters except '+'
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Handle international format
    if phone.startswith('+'):
        ton = 0x91  # International format
        phone = phone[1:]
    else:
        ton = 0x81  # Unknown format / national
    
    # Swap digit pairs (e.g., "1234" -> "2143")
    if len(phone) % 2:
        phone += 'F'
    
    swapped = ''.join(phone[i+1] + phone[i] for i in range(0, len(phone), 2))
    
    return ton, bytes.fromhex(swapped)


def create_pdu(phone, text, ref_num, part_num, total_parts):
    """
    Create PDU for SMS with concatenation support.
    
    Args:
        phone: Destination phone number
        text: Message text
        ref_num: Reference number for multipart SMS (0-255)
        part_num: Current part number (1-based)
        total_parts: Total number of parts
    
    Returns:
        tuple: (pdu_hex_string, tpdu_length)
    """
    # Determine encoding
    if is_gsm7_compatible(text):
        dcs = 0x00  # GSM 7-bit
        user_data = encode_gsm7(text)
        udl = len(text)  # User Data Length in septets for GSM7
    else:
        dcs = 0x08  # UCS2 (16-bit)
        user_data = text.encode('utf-16-be')
        udl = len(user_data)  # User Data Length in octets for UCS2
    
    # Encode phone number
    ton, phone_encoded = encode_phone_number(phone)
    phone_len = len(phone.replace('+', ''))
    
    # Build PDU
    pdu = []
    
    # SMSC (use default, length = 0)
    pdu.append(0x00)
    
    # PDU type (SMS-SUBMIT with UDH for multipart)
    if total_parts > 1:
        pdu_type = 0x41  # SMS-SUBMIT + UDHI (User Data Header Indicator)
    else:
        pdu_type = 0x01  # SMS-SUBMIT
    pdu.append(pdu_type)
    
    # Message reference (0x00 = let modem set)
    pdu.append(0x00)
    
    # Destination address length
    pdu.append(phone_len)
    
    # Type of number
    pdu.append(ton)
    
    # Phone number (swapped)
    pdu.extend(phone_encoded)
    
    # Protocol identifier
    pdu.append(0x00)
    
    # Data coding scheme
    pdu.append(dcs)
    
    # Validity period (not used, but can add 0xAA for 4 days)
    # pdu.append(0xAA)
    
    # User Data Header (for multipart)
    if total_parts > 1:
        udh = []
        udh.append(0x00)  # IEI: Concatenated short messages, 8-bit reference
        udh.append(0x03)  # IEDL: Length of header data
        udh.append(ref_num & 0xFF)  # Reference number (same for all parts)
        udh.append(total_parts)  # Total parts
        udh.append(part_num)  # This part number
        
        udh_len = len(udh) + 1  # +1 for UDHL
        
        # Adjust UDL based on encoding
        if dcs == 0x00:  # GSM7
            # For GSM7, we need to account for padding
            padding_bits = 7 - ((udh_len + 1) * 8) % 7
            if padding_bits == 7:
                padding_bits = 0
            # UDL = header length + text length + padding
            total_udl = udh_len + 1 + len(text)
            if padding_bits > 0:
                total_udl += 1
            pdu.append(total_udl)
        else:  # UCS2
            pdu.append(udh_len + 1 + udl)
        
        # Add UDHL and UDH
        pdu.append(udh_len)
        pdu.extend(udh)
        
        # Add padding for GSM7
        if dcs == 0x00 and padding_bits > 0:
            # Re-encode with padding
            user_data = encode_gsm7_with_padding(text, padding_bits)
        
        pdu.extend(user_data)
    else:
        # Single SMS - no UDH
        pdu.append(udl)
        pdu.extend(user_data)
    
    # Convert to hex string
    pdu_hex = ''.join(f'{b:02X}' for b in pdu)
    
    # TPDU length (everything except SMSC)
    tpdu_len = len(pdu) - 1
    
    return pdu_hex, tpdu_len
