"""
Encoding and Message Analysis Module

Handles character encoding detection, message size calculation,
and message splitting for SMS.
"""


def is_gsm7_compatible(text):
    """Check if text contains only GSM 7-bit characters."""
    # GSM 7-bit basic character set
    gsm7_basic = (
        "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
        "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
    )
    # GSM 7-bit extended characters (count as 2 characters each)
    gsm7_extended = "^{}\\[~]|€"
    
    for char in text:
        if char not in gsm7_basic and char not in gsm7_extended:
            return False
    return True


def calculate_sms_parts(text):
    """
    Calculate how many SMS parts are needed and the character limit per part.
    
    Args:
        text: The message text to analyze
    
    Returns:
        tuple: (num_parts, chars_per_part, encoding)
            - num_parts: Number of SMS parts needed
            - chars_per_part: Character limit per part
            - encoding: 'GSM7' or 'UCS2'
    """
    # Check encoding needed
    if is_gsm7_compatible(text):
        encoding = 'GSM7'
        # Calculate length considering extended characters count as 2
        gsm7_extended = "^{}\\[~]|€"
        char_count = sum(2 if c in gsm7_extended else 1 for c in text)
        
        # Single SMS: 160 chars, Multipart SMS: 153 chars per part
        if char_count <= 160:
            return 1, 160, encoding
        else:
            num_parts = (char_count + 152) // 153  # Ceiling division
            return num_parts, 153, encoding
    else:
        encoding = 'UCS2'
        char_count = len(text)
        
        # Single SMS: 70 chars, Multipart SMS: 67 chars per part
        if char_count <= 70:
            return 1, 70, encoding
        else:
            num_parts = (char_count + 66) // 67  # Ceiling division
            return num_parts, 67, encoding


def split_message(text, chars_per_part):
    """
    Split message into parts of specified character length.
    
    Args:
        text: The message text to split
        chars_per_part: Maximum characters per part
    
    Returns:
        list: List of message parts
    """
    parts = []
    gsm7_extended = "^{}\\[~]|€"
    
    if is_gsm7_compatible(text):
        # GSM7: need to account for extended chars counting as 2
        current_part = ""
        current_length = 0
        
        for char in text:
            char_length = 2 if char in gsm7_extended else 1
            
            if current_length + char_length <= chars_per_part:
                current_part += char
                current_length += char_length
            else:
                parts.append(current_part)
                current_part = char
                current_length = char_length
        
        if current_part:
            parts.append(current_part)
    else:
        # UCS2: simple character-based split
        for i in range(0, len(text), chars_per_part):
            parts.append(text[i:i + chars_per_part])
    
    return parts
