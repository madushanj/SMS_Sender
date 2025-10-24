"""
Improved Modem Communication Module using python-gsmmodem-new library

This replaces the manual PDU handling with a proper GSM modem library
that handles all the protocol details correctly.
"""

import logging
from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException, CmsError, CommandError

logger = logging.getLogger('SMSDaemon')


class ModemSMS:
    """Wrapper for GSM modem SMS operations"""
    
    def __init__(self, port, baudrate, timeout=30):
        """
        Initialize modem connection
        
        Args:
            port: Serial port (e.g., 'COM6' or '/dev/ttyUSB0')
            baudrate: Baud rate (e.g., 9600, 115200)
            timeout: Response timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.modem = None
        
    def connect(self):
        """Connect to the modem"""
        try:
            self.modem = GsmModem(self.port, self.baudrate)
            logger.info(f"Connecting to modem on {self.port} at {self.baudrate} baud...")
            self.modem.connect()
            
            # Log modem info
            manufacturer = self.modem.manufacturer
            model = self.modem.model
            revision = self.modem.revision
            
            logger.info(f"Modem connected: {manufacturer} {model} (Firmware: {revision})")
            
            # Check signal strength
            try:
                signal = self.modem.signalStrength
                logger.info(f"Signal strength: {signal}%")
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to modem: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the modem"""
        if self.modem:
            try:
                self.modem.close()
                logger.info("Modem disconnected")
            except:
                pass
    
    def send_sms(self, number, text):
        """
        Send SMS using the modem library
        
        Args:
            number: Destination phone number
            text: Message text
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.modem:
            return False, "Modem not connected"
        
        try:
            logger.debug(f"Sending SMS to {number}: {text[:50]}...")
            
            # Send SMS (library handles multipart automatically)
            sms = self.modem.sendSms(number, text, waitForDeliveryReport=False)
            
            logger.debug(f"SMS sent successfully, reference: {sms.reference if hasattr(sms, 'reference') else 'N/A'}")
            return True, "SMS sent successfully"
            
        except TimeoutException as e:
            error_msg = f"Timeout sending SMS: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg
            
        except CmsError as e:
            error_msg = f"CMS Error {e.code}: {e.message}"
            logger.error(error_msg)
            return False, error_msg
            
        except CommandError as e:
            error_msg = f"Command Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg
    
    def check_network(self):
        """Check network registration status"""
        if not self.modem:
            return False, "Modem not connected"
            
        try:
            if self.modem.networkName:
                return True, f"Registered on {self.modem.networkName}"
            else:
                return False, "Not registered on network"
        except:
            return False, "Unable to check network status"


# Backward compatibility wrapper for existing code
def send_sms(modem_wrapper, number, text, modem_timeout=30):
    """
    Compatibility wrapper for send_sms function
    
    Args:
        modem_wrapper: ModemSMS instance
        number: Phone number
        text: Message text
        modem_timeout: Timeout (ignored, uses modem_wrapper timeout)
        
    Returns:
        str: Status message
    """
    success, message = modem_wrapper.send_sms(number, text)
    
    if success:
        return "+CMGS: OK"  # Simulate success response
    else:
        return f"ERROR: {message}"
