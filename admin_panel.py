"""
Streamlit Admin Dashboard for License Management
Run with: streamlit run admin_panel.py
"""

import os
import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid

# Load environment variables (for local development)
load_dotenv('config.env')

# Page configuration
st.set_page_config(
    page_title="License Management Dashboard",
    page_icon="🔐",
    layout="wide"
)

# Initialize Supabase connection
@st.cache_resource
def init_supabase():
    """Initialize Supabase client for read operations."""
    try:
        # Try Streamlit secrets first (for production), then environment variables
        supabase_url = None
        supabase_key = None
        
        try:
            # Try to access secrets (works in Streamlit Cloud)
            if hasattr(st, 'secrets') and st.secrets:
                supabase_url = st.secrets.get('SUPABASE_URL')
                supabase_key = st.secrets.get('SUPABASE_KEY')
        except (KeyError, AttributeError, TypeError):
            pass
        
        # Fallback to environment variables (for local development)
        if not supabase_url:
            supabase_url = os.getenv('SUPABASE_URL')
        if not supabase_key:
            supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            st.error("⚠️ SUPABASE_URL and SUPABASE_KEY must be set in Streamlit Secrets or .env file")
            st.info("Please add your Supabase credentials to Streamlit Secrets (Settings → Secrets)")
            st.stop()
            return None
        
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"❌ Error initializing Supabase: {str(e)}")
        st.info("Please check your Supabase credentials in Streamlit Secrets")
        st.stop()
        return None

@st.cache_resource
def init_service_client():
    """Initialize Supabase client using the service_role key for writes."""
    try:
        # Try Streamlit secrets first (for production), then environment variables
        supabase_url = None
        service_key = None
        
        try:
            # Try to access secrets (works in Streamlit Cloud)
            if hasattr(st, 'secrets') and st.secrets:
                supabase_url = st.secrets.get('SUPABASE_URL')
                service_key = st.secrets.get('SUPABASE_SERVICE_KEY')
        except (KeyError, AttributeError, TypeError):
            pass
        
        # Fallback to environment variables (for local development)
        if not supabase_url:
            supabase_url = os.getenv('SUPABASE_URL')
        if not service_key:
            service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not service_key:
            st.warning("⚠️ SUPABASE_SERVICE_KEY not found. License creation will fail. Please add it to Streamlit Secrets.")
            return None
        
        return create_client(supabase_url, service_key)
    except Exception as e:
        st.warning(f"⚠️ Error initializing service client: {str(e)}")
        return None

# Initialize clients
supabase = init_supabase()
service_client = init_service_client()

