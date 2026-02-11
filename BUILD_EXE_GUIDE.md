# Building Standalone Executable (.exe) Guide

This guide will help you create a standalone Windows executable (.exe) file that bundles the entire Vulnerable E-Commerce Lab application. Users can run it without installing Python or any dependencies!

## 🎯 What This Creates

A **single .exe file** that:

- ✅ Runs on any Windows PC (no Python installation needed)
- ✅ Includes all templates, static files, and data
- ✅ Auto-opens browser when started
- ✅ Self-contained (no external dependencies)
- ✅ Easy to distribute to students
- ✅ Portable (can run from USB drive)

## 📋 Prerequisites

1. **Python 3.8+** installed on your development machine
2. **PyInstaller** package
3. All project files in the `vulnerable_ecommerce` directory

## 🚀 Quick Build Instructions

### Step 1: Install PyInstaller

```powershell
# Make sure you're in the project directory
cd "E:\AS LAb\vulnerable_ecommerce"

# Activate virtual environment (if using one)
venv\Scripts\activate

# Install PyInstaller
pip install pyinstaller
```

### Step 2: Build the Executable

```powershell
# Build using the spec file (recommended)
pyinstaller VulnerableEcommerceLab.spec

# OR build with command line options
pyinstaller --onefile --name "VulnerableEcommerceLab" --add-data "templates;templates" --add-data "static;static" --add-data "data;data" --add-data "app.py;." --hidden-import flask --hidden-import werkzeug --console create_exe.py
```

### Step 3: Find Your Executable

After building (takes 2-5 minutes), you'll find:

- **Executable**: `dist\VulnerableEcommerceLab.exe`
- **Size**: ~50-80 MB (includes Python runtime and all dependencies)

### Step 4: Test the Executable

```powershell
# Navigate to the dist folder
cd dist

# Run the executable
.\VulnerableEcommerceLab.exe
```

The application should:

1. Open a console window
2. Start the Flask server
3. Automatically open your browser to http://127.0.0.1:5000

## 📦 Distribution

### What to Distribute

**Option 1: Just the .exe (Simplest)**

- File: `dist\VulnerableEcommerceLab.exe`
- Size: ~50-80 MB
- Everything is bundled inside

**Option 2: .exe + Data folder (If you want easy data reset)**

- `VulnerableEcommerceLab.exe`
- `data\` folder (for wordlists, etc.)
- This allows users to reset data without rebuilding

### How to Share

1. **USB Drive**: Copy the .exe to a USB drive
2. **Network Share**: Place on a shared network folder
3. **Cloud Storage**: Upload to Google Drive, Dropbox, etc.
4. **GitHub Release**: Create a release with the .exe as an asset

### Instructions for Users

Create a simple text file (`INSTRUCTIONS.txt`) to include:

```
Vulnerable E-Commerce Lab - Standalone Application

HOW TO RUN:
1. Double-click VulnerableEcommerceLab.exe
2. Wait for the console window to appear
3. Browser will open automatically to http://127.0.0.1:5000
4. Start practicing!

HOW TO STOP:
- Press Ctrl+C in the console window
- Or simply close the console window

SYSTEM REQUIREMENTS:
- Windows 7/8/10/11
- No Python installation needed
- No internet connection required (runs locally)

TROUBLESHOOTING:
- If Windows Defender blocks it, click "More info" → "Run anyway"
  (This is a false positive due to PyInstaller)
- If port 5000 is in use, close other applications using that port
- Make sure you have at least 200 MB free disk space

⚠️ WARNING:
This application contains intentional security vulnerabilities
for educational purposes only. Do not use with real data!
```

## 🛠️ Advanced Build Options

### Build with Custom Icon

1. Get an `.ico` file (you can convert PNG to ICO online)
2. Save it as `icon.ico` in the project directory
3. Update the spec file:
   ```python
   icon='icon.ico'
   ```
4. Rebuild: `pyinstaller VulnerableEcommerceLab.spec`

### Build Without Console Window

If you want a GUI-only version (no console):

1. Edit `VulnerableEcommerceLab.spec`
2. Change `console=True` to `console=False`
3. Rebuild

**Note**: This is NOT recommended because users won't see error messages or know how to stop the server.

### Optimize File Size

```powershell
# Use UPX compression (already enabled in spec file)
# Install UPX first: https://upx.github.io/

