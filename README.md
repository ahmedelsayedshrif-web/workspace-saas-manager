# License Management System

A complete subscription-based license verification system for desktop applications using Supabase and Streamlit.

## Features

- ✅ Hardware ID (HWID) based device locking
- ✅ Server-side time verification (prevents time manipulation)
- ✅ License activation and verification
- ✅ Admin dashboard for license management
- ✅ Automatic expiration checking
- ✅ License revocation capability

## Setup Instructions

### Phase 1: Supabase Database Setup

1. **Create a Supabase account** at [supabase.com](https://supabase.com)

2. **Create a new project** in Supabase

3. **Run the SQL scripts** in the Supabase SQL Editor:
   - First, run `supabase_setup.sql` to create the licenses table
   - Then, run `supabase_functions.sql` to create helper functions and security policies

4. **Get your API credentials**:
   - Go to Project Settings > API
   - Copy your `Project URL` (SUPABASE_URL)
   - Copy your `anon/public` key (SUPABASE_KEY)
   - (Optional) Copy your `service_role` key for admin panel (SUPABASE_SERVICE_KEY)

### Phase 2: Local Configuration

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file** in the project root:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_supabase_anon_key_here
   SUPABASE_SERVICE_KEY=your_service_role_key_here  # Optional, for admin panel
   ```

### Phase 3: Using the License Manager

#### In Your Application

```python
from license_manager import check_license_on_startup, LicenseManager

# Simple usage - check on startup
if not check_license_on_startup():
    exit(1)  # Exit if license is invalid

# Advanced usage
manager = LicenseManager()
is_valid, message = manager.check_license()

if is_valid:
    # Continue with your application
    print("License verified!")
else:
    # Handle invalid license
    print(f"License error: {message}")
    
    # If no license found, activate one
    license_key = input("Enter license key: ")
    success, msg = manager.activate_license(license_key)
    print(msg)
```

### Phase 4: Admin Dashboard

Run the Streamlit admin panel:

```bash
streamlit run admin_panel.py
```

The dashboard allows you to:
- Create new license keys
- View all licenses
- Revoke licenses
- View statistics
- Search and filter licenses

## File Structure

```
.
├── license_manager.py      # Client-side license verification module
├── admin_panel.py          # Streamlit admin dashboard
├── supabase_setup.sql      # Database table creation
├── supabase_functions.sql  # Helper functions and security policies
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
└── README.md              # This file
```

## Security Notes

1. **Never commit `.env` file** - It contains sensitive API keys
2. **Use service_role key only in admin panel** - Never expose it in client applications
3. **HWID locking** - Each license can only be activated on one device
4. **Server time verification** - Prevents users from manipulating system time
5. **Row Level Security (RLS)** - Configured in Supabase for additional security

## License Flow

1. **First Time User**:
   - Application starts → No HWID found in database
   - User enters license key
   - HWID is linked to license key (device locked)

2. **Subsequent Starts**:
   - Application starts → HWID found in database
   - License status checked (active + not expired)
   - Server time verified (prevents time manipulation)
   - Access granted or denied

3. **Admin Actions**:
   - Create license → Generate UUID key
   - Revoke license → Set `is_active = False`
   - View statistics → Monitor all licenses

## Troubleshooting

### "License verification failed: Connection error"
- Check your internet connection
- Verify SUPABASE_URL and SUPABASE_KEY in `.env`
- Check Supabase project is active

### "No license found for this machine"
- User needs to activate license with a valid license key
- Check if license key exists in database (via admin panel)

### "This license key is already activated on another machine"
- Each license can only be used on one device
- To transfer license, revoke it first, then activate on new device

### Admin panel shows "Error fetching licenses"
- Verify SUPABASE_SERVICE_KEY is set in `.env`
- Check RLS policies in Supabase are correctly configured

## License

This license management system is provided as-is for your application.

