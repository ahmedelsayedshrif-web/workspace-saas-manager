# Complete Setup Guide

## Phase 1: Supabase Database Setup ✅

### Step 1: Run SQL Scripts in Supabase

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Run the following SQL scripts **in order**:

   **First, run `supabase_setup.sql`:**
   - This creates the `licenses` table with all required columns
   - Creates indexes for performance
   - Sets up automatic timestamp updates

   **Then, run `supabase_functions.sql`:**
   - Creates the `get_server_date()` function for time verification
   - Sets up Row Level Security (RLS) policies
   - Configures proper access permissions

### Step 2: Get Your API Credentials

1. In Supabase, go to **Project Settings** → **API**
2. Copy the following values:
   - **Project URL** → This is your `SUPABASE_URL`
   - **anon/public key** → This is your `SUPABASE_KEY` (for client-side)
   - **service_role key** → This is your `SUPABASE_SERVICE_KEY` (for admin panel - keep secret!)

### Step 3: Create `.env` File

Create a file named `.env` in the project root with:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

**⚠️ IMPORTANT:** Never commit the `.env` file to Git! It's already in `.gitignore`.

---

## Phase 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `supabase` - Supabase Python client
- `python-dotenv` - Environment variable management
- `wmi` - Windows Hardware ID generation (Windows only)
- `psutil` - Cross-platform system utilities
- `streamlit` - Admin dashboard framework
- `python-dateutil` - Date handling utilities

---

## Phase 3: Test the System

### Test License Manager

```python
python license_manager.py
```

This will:
- Generate and display your Hardware ID
- Check for an existing license
- Show license status

### Test Admin Panel

```bash
streamlit run admin_panel.py
```

This opens the admin dashboard in your browser where you can:
- Create new licenses
- View all licenses
- Revoke licenses
- View statistics

---

## Phase 4: Integrate into Your Application

### Simple Integration

Add this to the start of your main application:

```python
from license_manager import check_license_on_startup

if __name__ == "__main__":
    # Check license before starting
    if not check_license_on_startup():
        print("Application cannot start without a valid license.")
        input("Press Enter to exit...")
        exit(1)
    
    # Your application code here
    print("Application started successfully!")
```

### Advanced Integration

```python
from license_manager import LicenseManager

def main():
    manager = LicenseManager()
    
    # Check license
    is_valid, message = manager.check_license()
    
    if not is_valid:
        print(f"License Error: {message}")
        
        # If no license found, try activation
        if "No license found" in message or "activate" in message.lower():
            license_key = input("\nEnter your license key: ").strip()
            if license_key:
                success, act_msg = manager.activate_license(license_key)
                print(act_msg)
                if success:
                    # Re-check license
                    is_valid, message = manager.check_license()
        
        if not is_valid:
            print("\nApplication cannot start without a valid license.")
            input("Press Enter to exit...")
            return
    
    print(f"✓ {message}")
    # Continue with your application
    run_your_application()

if __name__ == "__main__":
    main()
```

---

## Phase 5: Push to GitHub

Since GitHub CLI is not available, use these commands:

### Option 1: Create Repository on GitHub Website

1. Go to [github.com](https://github.com) and create a new repository
2. **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Copy the repository URL (e.g., `https://github.com/yourusername/license-system.git`)

### Option 2: Push Using Git Commands

```bash
# Add the remote repository (replace with your actual URL)
git remote add origin https://github.com/yourusername/license-system.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

### Option 3: Using SSH (if configured)

```bash
git remote add origin git@github.com:yourusername/license-system.git
git branch -M main
git push -u origin main
```

---

## Usage Workflow

### For You (Admin):

1. **Create License**:
   - Run `streamlit run admin_panel.py`
   - Go to "Create License" page
   - Enter client name and duration
   - Copy the generated license key
   - Share the license key with your client

2. **Monitor Licenses**:
   - Use the dashboard to view all licenses
   - Check expiration dates
   - See which licenses are activated

3. **Revoke License** (if needed):
   - Go to "Revoke License" page
   - Select the license
   - Click "Revoke License"
   - The client will be immediately locked out

### For Your Clients:

1. **First Time**:
   - Install your application
   - Run the application
   - Enter the license key when prompted
   - License is activated and locked to their device

2. **Subsequent Uses**:
   - Application automatically verifies license on startup
   - No user interaction needed (if license is valid)

---

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set"
- Make sure `.env` file exists in project root
- Verify the file contains correct values
- Check for typos in variable names

### "License verification failed: Connection error"
- Check internet connection
- Verify Supabase project is active
- Check if RLS policies are correctly configured

### "No license found for this machine"
- Client needs to activate license with valid key
- Check if license key exists in database (admin panel)

### Admin panel shows errors
- Make sure `SUPABASE_SERVICE_KEY` is set in `.env`
- Verify RLS policies allow service_role access
- Check Supabase project status

### HWID generation fails
- On Windows: `wmi` package should be installed
- On other platforms: Uses `psutil` as fallback
- Check if both packages are installed: `pip install wmi psutil`

---

## Security Best Practices

1. ✅ **Never commit `.env` file** - Already in `.gitignore`
2. ✅ **Use service_role key only in admin panel** - Never in client apps
3. ✅ **Keep service_role key secret** - Treat it like a password
4. ✅ **Use HTTPS** - Supabase uses HTTPS by default
5. ✅ **Enable RLS** - Row Level Security is configured in SQL scripts
6. ✅ **Server time verification** - Prevents time manipulation attacks
7. ✅ **HWID locking** - Each license locked to one device

---

## Next Steps

- [ ] Run SQL scripts in Supabase
- [ ] Create `.env` file with your credentials
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Test license manager: `python license_manager.py`
- [ ] Test admin panel: `streamlit run admin_panel.py`
- [ ] Create your first license in admin panel
- [ ] Integrate `license_manager.py` into your application
- [ ] Push code to GitHub (optional)

---

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Verify all SQL scripts ran successfully
3. Check Supabase project logs
4. Review the README.md for additional information

