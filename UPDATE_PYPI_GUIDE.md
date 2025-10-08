# How to Update Your Package on PyPI

## 🎯 Quick Steps Overview

1. **Update version number**
2. **Clean old build files**
3. **Build new distribution**
4. **Upload to PyPI**
5. **Verify installation**

---

## 📝 Detailed Step-by-Step Guide

### Step 1: Update Version Number

Open `setup.py` and increment the version:

```python
setup(
    name="sap-odata-connector-testcov",
    version="1.0.1",  # ← Change this (was 1.0.0)
    # ... rest of setup
)
```

**Version Numbering Guide:**
- `1.0.0` → `1.0.1` - Bug fixes, small changes
- `1.0.0` → `1.1.0` - New features, backward compatible
- `1.0.0` → `2.0.0` - Breaking changes

**For your changes (bug fixes + improvements), use: `1.0.1`**

---

### Step 2: Clean Old Build Files

**Windows PowerShell:**
```powershell
# Remove old build directories
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

# Or manually delete these folders:
# - dist/
# - build/
# - sap_odata_connector_testcov.egg-info/
```

**Windows CMD:**
```cmd
rmdir /s /q dist
rmdir /s /q build
rmdir /s /q sap_odata_connector_testcov.egg-info
```

**Why?** Old build files can cause conflicts. Always start fresh.

---

### Step 3: Build New Distribution

```powershell
# Make sure you're in the package directory
cd "c:\Users\Mothe Bhuvan Chandra\Documents\sap_odata_connector"

# Build the package
python setup.py sdist bdist_wheel
```

**Expected Output:**
```
running sdist
running egg_info
writing sap_odata_connector_testcov.egg-info\PKG-INFO
...
running bdist_wheel
...
creating dist\sap_odata_connector_testcov-1.0.1-py3-none-any.whl
creating dist\sap-odata-connector-testcov-1.0.1.tar.gz
```

**Verify:** Check that `dist/` folder contains:
- `sap_odata_connector_testcov-1.0.1-py3-none-any.whl`
- `sap-odata-connector-testcov-1.0.1.tar.gz`

---

### Step 4: Upload to PyPI

```powershell
# Upload to PyPI
twine upload dist/*
```

**You'll be prompted for:**
```
Enter your username: __token__
Enter your password: [Your PyPI API token]
```

**Expected Output:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading sap_odata_connector_testcov-1.0.1-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
Uploading sap-odata-connector-testcov-1.0.1.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View at:
https://pypi.org/project/sap-odata-connector-testcov/1.0.1/
```

---

### Step 5: Verify Installation

**Wait 2-3 minutes** for PyPI to process, then test:

```powershell
# Create a test environment
python -m venv test_env
.\test_env\Scripts\activate

# Install the updated package
pip install sap-odata-connector-testcov --upgrade

# Verify version
python -c "import odc; print('Installed successfully!')"

# Deactivate and clean up
deactivate
Remove-Item -Recurse -Force test_env
```

---

## 🔧 Complete Commands (Copy-Paste Ready)

### Option A: PowerShell (Recommended)

```powershell
# Navigate to package directory
cd "c:\Users\Mothe Bhuvan Chandra\Documents\sap_odata_connector"

# Step 1: Clean old builds
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

# Step 2: Build new distribution
python setup.py sdist bdist_wheel

