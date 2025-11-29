"""
License Manager Module
Handles hardware ID generation, license verification, and activation.
"""

import os
import sys
import hashlib
import platform
from datetime import datetime, date
from typing import Optional, Tuple, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Try to import Windows-specific libraries
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class LicenseManager:
    """Manages license verification and activation for the application."""
    
    def __init__(self):
        """Initialize the license manager with Supabase connection."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env file. "
                "Please provide your Supabase credentials."
            )
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.hwid = self._get_hwid()
    
    def _get_hwid(self) -> str:
        """
        Generate a unique Hardware ID for the current machine.
        Uses multiple hardware identifiers for better uniqueness.
        """
        hw_components = []
        
        # Get machine name
        try:
            hw_components.append(platform.node())
        except:
            pass
        
        # Get processor serial number (Windows)
        if platform.system() == 'Windows' and WMI_AVAILABLE:
            try:
                c = wmi.WMI()
                for processor in c.Win32_Processor():
                    hw_components.append(processor.ProcessorId)
                    break
            except:
                pass
        
        # Get disk serial number
        if platform.system() == 'Windows' and WMI_AVAILABLE:
            try:
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    hw_components.append(disk.SerialNumber)
                    break
            except:
                pass
        
        # Get MAC address (fallback method)
        if PSUTIL_AVAILABLE:
            try:
                import psutil
                net_if_addrs = psutil.net_if_addrs()
                for interface_name, addresses in net_if_addrs.items():
                    for addr in addresses:
                        if addr.family == psutil.AF_LINK and addr.address:
                            hw_components.append(addr.address)
                            break
                    if hw_components:
                        break
            except:
                pass
        
        # Fallback: Use platform-specific identifiers
        if not hw_components:
            hw_components.append(platform.machine())
            hw_components.append(platform.processor())
        
        # Combine all components and create a hash
        hw_string = '|'.join(str(comp) for comp in hw_components if comp)
        hwid = hashlib.sha256(hw_string.encode()).hexdigest()[:32]
        
        return hwid
    
    def _get_server_time(self) -> date:
        """
        Get the current date from the database server.
        This prevents time manipulation attacks.
        """
        try:
            # Try to call the get_server_date() function
            response = self.supabase.rpc('get_server_date').execute()
            if response.data is not None:
                # The function returns a date string
                if isinstance(response.data, str):
                    return datetime.fromisoformat(response.data).date()
                elif isinstance(response.data, dict) and 'date' in response.data:
                    return datetime.fromisoformat(response.data['date']).date()
                # Sometimes Supabase returns the value directly
                return response.data if isinstance(response.data, date) else date.today()
        except Exception as e:
            # Fallback: Try to get server time from a query
            try:
                # Query the database to get current timestamp
                response = self.supabase.table('licenses').select('created_at').limit(1).execute()
                if response.data and len(response.data) > 0:
                    # Extract date from timestamp
                    created_at = response.data[0].get('created_at')
                    if created_at:
                        # Parse the timestamp
                        if isinstance(created_at, str):
                            return datetime.fromisoformat(created_at.split('T')[0]).date()
            except:
                pass
        
        # Final fallback: Use local date (not ideal, but functional)
        # In production, you should ensure the RPC function works
        return date.today()
    
    def check_license(self) -> Tuple[bool, str]:
        """
        Check if the current machine has a valid, active license.
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Query for license by HWID
            response = self.supabase.table('licenses')\
                .select('*')\
                .eq('hwid', self.hwid)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return False, "No license found for this machine. Please activate your license."
            
            license_data = response.data[0]
            
            # Check if license is active
            if not license_data.get('is_active', False):
                return False, "Your license has been revoked. Please contact support."
            
            # Get server date to prevent time manipulation
            server_date = self._get_server_time()
            
            # Parse expiration date
            expiration_date_str = license_data.get('expiration_date')
            if expiration_date_str:
                if isinstance(expiration_date_str, str):
                    expiration_date = datetime.fromisoformat(expiration_date_str.split('T')[0]).date()
                else:
                    expiration_date = expiration_date_str
            else:
                return False, "Invalid license data. Please contact support."
            
            # Check if license has expired
            if expiration_date < server_date:
                days_expired = (server_date - expiration_date).days
                return False, f"Your license expired {days_expired} day(s) ago. Please renew your subscription."
            
            # License is valid
            days_remaining = (expiration_date - server_date).days
            client_name = license_data.get('client_name', 'User')
            
            return True, f"License valid for {client_name}. Expires in {days_remaining} day(s)."
        
        except Exception as e:
            return False, f"License verification failed: {str(e)}. Please check your internet connection."
    
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Activate a license key for this machine (first-time activation).
        
        Args:
            license_key: The license key (UUID) provided by the user
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validate license key format (UUID)
            try:
                import uuid
                uuid.UUID(license_key)  # Validate UUID format
            except ValueError:
                return False, "Invalid license key format. Please check your license key."
            
            # Check if license key exists and is available
            response = self.supabase.table('licenses')\
                .select('*')\
                .eq('license_key', license_key)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return False, "License key not found. Please verify your license key."
            
            license_data = response.data[0]
            
            # Check if license is already activated on another machine
            if license_data.get('hwid'):
                if license_data.get('hwid') != self.hwid:
                    return False, "This license key is already activated on another machine. Each license can only be used on one device."
                else:
                    return True, "License is already activated on this machine."
            
            # Check if license is active
            if not license_data.get('is_active', False):
                return False, "This license key has been revoked. Please contact support."
            
            # Check expiration (using server time)
            server_date = self._get_server_time()
            expiration_date_str = license_data.get('expiration_date')
            if expiration_date_str:
                if isinstance(expiration_date_str, str):
                    expiration_date = datetime.fromisoformat(expiration_date_str.split('T')[0]).date()
                else:
                    expiration_date = expiration_date_str
                
                if expiration_date < server_date:
                    return False, "This license key has already expired. Please contact support for renewal."
            
            # Activate license by linking HWID
            update_response = self.supabase.table('licenses')\
                .update({'hwid': self.hwid})\
                .eq('license_key', license_key)\
                .execute()
            
            if update_response.data:
                client_name = license_data.get('client_name', 'User')
                return True, f"License activated successfully for {client_name}!"
            else:
                return False, "Failed to activate license. Please try again or contact support."
        
        except Exception as e:
            return False, f"Activation failed: {str(e)}. Please check your internet connection."
    
    
    def get_license_info(self) -> Optional[Dict]:
        """
        Get current license information for this machine.
        
        Returns:
            Dict with license information or None if not found
        """
        try:
            response = self.supabase.table('licenses')\
                .select('*')\
                .eq('hwid', self.hwid)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except:
            return None


def check_license_on_startup() -> bool:
    """
    Convenience function to check license on application startup.
    Returns True if license is valid, False otherwise.
    """
    try:
        manager = LicenseManager()
        is_valid, message = manager.check_license()
        
        if not is_valid:
            print(f"\n{'='*60}")
            print("LICENSE VERIFICATION FAILED")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
            
            # If no license found, prompt for activation
            if "No license found" in message or "activate" in message.lower():
                license_key = input("Enter your license key to activate: ").strip()
                if license_key:
                    success, act_message = manager.activate_license(license_key)
                    print(act_message)
                    if success:
                        return True
            
            return False
        
        print(f"\n✓ {message}\n")
        return True
    
    except Exception as e:
        print(f"\nERROR: Failed to initialize license manager: {str(e)}\n")
        return False


if __name__ == "__main__":
    # Test the license manager
    print("Testing License Manager...")
    print(f"Hardware ID: {LicenseManager().hwid}")
    
    # Check license
    is_valid, message = LicenseManager().check_license()
    print(f"License Status: {is_valid}")
    print(f"Message: {message}")

