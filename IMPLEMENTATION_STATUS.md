# Lab Variations - Implementation Status

## ✅ COMPLETED LABS

### Lab 1: Path Traversal (3 Variations - COMPLETE)

1. **DocuVault** (Blue) - Document Management
   - Route: `/lab1/1`
   - Files: invoice1.txt, invoice2.txt, readme.txt
   - Path: `/data/docuvault/invoices/`
   - Exploit: `../../../etc/passwd`

2. **ShopExpress** (Orange) - E-commerce Receipts
   - Route: `/lab1/2`
   - Files: order_12345.pdf, order_12346.pdf, receipt_001.pdf
   - Path: `/data/shopexpress/receipts/2024/`
   - Exploit: `../../../../etc/passwd`

3. **MediaHub** (Pink) - Photo Gallery
   - Route: `/lab1/3`
   - Files: photo_001.jpg, photo_002.jpg, photo_003.jpg
   - Path: `/data/mediahub/gallery/uploads/`
   - Exploit: `../../../../etc/passwd`

---

### Lab 3.2: 2FA Bypass (3 Variations - COMPLETE)

1. **SecureShop** (Indigo) - E-commerce
   - Route: `/lab3/2`
   - Credentials: wiener:peter / carlos:montoya
   - Account URL: `/lab3/2/my-account`
   - Flag: `FLAG{two_factor_authentication_bypass_master}`

2. **BankSecure** (Green) - Online Banking
   - Route: `/lab3/2b`
   - Credentials: alice:alice123 / bob:bob456
   - Account URL: `/lab3/2b/dashboard`
   - Flag: `FLAG{two_factor_authentication_bypass_banksecure}`

3. **CloudDrive** (Red) - Cloud Storage
   - Route: `/lab3/2c`
   - Credentials: user1:pass1 / admin:admin2024
   - Account URL: `/lab3/2c/files`
   - Flag: `FLAG{two_factor_authentication_bypass_clouddrive}`

---

## ✅ EXISTING SINGLE VARIATIONS

### Lab 2.1: Robots.txt

- Route: `/lab2/1`
- robots.txt reveals: `/admin-panel`
- Flag: `FLAG{robots_txt_disclosure_master}`

### Lab 2.2: Hidden Admin Panel

- Route: `/lab2/2`
- Hidden link in HTML: `/secret-admin`
- Flag: `FLAG{hidden_admin_panel_master}`

### Lab 2.3: Cookie Manipulation

- Route: `/lab2/3`
- Cookie: `Admin=false` → `Admin=true`
- Flag: `FLAG{cookie_manipulation_master}`

### Lab 2.4: IDOR (Parameter Tampering)

- Route: `/lab2/4`
- URL: `/my-account?id=user` → `?id=admin`
- Credentials: user/password, admin/[varies]
- Flag: `FLAG{idor_parameter_tampering_master}`

### Lab 2.5: Password Disclosure

- Route: `/lab2/5`
- Credentials: user/password, admin/[random]
- Profile URL: `/lab2/5/profile?username=admin`
- Flag: `FLAG{password_disclosure_idor_master}`

### Lab 3.1: Brute Force Attack

- Route: `/lab3/1`
- Wordlists: 100 usernames × 100 passwords
- Random credentials on each access
- Flag: `FLAG{brute_force_authentication_master}`

---

## 📊 SUMMARY

### Total Labs Implemented:

- **Lab 1:** 3 variations ✅
- **Lab 2:** 5 sub-labs (1 variation each) ✅
- **Lab 3.1:** 1 variation ✅
- **Lab 3.2:** 3 variations ✅

### Total Unique Lab Experiences: **12**

### Breakdown:

- Path Traversal: 3 variations
- Robots.txt: 1 variation
- Hidden Admin: 1 variation
- Cookie Manipulation: 1 variation
- IDOR: 1 variation
- Password Disclosure: 1 variation
- Brute Force: 1 variation
- 2FA Bypass: 3 variations

---

## 🎯 FUTURE ENHANCEMENTS (Optional)

If you want to expand further, you can add 2 more variations for each Lab 2 sub-lab and Lab 3.1:

### Lab 2 Additional Variations (12 more labs):

- Lab 2.1: +2 variations (FashionHub, FoodMart)
- Lab 2.2: +2 variations (BookStore, GameZone)
- Lab 2.3: +2 variations (SportsGear, PetShop)
- Lab 2.4: +2 variations (JewelryStore, ElectroMart)
- Lab 2.5: +2 variations (CloudMart, DataVault)

### Lab 3.1 Additional Variations (2 more labs):

- SecureBank (Blue banking theme)
- TechHub (Orange tech company theme)

**Potential Total:** 26 unique lab experiences

---

## 🚀 CURRENT STATUS: PRODUCTION READY

The application currently has **12 fully functional, professionally designed lab variations** ready for students to practice with. Each lab provides:

✅ Realistic website themes
✅ Professional UI/UX
✅ Different credentials and branding
✅ Same vulnerability for consistent learning
✅ Unique flags for tracking completion
✅ No hints or guidance (black-box testing)

The labs are ready for deployment and student use!