# Step 3: Upload to PyPI
twine upload dist/*

# Step 4: Verify (wait 2-3 minutes first)
pip install sap-odata-connector-testcov --upgrade
```

### Option B: Using Build Script

Create a file `update_pypi.ps1`:

```powershell
# update_pypi.ps1
Write-Host "🚀 Updating PyPI Package..." -ForegroundColor Cyan

# Clean
Write-Host "📦 Cleaning old builds..." -ForegroundColor Yellow
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

# Build
Write-Host "🔨 Building distribution..." -ForegroundColor Yellow
python setup.py sdist bdist_wheel

# Check if build succeeded
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build successful!" -ForegroundColor Green
    
    # Upload
    Write-Host "📤 Uploading to PyPI..." -ForegroundColor Yellow
    twine upload dist/*
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Upload successful!" -ForegroundColor Green
        Write-Host "🎉 Package updated on PyPI!" -ForegroundColor Cyan
    } else {
        Write-Host "✗ Upload failed!" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Build failed!" -ForegroundColor Red
}
```

Then run:
```powershell
.\update_pypi.ps1
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: "File already exists"

**Error:**
```
HTTPError: 400 Bad Request
File already exists
```

**Solution:**
You forgot to increment the version number! Go back to Step 1 and change the version in `setup.py`.

---

### Issue 2: "Invalid username or password"

**Error:**
```
HTTPError: 403 Forbidden
Invalid or non-existent authentication information
```

**Solution:**
- Username should be: `__token__`
- Password should be your PyPI API token (starts with `pypi-`)
- Get token from: https://pypi.org/manage/account/token/

---

### Issue 3: "twine: command not found"

**Error:**
```
twine : The term 'twine' is not recognized
```

**Solution:**
```powershell
pip install twine --upgrade
```

---

### Issue 4: Build files not created

**Error:**
No files in `dist/` folder after build

**Solution:**
```powershell
# Check for errors in setup.py
python setup.py check

# Try building again with verbose output
python setup.py sdist bdist_wheel --verbose
```

---

## 📊 Version History Tracking

After each update, document your changes:

Create/Update `CHANGELOG.md`:

```markdown
# Changelog

## [1.0.1] - 2025-10-07

### Added
- Enhanced logging with colored output
- Centralized log messages for better debugging
- Global record tracker registration

### Fixed
- Entity registration with global tracker
- Improved error messages
- Better troubleshooting information

### Changed
- Removed "lightweight" terminology from logs
- Improved log message clarity

## [1.0.0] - 2025-10-06

### Initial Release
- SAP OData connector with automatic pagination
- Support for filters, expansion, field selection
- Comprehensive documentation
```

---

## 🎯 Best Practices

### 1. Always Test Locally First

```powershell
# Install in development mode
pip install -e .

# Run your tests
pytest tests/ -v

# Test the actual functionality
python test_new_filter.py
```

### 2. Update Documentation

If you added new features, update:
- README.md (if exists)
- Docstrings in code
- CHANGELOG.md

### 3. Git Commit Before Publishing

```powershell
git add .
git commit -m "Version 1.0.1 - Bug fixes and logging improvements"
git tag v1.0.1
git push origin main --tags
```

### 4. Keep PyPI Token Secure

**Never commit your PyPI token to git!**

Store it in:
- Environment variable
- Password manager
- `.pypirc` file (add to `.gitignore`)

---

## 🔐 Setting Up .pypirc (Optional)

Create `C:\Users\Mothe Bhuvan Chandra\.pypirc`:

```ini
[distutils]
index-servers =
    pypi

[pypi]
username = __token__
password = pypi-your-token-here
```

Then you can upload without entering credentials:
```powershell
twine upload dist/*
```

**⚠️ Important:** Add `.pypirc` to `.gitignore`!

---

## ✅ Checklist Before Publishing

- [ ] Version number incremented in `setup.py`
- [ ] Code tested locally
- [ ] Tests passing (`pytest tests/`)
- [ ] Old build files cleaned
- [ ] New distribution built successfully
- [ ] CHANGELOG.md updated (optional)
- [ ] Git committed (optional but recommended)
- [ ] Ready to upload!

---

## 🎉 Quick Reference

```powershell
# The 4 essential commands:
cd "c:\Users\Mothe Bhuvan Chandra\Documents\sap_odata_connector"
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python setup.py sdist bdist_wheel
twine upload dist/*
```

---

## 📞 If You Get Stuck

**Try these in order:**

1. **Check version number** - Did you increment it?
2. **Check PyPI token** - Is it correct?
3. **Check build output** - Any errors during build?
4. **Check internet** - Can you access pypi.org?
5. **Ask me!** - I'll help you debug

---

## 🚀 You're Ready!

Follow the steps above, and if you encounter any issues, just let me know:
- What step you're on
- What error message you see
- What you've tried

I'll help you resolve it immediately!

---

**Good luck with your update!** 🎊