# Build with optimization
pyinstaller --onefile --upx-dir="C:\path\to\upx" VulnerableEcommerceLab.spec
```

### Build for Specific Python Version

```powershell
# Use a specific Python version
py -3.10 -m PyInstaller VulnerableEcommerceLab.spec
```

## 🔧 Troubleshooting Build Issues

### Issue: "Failed to execute script"

**Solution**: Add missing hidden imports to the spec file:

```python
hiddenimports=[
    'flask',
    'werkzeug',
    'jinja2',
    'click',
    'itsdangerous',
    'markupsafe',
    'sqlite3',
],
```

### Issue: Templates not found

**Solution**: Verify data files in spec:

```python
datas=[
    ('templates', 'templates'),
    ('static', 'static'),
    ('data', 'data'),
    ('app.py', '.'),
],
```

### Issue: Large file size

**Solutions**:

- Use `--onefile` option (already used)
- Enable UPX compression (already enabled)
- Exclude unnecessary packages:
  ```python
  excludes=['matplotlib', 'numpy', 'pandas'],
  ```

### Issue: Antivirus flags the .exe

**This is normal!** PyInstaller executables are often flagged as false positives.

**Solutions**:

1. Add exception in Windows Defender
2. Submit to antivirus vendors as false positive
3. Code sign the executable (requires certificate)
4. Distribute with a README explaining this is expected

### Issue: Database errors

**Solution**: Make sure the database is created fresh on first run. The `create_exe.py` launcher handles this with `init_db()`.

## 📊 Build Output Structure

```
vulnerable_ecommerce/
├── build/                    # Temporary build files (can delete)
├── dist/                     # Your executable is here!
│   └── VulnerableEcommerceLab.exe
├── create_exe.py            # Launcher script
├── VulnerableEcommerceLab.spec  # Build configuration
└── ... (other project files)
```

## 🎓 For Instructors

### Creating a Lab Package

1. **Build the executable**
2. **Create a folder structure**:
   ```
   VulnerableEcommerceLab_v1.0/
   ├── VulnerableEcommerceLab.exe
   ├── INSTRUCTIONS.txt
   ├── LAB_GUIDE.pdf (your lab instructions)
   └── README.txt
   ```
3. **Zip the folder**
4. **Distribute to students**

### Version Management

Include version info in the build:

1. Edit `create_exe.py` to show version:

   ```python
   print("  Version 1.0 - February 2026")
   ```

2. Rename output:
   ```powershell
   # After building
   cd dist
   ren VulnerableEcommerceLab.exe VulnerableEcommerceLab_v1.0.exe
   ```

### Multiple Builds

Create different builds for different labs:

```powershell
# Build for Lab 1-4 only
pyinstaller --onefile --name "VulnLab_Basic" create_exe.py

# Build for all labs
pyinstaller --onefile --name "VulnLab_Complete" create_exe.py
```

## 🔒 Security Considerations

### Code Obfuscation

PyInstaller provides basic obfuscation, but the code can still be extracted.

**For additional protection**:

1. Use PyArmor for code obfuscation
2. Add license checks
3. Implement time-limited access

### Distribution Security

- **Checksum**: Provide SHA256 hash of the .exe
  ```powershell
  certutil -hashfile VulnerableEcommerceLab.exe SHA256
  ```
- **Digital Signature**: Sign the .exe with a code signing certificate (optional, costs money)

## 📝 Automation Script

Create `build.bat` for easy rebuilding:

```batch
@echo off
echo Building Vulnerable E-Commerce Lab Executable...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Clean previous builds
rmdir /s /q build dist 2>nul

REM Build the executable
pyinstaller VulnerableEcommerceLab.spec

echo.
echo Build complete!
echo Executable location: dist\VulnerableEcommerceLab.exe
echo.
pause
```

Save as `build.bat` and double-click to build!

## 🎯 Alternative: Portable Python Distribution

If .exe doesn't work for you, create a **portable Python package**:

1. Use **WinPython** or **Python Embedded**
2. Bundle Python + your app + dependencies
3. Create a `run.bat` file:
   ```batch
   @echo off
   python\python.exe app.py
   pause
   ```

## 📞 Support

### Common Questions

**Q: How big will the .exe be?**
A: Approximately 50-80 MB (includes Python runtime)

**Q: Will it work on Mac/Linux?**
A: No, this creates a Windows .exe. For Mac/Linux, use PyInstaller on those platforms.

**Q: Can I reduce the file size?**
A: Yes, use UPX compression and exclude unnecessary packages.

**Q: Is it safe to distribute?**
A: Yes, but warn users about antivirus false positives.

**Q: Can users modify the labs?**
A: No, the code is bundled. For modifications, distribute the source code instead.

---

## ✅ Final Checklist

Before distributing:

- [ ] Test the .exe on a clean Windows machine (no Python installed)
- [ ] Verify all labs (1-8) work correctly
- [ ] Check that browser auto-opens
- [ ] Ensure database initializes properly
- [ ] Test file uploads (Lab 5)
- [ ] Verify static files load correctly
- [ ] Create user instructions
- [ ] Calculate and provide SHA256 checksum
- [ ] Test on different Windows versions (7, 10, 11)
- [ ] Scan with antivirus (expect false positives)

---

**You're ready to distribute! 🚀**

Students can now run the lab with just a double-click!