# Show connection status
if supabase is None:
    st.error("❌ Failed to connect to Supabase. Please check your configuration.")
    st.stop()

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-expired {
        color: #dc3545;
        font-weight: bold;
    }
    .status-inactive {
        color: #ffc107;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<h1 class="main-header">🔐 License Management Dashboard</h1>', unsafe_allow_html=True)

# Connection Status in Sidebar
st.sidebar.title("🔐 Navigation")
if supabase:
    st.sidebar.success("✅ Connected to Supabase")
else:
    st.sidebar.error("❌ Not Connected")

if service_client:
    st.sidebar.success("✅ Service Key Available")
else:
    st.sidebar.warning("⚠️ Service Key Missing")

st.sidebar.divider()

# Page Navigation
page = st.sidebar.radio(
    "Select Page",
    ["📊 Dashboard", "➕ Create License", "👥 View All Licenses", "✅ Manage License", "📈 Statistics"]
)

# Helper Functions
def get_all_licenses():
    """Fetch all licenses from the database."""
    try:
        if supabase is None:
            return []
        response = supabase.table('licenses').select('*').order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        error_msg = str(e)
        # Check if it's an API key error
        if '401' in error_msg or 'Invalid API key' in error_msg or 'Unauthorized' in error_msg or 'JSON could not be generated' in error_msg:
            # Only show error once using session state
            if 'api_key_error_shown' not in st.session_state:
                st.error("❌ Invalid API Key. Please check your SUPABASE_KEY in Streamlit Secrets.")
                st.info("📝 **How to fix:**\n1. Go to https://share.streamlit.io/\n2. Select your app\n3. Settings → Secrets\n4. Add SUPABASE_KEY from config.env")
                st.session_state['api_key_error_shown'] = True
        else:
            # Only show non-API-key errors
            st.error(f"❌ Error fetching licenses: {error_msg}")
        return []

def get_active_licenses():
    """Fetch only active licenses."""
    try:
        if supabase is None:
            return []
        response = supabase.table('licenses')\
            .select('*')\
            .eq('is_active', True)\
            .order('expiration_date', desc=False)\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        error_msg = str(e)
        # Check if it's an API key error - don't show duplicate error
        if '401' in error_msg or 'Invalid API key' in error_msg or 'Unauthorized' in error_msg or 'JSON could not be generated' in error_msg:
            # Error already shown by get_all_licenses, skip
            pass
        else:
            st.error(f"❌ Error fetching active licenses: {error_msg}")
        return []

def create_license(client_name: str, duration_months: int, notes: Optional[str] = None) -> tuple:
    """Create a new license."""
    try:
        # MUST use service_client for INSERT operations (bypasses RLS)
        if service_client is None:
            return False, None, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        # Calculate expiration date
        expiration_date = date.today() + timedelta(days=duration_months * 30)
        
        # Generate UUID license key
        license_key = str(uuid.uuid4())
        
        # Insert into database using service_client (bypasses RLS)
        response = service_client.table('licenses').insert({
            'license_key': license_key,
            'client_name': client_name,
            'expiration_date': expiration_date.isoformat(),
            'is_active': True,
            'notes': notes
        }).execute()
        
        if response.data:
            return True, license_key, None
        else:
            return False, None, "Failed to create license - no data returned"
    except Exception as e:
        error_msg = str(e)
        # Extract error details if available
        if isinstance(e, dict):
            error_msg = e.get('message', str(e))
        return False, None, error_msg

def activate_license(license_key: str) -> tuple:
    """Activate a license by setting is_active to True."""
    try:
        # Use service_client for UPDATE operations (bypasses RLS)
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        response = service_client.table('licenses')\
            .update({'is_active': True})\
            .eq('license_key', license_key)\
            .execute()
        
        if response.data:
            return True, f"License {license_key[:8]}... activated successfully!"
        else:
            return False, "License not found or already active"
    except Exception as e:
        return False, str(e)

def extend_license(license_key: str, additional_months: int) -> tuple:
    """Extend license expiration date by adding months."""
    try:
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        # Get current license
        response = service_client.table('licenses')\
            .select('expiration_date')\
            .eq('license_key', license_key)\
            .execute()
        
        if not response.data:
            return False, "License not found"
        
        current_expiration = response.data[0].get('expiration_date')
        if current_expiration:
            # Parse current expiration date
            if isinstance(current_expiration, str):
                current_date = datetime.fromisoformat(current_expiration.split('T')[0]).date()
            else:
                current_date = current_expiration
            
            # Add months to current expiration (or use today if expired)
            if current_date < date.today():
                new_expiration = date.today() + timedelta(days=additional_months * 30)
            else:
                new_expiration = current_date + timedelta(days=additional_months * 30)
            
            # Update expiration date
            update_response = service_client.table('licenses')\
                .update({'expiration_date': new_expiration.isoformat()})\
                .eq('license_key', license_key)\
                .execute()
            
            if update_response.data:
                return True, f"License extended successfully! New expiration: {new_expiration}"
            else:
                return False, "Failed to update license"
        else:
            return False, "Invalid license data"
    except Exception as e:
        return False, str(e)

def revoke_license(license_key: str) -> tuple:
    """Revoke a license by setting is_active to False."""
    try:
        # Use service_client for UPDATE operations (bypasses RLS)
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        response = service_client.table('licenses')\
            .update({'is_active': False})\
            .eq('license_key', license_key)\
            .execute()
        
        if response.data:
            return True, "License revoked successfully"
        else:
            return False, "License not found or already revoked"
    except Exception as e:
        return False, str(e)

def delete_license(license_key: str) -> tuple:
    """Permanently delete a license from the database."""
    try:
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        response = service_client.table('licenses')\
            .delete()\
            .eq('license_key', license_key)\
            .execute()
        
        if response.data:
            return True, "License deleted successfully"
        else:
            return False, "License not found"
    except Exception as e:
        return False, str(e)

def unlink_device(license_key: str) -> tuple:
    """Unlink device (HWID) from a license, allowing it to be activated on another device."""
    try:
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        response = service_client.table('licenses')\
            .update({'hwid': None})\
            .eq('license_key', license_key)\
            .execute()
        
        if response.data:
            return True, "Device unlinked successfully. License can now be activated on another device."
        else:
            return False, "License not found"
    except Exception as e:
        return False, str(e)

def reset_license(license_key: str) -> tuple:
    """Reset license: activate it, unlink device, and extend if expired."""
    try:
        if service_client is None:
            return False, "Service role key is missing. Please add SUPABASE_SERVICE_KEY to Streamlit Secrets."
        
        # Get current license
        response = service_client.table('licenses')\
            .select('*')\
            .eq('license_key', license_key)\
            .execute()
        
        if not response.data:
            return False, "License not found"
        
        license_data = response.data[0]
        updates = {
            'is_active': True,
            'hwid': None
        }
        
        # Check if expired and extend by 1 month if so
        exp_date_str = license_data.get('expiration_date')
        if exp_date_str:
            if isinstance(exp_date_str, str):
                exp_date = datetime.fromisoformat(exp_date_str.split('T')[0]).date()
            else:
                exp_date = exp_date_str
            
            if exp_date < date.today():
                # Extend by 1 month from today
                updates['expiration_date'] = (date.today() + timedelta(days=30)).isoformat()
        
        # Apply updates
        update_response = service_client.table('licenses')\
            .update(updates)\
            .eq('license_key', license_key)\
            .execute()
        
        if update_response.data:
            return True, "License reset successfully: activated, device unlinked, and extended if expired."
        else:
            return False, "Failed to reset license"
    except Exception as e:
        return False, str(e)

def get_statistics():
    """Get license statistics."""
    all_licenses = get_all_licenses()
    active_licenses = get_active_licenses()
    
    today = date.today()
    expired_count = 0
    expiring_soon = 0  # Expiring in next 30 days
    
    for license in all_licenses:
        if license.get('is_active'):
            exp_date_str = license.get('expiration_date')
            if exp_date_str:
                if isinstance(exp_date_str, str):
                    exp_date = datetime.fromisoformat(exp_date_str.split('T')[0]).date()
                else:
                    exp_date = exp_date_str
                
                if exp_date < today:
                    expired_count += 1
                elif (exp_date - today).days <= 30:
                    expiring_soon += 1
    
    return {
        'total': len(all_licenses),
        'active': len(active_licenses),
        'expired': expired_count,
        'expiring_soon': expiring_soon,
        'revoked': len(all_licenses) - len(active_licenses) - expired_count
    }

# Dashboard Page
if page == "📊 Dashboard":
    st.header("📊 License Overview")
    
    stats = get_statistics()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Licenses", stats['total'])
    with col2:
        st.metric("Active Licenses", stats['active'], delta=stats['active'] - stats['expired'])
    with col3:
        st.metric("Expired", stats['expired'], delta=-stats['expired'])
    with col4:
        st.metric("Expiring Soon", stats['expiring_soon'], delta=stats['expiring_soon'])
    
    st.divider()
    
    # Recent licenses
    st.subheader("Recent Licenses")
    
    # Reset error flag when page changes
    if 'api_key_error_shown' in st.session_state:
        del st.session_state['api_key_error_shown']
    
    all_licenses = get_all_licenses()[:10]  # Show last 10
    
    if all_licenses:
        for license in all_licenses:
            with st.expander(f"📋 {license.get('client_name', 'Unknown')} - {license.get('license_key', 'N/A')[:8]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**License Key:** `{license.get('license_key')}`")
                    st.write(f"**Client:** {license.get('client_name')}")
                    st.write(f"**HWID:** {license.get('hwid') or 'Not activated'}")
                with col2:
                    exp_date = license.get('expiration_date')
                    if exp_date:
                        if isinstance(exp_date, str):
                            exp_date = datetime.fromisoformat(exp_date.split('T')[0]).date()
                        days_left = (exp_date - date.today()).days
                        status = "🟢 Active" if license.get('is_active') and days_left > 0 else "🔴 Inactive"
                        st.write(f"**Status:** {status}")
                        st.write(f"**Expires:** {exp_date} ({days_left} days)")
                    if license.get('notes'):
                        st.write(f"**Notes:** {license.get('notes')}")
    else:
        st.info("No licenses found. Create your first license using the sidebar.")

# Create License Page
elif page == "➕ Create License":
    st.header("➕ Create New License")
    
    with st.form("create_license_form"):
        client_name = st.text_input("Client Name *", placeholder="Enter client/company name")
        
        col1, col2 = st.columns(2)
        with col1:
            duration_months = st.number_input("Duration (Months) *", min_value=1, max_value=120, value=1)
        with col2:
            duration_days = duration_months * 30
            st.write(f"**Total Days:** {duration_days}")
        
        notes = st.text_area("Notes (Optional)", placeholder="Additional notes about this license")
        
        submitted = st.form_submit_button("🔑 Generate License Key", type="primary")
        
        if submitted:
            if not client_name:
                st.error("⚠️ Client name is required!")
            else:
                with st.spinner("Creating license..."):
                    success, license_key, error = create_license(client_name, duration_months, notes)
                    
                    if success:
                        st.success("✅ License created successfully!")
                        st.info(f"**License Key:** `{license_key}`")
                        st.warning("⚠️ **Important:** Share this license key with your client. They will need it to activate the software.")
                        
                        # Copy to clipboard button (if supported)
                        st.code(license_key, language=None)
                    else:
                        st.error(f"❌ Failed to create license: {error}")

# View All Licenses Page
elif page == "👥 View All Licenses":
    st.header("👥 All Licenses")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.selectbox("Filter by Status", ["All", "Active", "Expired", "Revoked"])
    with col2:
        search_term = st.text_input("🔍 Search (Client Name or License Key)", "")
    
    # Fetch licenses
    all_licenses = get_all_licenses()
    
    # Apply filters
    filtered_licenses = all_licenses
    if filter_status != "All":
        today = date.today()
        if filter_status == "Active":
            filtered_licenses = [l for l in all_licenses if l.get('is_active')]
            filtered_licenses = [l for l in filtered_licenses if 
                               datetime.fromisoformat(l.get('expiration_date', '').split('T')[0]).date() >= today]
        elif filter_status == "Expired":
            filtered_licenses = [l for l in all_licenses 
                               if datetime.fromisoformat(l.get('expiration_date', '').split('T')[0]).date() < today]
        elif filter_status == "Revoked":
            filtered_licenses = [l for l in all_licenses if not l.get('is_active')]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_licenses = [l for l in filtered_licenses 
                           if search_lower in l.get('client_name', '').lower() 
                           or search_lower in l.get('license_key', '').lower()]
    
    # Display licenses in a table
    if filtered_licenses:
        st.write(f"**Found {len(filtered_licenses)} license(s)**")
        
        # Display licenses in table format
        for license in filtered_licenses:
            exp_date_str = license.get('expiration_date', '')
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.split('T')[0]).date()
                days_left = (exp_date - date.today()).days
                status = "🟢 Active" if license.get('is_active') and days_left > 0 else "🔴 Expired" if days_left < 0 else "⚪ Revoked"
            else:
                status = "❓ Unknown"
                days_left = 0
            
            with st.expander(f"{license.get('client_name', 'N/A')} - {status}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**License Key:** `{license.get('license_key', 'N/A')}`")
                    st.write(f"**Client:** {license.get('client_name', 'N/A')}")
                    st.write(f"**HWID:** {license.get('hwid') or 'Not activated'}")
                with col2:
                    st.write(f"**Status:** {status}")
                    st.write(f"**Expiration:** {license.get('expiration_date', 'N/A')}")
                    st.write(f"**Days Left:** {days_left}")
                    st.write(f"**Created:** {license.get('created_at', 'N/A')[:10] if license.get('created_at') else 'N/A'}")
    else:
        st.info("No licenses found matching your criteria.")

