# Lab 2 Variations - Implementation Plan

## Overview

Creating 3 themed variations for each of the 5 Lab 2 sub-labs.
Total: 15 variations (5 existing + 10 new)

---

## Lab 2.1: Robots.txt Disclosure

### Variation A: TechStore (Blue) ✅ EXISTS

- Route: `/lab2/1`
- robots.txt reveals: `/admin-panel`
- Flag: `FLAG{robots_txt_disclosure_master}`

### Variation B: FashionHub (Purple) ❌ TO CREATE

- Route: `/lab2/1b`
- robots.txt reveals: `/management`
- Flag: `FLAG{robots_txt_fashionhub}`
- Theme: Fashion e-commerce, purple gradient

### Variation C: FoodMart (Green) ❌ TO CREATE

- Route: `/lab2/1c`
- robots.txt reveals: `/backend`
- Flag: `FLAG{robots_txt_foodmart}`
- Theme: Food delivery, green theme

---

## Lab 2.2: Hidden Admin Panel

### Variation A: GadgetShop (Cyan) ✅ EXISTS

- Route: `/lab2/2`
- Hidden link: `/secret-admin`
- Flag: `FLAG{hidden_admin_panel_master}`

### Variation B: BookStore (Brown) ❌ TO CREATE

- Route: `/lab2/2b`
- Hidden link: `/admin-portal`
- Flag: `FLAG{hidden_admin_bookstore}`
- Theme: Bookstore, brown/beige theme

### Variation C: GameZone (Red) ❌ TO CREATE

- Route: `/lab2/2c`
- Hidden link: `/control-panel`
- Flag: `FLAG{hidden_admin_gamezone}`
- Theme: Gaming store, red theme

---

## Lab 2.3: Cookie Manipulation

### Variation A: MusicStore (Indigo) ✅ EXISTS

- Route: `/lab2/3`
- Cookie: `Admin=false` → `Admin=true`
- Flag: `FLAG{cookie_manipulation_master}`

### Variation B: SportsGear (Orange) ❌ TO CREATE

- Route: `/lab2/3b`
- Cookie: `Role=user` → `Role=admin`
- Flag: `FLAG{cookie_manipulation_sportsgear}`
- Theme: Sports equipment, orange theme

### Variation C: PetShop (Pink) ❌ TO CREATE

- Route: `/lab2/3c`
- Cookie: `IsAdmin=0` → `IsAdmin=1`
- Flag: `FLAG{cookie_manipulation_petshop}`
- Theme: Pet store, pink theme

---

## Lab 2.4: IDOR (Parameter Tampering)

### Variation A: AutoParts (Gray) ✅ EXISTS

- Route: `/lab2/4`
- URL: `/my-account?id=user` → `?id=admin`
- Credentials: user/password, admin/[random]
- Flag: `FLAG{idor_parameter_tampering_master}`

### Variation B: JewelryStore (Gold) ❌ TO CREATE

- Route: `/lab2/4b`
- URL: `/profile?user=customer` → `?user=manager`
- Credentials: customer/pass123, manager/secure456
- Flag: `FLAG{idor_jewelrystore}`
- Theme: Jewelry, gold/yellow theme

### Variation C: ElectroMart (Blue) ❌ TO CREATE

- Route: `/lab2/4c`
- URL: `/dashboard?account=buyer` → `?account=seller`
- Credentials: buyer/buy123, seller/sell456
- Flag: `FLAG{idor_electromart}`
- Theme: Electronics, blue theme

---

## Lab 2.5: Password Disclosure

### Variation A: ShopHub (Purple) ✅ EXISTS

- Route: `/lab2/5`
- Credentials: user/password, admin/[random]
- Profile URL: `/lab2/5/profile?username=admin`
- Flag: `FLAG{password_disclosure_idor_master}`

### Variation B: CloudMart (Teal) ❌ TO CREATE

- Route: `/lab2/5b`
- Credentials: guest/guest123, root/[random]
- Profile URL: `/lab2/5b/account?user=root`
- Flag: `FLAG{password_disclosure_cloudmart}`
- Theme: Cloud services, teal theme

### Variation C: DataVault (Red) ❌ TO CREATE

- Route: `/lab2/5c`
- Credentials: viewer/view123, owner/[random]
- Profile URL: `/lab2/5c/info?id=owner`
- Flag: `FLAG{password_disclosure_datavault}`
- Theme: Data storage, red theme

---

## Implementation Priority

Given the scope, I'll implement in this order:

1. **Create 5 menu pages** (one for each sub-lab)
2. **Lab 2.5 variations** (most complex, similar to existing)
3. **Lab 2.4 variations** (IDOR, important concept)
4. **Lab 2.3 variations** (cookie manipulation)
5. **Lab 2.1 & 2.2 variations** (simpler)

---

## Files to Create

### Menu Pages (5):

- `templates/lab2/sub1_menu.html`
- `templates/lab2/sub2_menu.html`
- `templates/lab2/sub3_menu.html`
- `templates/lab2/sub4_menu.html`
- `templates/lab2/sub5_menu.html`

### Variation Templates (10 new):

- Lab 2.1: `sub1b.html`, `sub1c.html` + robots files
- Lab 2.2: `sub2b.html`, `sub2c.html`, `sub2b_admin.html`, `sub2c_admin.html`
- Lab 2.3: `sub3b.html`, `sub3c.html`, `sub3b_admin.html`, `sub3c_admin.html`
- Lab 2.4: `sub4b.html`, `sub4c.html`, `sub4b_account.html`, `sub4c_account.html`
- Lab 2.5: `sub5b.html`, `sub5c.html`, `sub5b_profile.html`, `sub5c_profile.html`

### Routes in app.py:

- 5 menu routes
- 10+ variation routes

**Total New Files:** ~35 files
