# Lab Navigation Guide

## 🏠 Main Menu

**URL:** `http://localhost:5000/`

From here you'll see:

- **Lab 1: Path Traversal** - Badge shows "3 Variations"
- **Lab 2: Access Control** - Badge shows "5 Sub-Labs"
- **Lab 3: Authentication** - Badge shows "2 Types"

---

## 📂 Lab 1: Path Traversal (3 Variations)

### Navigation Path:

1. Main Menu → Click "View Variations"
2. **URL:** `/lab1/menu` or `/lab1`

### Available Variations:

- **Lab 1.1: DocuVault** (Blue) - `/lab1/1`
- **Lab 1.2: ShopExpress** (Orange) - `/lab1/2`
- **Lab 1.3: MediaHub** (Pink) - `/lab1/3`

---

## 🔐 Lab 2: Access Control (5 Sub-Labs)

### Navigation Path:

1. Main Menu → Click "View Sub-Labs"
2. **URL:** `/lab2`

### Available Sub-Labs:

- **Lab 2.1: Robots.txt** - `/lab2/1`
- **Lab 2.2: Hidden Admin** - `/lab2/2`
- **Lab 2.3: Cookie Manipulation** - `/lab2/3`
- **Lab 2.4: IDOR** - `/lab2/4`
- **Lab 2.5: Password Disclosure** - `/lab2/5`

---

## 🔑 Lab 3: Authentication (2 Types, 4 Total Labs)

### Navigation Path:

1. Main Menu → Click "View Sub-Labs"
2. **URL:** `/lab3`

### Lab 3.1: Brute Force Attack

- **Single variation:** `/lab3/1`

### Lab 3.2: 2FA Bypass (3 Variations)

**Navigation Path:**

1. Lab 3 Menu → Click "View Variations" for Lab 3.2
2. **URL:** `/lab3/2/menu`

**Available Variations:**

- **Variation A: SecureShop** (Indigo) - `/lab3/2`
  - Credentials: wiener:peter / carlos:montoya
  - Exploit URL: `/lab3/2/my-account`

- **Variation B: BankSecure** (Green) - `/lab3/2b`
  - Credentials: alice:alice123 / bob:bob456
  - Exploit URL: `/lab3/2b/dashboard`

- **Variation C: CloudDrive** (Red) - `/lab3/2c`
  - Credentials: user1:pass1 / admin:admin2024
  - Exploit URL: `/lab3/2c/files`

---

## 🎯 Quick Access URLs

### Lab 1 Variations:

```
http://localhost:5000/lab1/1  # DocuVault
http://localhost:5000/lab1/2  # ShopExpress
http://localhost:5000/lab1/3  # MediaHub
```

### Lab 2 Sub-Labs:

```
http://localhost:5000/lab2/1  # Robots.txt
http://localhost:5000/lab2/2  # Hidden Admin
http://localhost:5000/lab2/3  # Cookie Manipulation
http://localhost:5000/lab2/4  # IDOR
http://localhost:5000/lab2/5  # Password Disclosure
```

### Lab 3 Sub-Labs:

```
http://localhost:5000/lab3/1   # Brute Force
http://localhost:5000/lab3/2   # 2FA Bypass - SecureShop
http://localhost:5000/lab3/2b  # 2FA Bypass - BankSecure
http://localhost:5000/lab3/2c  # 2FA Bypass - CloudDrive
```

---

## 📊 Total Lab Count

- **12 Unique Lab Experiences**
  - Lab 1: 3 variations
  - Lab 2: 5 sub-labs
  - Lab 3: 4 labs (1 brute force + 3 2FA variations)

---

## 💡 Tips

1. **Badges on cards** show how many variations/sub-labs are available
2. **Menu pages** provide easy navigation between variations
3. **Each variation** has the same vulnerability but different themes
4. **Flags are unique** for each variation to track completion
