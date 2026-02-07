# Lab Variations Structure

## Overview

Each sub-lab will have 3 themed variations with the same vulnerability but different:

- Website themes and colors
- Branding and UI
- Credentials (where applicable)
- URLs and endpoints

---

## Lab 1: Path Traversal (✅ COMPLETE)

### 1.1: DocuVault (Blue) - Document Management

- Files: invoice1.txt, invoice2.txt, readme.txt
- Path: `/data/docuvault/invoices/`
- Exploit: `../../../etc/passwd`

### 1.2: ShopExpress (Orange) - E-commerce Receipts

- Files: order_12345.pdf, order_12346.pdf, receipt_001.pdf
- Path: `/data/shopexpress/receipts/2024/`
- Exploit: `../../../../etc/passwd`

### 1.3: MediaHub (Pink) - Photo Gallery

- Files: photo_001.jpg, photo_002.jpg, photo_003.jpg
- Path: `/data/mediahub/gallery/uploads/`
- Exploit: `../../../../etc/passwd`

---

## Lab 2: Access Control

### 2.1: Robots.txt Disclosure

**Variation A: TechStore (Blue)**

- robots.txt reveals `/admin-panel`
- Flag: `FLAG{robots_txt_techstore}`

**Variation B: FashionHub (Purple)**

- robots.txt reveals `/management`
- Flag: `FLAG{robots_txt_fashionhub}`

**Variation C: FoodMart (Green)**

- robots.txt reveals `/backend`
- Flag: `FLAG{robots_txt_foodmart}`

### 2.2: Hidden Admin Panel

**Variation A: GadgetShop (Cyan)**

- Hidden link in HTML: `/secret-admin`
- Flag: `FLAG{hidden_admin_gadgetshop}`

**Variation B: BookStore (Brown)**

- Hidden link in HTML: `/admin-portal`
- Flag: `FLAG{hidden_admin_bookstore}`

**Variation C: GameZone (Red)**

- Hidden link in HTML: `/control-panel`
- Flag: `FLAG{hidden_admin_gamezone}`

### 2.3: Cookie Manipulation

**Variation A: MusicStore (Indigo)**

- Cookie: `Admin=false` → `Admin=true`
- Flag: `FLAG{cookie_manipulation_musicstore}`

**Variation B: SportsGear (Orange)**

- Cookie: `Role=user` → `Role=admin`
- Flag: `FLAG{cookie_manipulation_sportsgear}`

**Variation C: PetShop (Pink)**

- Cookie: `IsAdmin=0` → `IsAdmin=1`
- Flag: `FLAG{cookie_manipulation_petshop}`

### 2.4: IDOR (Parameter Tampering)

**Variation A: AutoParts (Gray)**

- URL: `/my-account?id=user` → `?id=admin`
- Credentials: user/password, admin/admin123
- Flag: `FLAG{idor_autoparts}`

**Variation B: JewelryStore (Gold)**

- URL: `/profile?user=customer` → `?user=manager`
- Credentials: customer/pass123, manager/secure456
- Flag: `FLAG{idor_jewelrystore}`

**Variation C: ElectroMart (Blue)**

- URL: `/dashboard?account=buyer` → `?account=seller`
- Credentials: buyer/buy123, seller/sell456
- Flag: `FLAG{idor_electromart}`

### 2.5: Password Disclosure

**Variation A: ShopHub (Purple)** - ✅ EXISTING

- Credentials: user/password, admin/[random]
- Profile URL: `/lab2/5/profile?username=admin`
- Flag: `FLAG{password_disclosure_idor_master}`

**Variation B: CloudMart (Teal)**

- Credentials: guest/guest123, root/[random]
- Profile URL: `/lab2/5b/account?user=root`
- Flag: `FLAG{password_disclosure_cloudmart}`

**Variation C: DataVault (Red)**

- Credentials: viewer/view123, owner/[random]
- Profile URL: `/lab2/5c/info?id=owner`
- Flag: `FLAG{password_disclosure_datavault}`

---

## Lab 3: Authentication

### 3.1: Brute Force Attack

**Variation A: CyberMart (Green)** - ✅ EXISTING

- Wordlists: 100 usernames × 100 passwords
- Random credentials on each access
- Flag: `FLAG{brute_force_authentication_master}`

**Variation B: SecureBank (Blue)**

- Same wordlists
- Different theme: Banking
- Flag: `FLAG{brute_force_securebank}`

**Variation C: TechHub (Orange)**

- Same wordlists
- Different theme: Tech Company
- Flag: `FLAG{brute_force_techhub}`

### 3.2: 2FA Bypass

**Variation A: SecureShop (Indigo)** - ✅ EXISTING

- Credentials: wiener/peter, carlos/montoya
- Account URL: `/lab3/2/my-account`
- Flag: `FLAG{two_factor_authentication_bypass_master}`

**Variation B: BankSecure (Green)** - ⚠️ BACKEND READY

- Credentials: alice/alice123, bob/bob456
- Account URL: `/lab3/2b/dashboard`
- Flag: `FLAG{two_factor_authentication_bypass_banksecure}`

**Variation C: CloudDrive (Red)** - ⚠️ BACKEND READY

- Credentials: user1/pass1, admin/admin2024
- Account URL: `/lab3/2c/files`
- Flag: `FLAG{two_factor_authentication_bypass_clouddrive}`

---

## Implementation Priority

### High Priority (Core Learning):

1. ✅ Lab 1 - All 3 variations complete
2. ⚠️ Lab 3.2 - Finish B & C templates
3. ⚠️ Lab 2.4 - Create 2 more IDOR variations
4. ⚠️ Lab 2.5 - Create 2 more Password Disclosure variations

### Medium Priority:

5. Lab 2.3 - Create 2 more Cookie Manipulation variations
6. Lab 3.1 - Create 2 more Brute Force variations

### Lower Priority (Simpler vulnerabilities):

7. Lab 2.1 - Create 2 more Robots.txt variations
8. Lab 2.2 - Create 2 more Hidden Admin variations

---

## Total Count:

- **Lab 1:** 3 variations ✅
- **Lab 2:** 5 vulnerabilities × 3 variations = 15 sub-labs
- **Lab 3:** 2 vulnerabilities × 3 variations = 6 sub-labs
- **TOTAL:** 24 unique lab experiences!