# Manage License Page
elif page == "✅ Manage License":
    st.header("✅ Manage License")
    
    # Get all licenses
    all_licenses = get_all_licenses()
    
    if all_licenses:
        license_options = {
            f"{l.get('client_name')} - {l.get('license_key')[:36]}... ({'🟢 Active' if l.get('is_active') else '🔴 Inactive'})": l.get('license_key')
            for l in all_licenses
        }
        
        selected_license_display = st.selectbox("Select License", list(license_options.keys()))
        selected_license_key = license_options[selected_license_display]
        
        # Show license details
        selected_license = next(l for l in all_licenses if l.get('license_key') == selected_license_key)
        
        # License Details Card
        st.subheader("📋 License Details")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **Client:** {selected_license.get('client_name')}  
            **License Key:** `{selected_license.get('license_key')}`  
            **HWID:** {selected_license.get('hwid') or '❌ Not activated'}
            **Created:** {selected_license.get('created_at', 'N/A')[:10] if selected_license.get('created_at') else 'N/A'}
            """)
        
        with col2:
            exp_date_str = selected_license.get('expiration_date')
            if exp_date_str:
                if isinstance(exp_date_str, str):
                    exp_date = datetime.fromisoformat(exp_date_str.split('T')[0]).date()
                else:
                    exp_date = exp_date_str
                days_left = (exp_date - date.today()).days
            else:
                exp_date = None
                days_left = 0
            
            status_icon = "🟢" if selected_license.get('is_active') and days_left > 0 else "🔴"
            status_text = "Active" if selected_license.get('is_active') and days_left > 0 else "Inactive"
            
            st.info(f"""
            **Status:** {status_icon} {status_text}  
            **Expiration:** {exp_date or 'N/A'}  
            **Days Left:** {days_left} days
            **Notes:** {selected_license.get('notes') or 'None'}
            """)
        
        st.divider()
        
        # Action Buttons Section
        st.subheader("⚙️ License Actions")
        
        # Show current status
        is_active = selected_license.get('is_active', False)
        if is_active:
            st.success("✅ License is currently ACTIVE")
        else:
            st.warning("⚠️ License is currently INACTIVE")
        
        # Row 1: Activate/Revoke - Always show buttons
        col_act, col_rev = st.columns(2)
        
        with col_act:
            if st.button("✅ Activate License", type="primary", use_container_width=True, 
                        disabled=is_active, help="Activate this license"):
                with st.spinner("Activating license..."):
                    success, message = activate_license(selected_license_key)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        with col_rev:
            if st.button("🚫 Revoke License", type="secondary", use_container_width=True,
                        disabled=not is_active, help="Revoke (deactivate) this license"):
                with st.spinner("Revoking license..."):
                    success, message = revoke_license(selected_license_key)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        st.divider()
        
        # Row 2: Extend License
        st.subheader("📅 Extend License Duration")
        col_ext1, col_ext2, col_ext3 = st.columns([2, 1, 1])
        
        with col_ext1:
            extend_months = st.number_input("Add Months", min_value=1, max_value=120, value=1, step=1, key="extend_months")
            st.caption(f"Will add {extend_months * 30} days to the license")
        
        with col_ext2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("📅 Extend License", type="primary", use_container_width=True):
                with st.spinner(f"Extending license by {extend_months} month(s)..."):
                    success, message = extend_license(selected_license_key, extend_months)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        with col_ext3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🔄 Reset License", type="secondary", use_container_width=True, help="Activate, unlink device, and extend if expired"):
                with st.spinner("Resetting license..."):
                    success, message = reset_license(selected_license_key)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        st.divider()
        
        # Row 3: Device Management
        st.subheader("🔗 Device Management")
        
        # Show device info
        current_hwid = selected_license.get('hwid')
        if current_hwid:
            st.info(f"**Current Device:** `{current_hwid}`")
        else:
            st.info("**Current Device:** ❌ Not linked to any device")
        
        # Unlink button - always visible
        col_dev1, col_dev2 = st.columns([1, 1])
        with col_dev1:
            if st.button("🔓 Unlink Device", type="secondary", use_container_width=True, 
                       disabled=not current_hwid,
                       help="Unlink current device. License can be activated on another device."):
                with st.spinner("Unlinking device..."):
                    success, message = unlink_device(selected_license_key)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        with col_dev2:
            st.write("")  # Spacing
        
        st.divider()
        
        # Row 4: Dangerous Actions
        st.subheader("⚠️ Dangerous Actions")
        st.warning("⚠️ **Warning:** These actions cannot be undone!")
        
        col_del1, col_del2 = st.columns([3, 1])
        
        with col_del1:
            st.error("**Delete License:** This will permanently delete the license from the database.")
        
        with col_del2:
            if st.button("🗑️ Delete License", type="primary", use_container_width=True):
                # Confirmation
                st.error("⚠️ **Are you sure?** This action cannot be undone!")
                col_confirm1, col_confirm2 = st.columns(2)
                with col_confirm1:
                    if st.button("✅ Yes, Delete Permanently", type="primary", use_container_width=True):
                        with st.spinner("Deleting license..."):
                            success, message = delete_license(selected_license_key)
                            if success:
                                st.success(f"✅ {message}")
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                with col_confirm2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.rerun()
    else:
        st.info("No licenses found in database.")

# Statistics Page
elif page == "📈 Statistics":
    st.header("📈 License Statistics")
    
    stats = get_statistics()
    
    # Visual statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("License Distribution")
        # Simple chart data without pandas
        chart_data = {
            'Active': stats['active'],
            'Expired': stats['expired'], 
            'Revoked': stats['revoked']
        }
        st.bar_chart(chart_data)
    
    with col2:
        st.subheader("Quick Stats")
        st.metric("Total Licenses", stats['total'])
        st.metric("Active", stats['active'])
        st.metric("Expired", stats['expired'])
        st.metric("Expiring Soon (30 days)", stats['expiring_soon'])
        st.metric("Revoked", stats['revoked'])
    
    # Expiring soon list
    if stats['expiring_soon'] > 0:
        st.divider()
        st.subheader("⚠️ Licenses Expiring Soon (Next 30 Days)")
        all_licenses = get_all_licenses()
        today = date.today()
        expiring_licenses = []
        
        for license in all_licenses:
            if license.get('is_active'):
                exp_date_str = license.get('expiration_date')
                if exp_date_str:
                    exp_date = datetime.fromisoformat(exp_date_str.split('T')[0]).date()
                    days_left = (exp_date - today).days
                    if 0 < days_left <= 30:
                        expiring_licenses.append({
                            'Client': license.get('client_name'),
                            'Days Left': days_left,
                            'Expiration Date': exp_date
                        })
        
        if expiring_licenses:
            for exp_license in expiring_licenses:
                st.warning(f"**{exp_license['Client']}** - Expires in **{exp_license['Days Left']} days** ({exp_license['Expiration Date']})")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        License Management System | Built with Streamlit & Supabase
    </div>
""", unsafe_allow_html=True)

