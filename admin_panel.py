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
    # Try Streamlit secrets first (for production), then environment variables
    supabase_url = st.secrets.get('SUPABASE_URL') or os.getenv('SUPABASE_URL')
    supabase_key = st.secrets.get('SUPABASE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        st.error("⚠️ SUPABASE_URL and SUPABASE_KEY must be set in Streamlit Secrets or .env file")
        st.stop()
    
    return create_client(supabase_url, supabase_key)

@st.cache_resource
def init_service_client():
    """Initialize Supabase client using the service_role key for writes."""
    # Try Streamlit secrets first (for production), then environment variables
    supabase_url = st.secrets.get('SUPABASE_URL') or os.getenv('SUPABASE_URL')
    service_key = st.secrets.get('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not service_key:
        st.warning("⚠️ SUPABASE_SERVICE_KEY not found. License creation will fail. Please add it to Streamlit Secrets.")
        return None
    
    return create_client(supabase_url, service_key)

supabase = init_supabase()
service_client = init_service_client()

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

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["📊 Dashboard", "➕ Create License", "👥 View All Licenses", "🚫 Revoke License", "📈 Statistics"]
)

# Helper Functions
def get_all_licenses():
    """Fetch all licenses from the database."""
    try:
        response = supabase.table('licenses').select('*').order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching licenses: {str(e)}")
        return []

def get_active_licenses():
    """Fetch only active licenses."""
    try:
        response = supabase.table('licenses')\
            .select('*')\
            .eq('is_active', True)\
            .order('expiration_date', desc=False)\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching active licenses: {str(e)}")
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

def revoke_license(license_key: str) -> tuple:
    """Revoke a license by setting is_active to False."""
    try:
        # Use service_client for UPDATE operations (bypasses RLS)
        target_client = service_client if service_client else supabase
        response = target_client.table('licenses')\
            .update({'is_active': False})\
            .eq('license_key', license_key)\
            .execute()
        
        if response.data:
            return True, "License revoked successfully"
        else:
            return False, "License not found or already revoked"
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

# Revoke License Page
elif page == "🚫 Revoke License":
    st.header("🚫 Revoke License")
    st.warning("⚠️ Revoking a license will immediately deactivate it. This action can be reversed by reactivating the license.")
    
    # Get all active licenses for selection
    active_licenses = get_active_licenses()
    
    if active_licenses:
        license_options = {
            f"{l.get('client_name')} - {l.get('license_key')[:36]}...": l.get('license_key')
            for l in active_licenses
        }
        
        selected_license_display = st.selectbox("Select License to Revoke", list(license_options.keys()))
        selected_license_key = license_options[selected_license_display]
        
        # Show license details
        selected_license = next(l for l in active_licenses if l.get('license_key') == selected_license_key)
        
        st.info(f"""
        **Client:** {selected_license.get('client_name')}  
        **License Key:** `{selected_license.get('license_key')}`  
        **HWID:** {selected_license.get('hwid') or 'Not activated'}  
        **Expiration:** {selected_license.get('expiration_date')}
        """)
        
        if st.button("🚫 Revoke License", type="primary"):
            with st.spinner("Revoking license..."):
                success, message = revoke_license(selected_license_key)
                if success:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    else:
        st.info("No active licenses to revoke.")

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

