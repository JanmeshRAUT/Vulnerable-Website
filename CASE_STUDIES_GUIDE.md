# Security Case Studies - Labs 4, 5, 7, 8, 9
## Complete Guide & Overview

---

## 📋 What You Have

Five detailed case study documents have been created, each presenting real-world security problems that require hands-on exploitation and remediation:

1. **CASE_STUDY_LAB4.md** - Server-Side Request Forgery (SSRF)
2. **CASE_STUDY_LAB5.md** - File Upload Vulnerabilities
3. **CASE_STUDY_LAB7.md** - SQL Injection
4. **CASE_STUDY_LAB8.md** - Cross-Site Scripting (XSS)
5. **CASE_STUDY_LAB9.md** - Mobile Binary Analysis

---

## 🎯 Quick Reference Table

| Lab | Vulnerability | Difficulty | Time | Key Skills |
|-----|---|---|---|---|
| **Lab 4** | SSRF | Medium | 30-45min | HTTP requests, URL encoding, network concepts |
| **Lab 5** | File Upload | Medium | 45-60min | File validation bypasses, code execution |
| **Lab 7** | SQL Injection | Hard | 60-90min | Database queries, UNION operations, blind extraction |
| **Lab 8** | XSS | Medium | 30-60min | Context awareness, HTML/JS syntax, browser behavior |
| **Lab 9** | Mobile Analysis | Medium | 45-75min | Binary analysis tools, string extraction, decompilation |

---

## 📚 Case Study Structure

Each document includes:

```
├── Business Context (real-world scenario)
├── Executive Summary
├── Business Problem (what went wrong)
├── Multiple Challenges
│   ├── Problem Statement
│   ├── Vulnerability Description
│   ├── Attack Vectors
│   ├── Step-by-step Objectives
│   └── Why It Works
├── General Exploitation Guide (how to approach)
├── Technical Concepts (learning material)
├── Tools & Techniques
├── Expected Discoveries (what you should find)
├── Defense Strategies (how to fix)
├── Real-World Impact (consequences)
└── Flag Submission Checklist
```

---

## 🚀 How to Use These Case Studies

### For Each Lab:

#### Step 1: Read the Case Study
- Understand the business context
- Grasp the security problem
- Learn what you're looking for

#### Step 2: Analyze the Challenges
- Different variants/difficulty levels
- Multiple exploitation paths
- Escalating complexity

#### Step 3: Follow the Exploitation Guide
- Step-by-step methodology
- Tool recommendations
- Proper technique application

#### Step 4: Execute Against the Lab
- Apply techniques to actual application
- Document your processes
- Capture flags/evidence

#### Step 5: Learn the Defense
- Understand root causes
- Learn prevention strategies
- Review code-level fixes

---

## 📖 Lab Descriptions

### Lab 4: Server-Side Request Forgery (SSRF)
**Main Concept**: Making the server request URLs you control to access internal resources

**What You'll Do**:
- Force server to access `http://localhost/admin`
- Navigate admin panel through SSRF
- Extract admin deletion URLs
- Execute admin operations

**Key Skills**:
- URL parameter manipulation
- Understanding HTTP client behavior
- Internal network concepts
- Interception & analysis

**Expected Outcomes**:
1. Access restricted internal admin panel
2. Delete user accounts via SSRF
3. Access metadata/configuration services
4. Understand attack chain

---

### Lab 5: File Upload Vulnerabilities
**Main Concept**: Bypassing file validation to upload and execute malicious code

**What You'll Do**:
- Upload innocent files first
- Identify file storage locations
- Craft malicious payloads (PHP, SVG, etc.)
- Bypass validation mechanisms
- Execute code on server

**Key Skills**:
- File type validation techniques
- Extension tricks & bypasses
- MIME type spoofing
- Polyglot file creation
- Code execution paths

**Expected Outcomes**:
1. Understand all validation layers
2. Successfully upload executable code
3. Execute code in multiple contexts (PHP, SVG, etc.)
4. Access files before validation

---

### Lab 7: SQL Injection
**Main Concept**: Injecting SQL code into user input to manipulate database queries

**What You'll Do**:
- Inject SQL into product filters
- Extract data using UNION queries
- Bypass authentication
- Extract user/admin credentials
- Learn blind injection techniques

**Key Skills**:
- SQL query structure
- UNION-based extraction
- Authentication bypass patterns
- Boolean blind injection
- Time-based blind techniques
- Database enumeration

**Expected Outcomes**:
1. Extract entire user database
2. Bypass login systems
3. Access admin credentials
4. Demonstrate chained attacks

---

### Lab 8: Cross-Site Scripting (XSS)
**Main Concept**: Injecting JavaScript code to execute in victim's browser

**What You'll Do**:
- Craft payloads for 5 different contexts:
  - HTML content
  - HTML attributes
  - JavaScript strings
  - DOM properties
  - URL protocols
- Execute code in each context
- Fetch data from endpoints

**Key Skills**:
- HTML/JavaScript context awareness
- Breaking out of different contexts
- Event handler usage
- Protocol handlers
- Filter bypass techniques

**Expected Outcomes**:
1. Understand context-specific payloads
2. Execute code in victim browser
3. Access sensitive data
4. Demonstrate session hijacking potential

---

### Lab 9: Mobile Binary Analysis
**Main Concept**: Extracting hardcoded secrets from Android APK files

**What You'll Do**:
- Extract APK as ZIP file
- Decompile DEX to source code
- Search for hardcoded strings
- Extract API keys, credentials
- Analyze AndroidManifest.xml
- Find encryption keys
- Access database credentials

**Key Skills**:
- APK structure understanding
- Decompilation tools (JADX, apktool)
- String extraction & analysis
- Manifest analysis
- Identifying secret patterns

**Expected Outcomes**:
1. Extract API keys from code
2. Find database credentials
3. Identify internal URLs/endpoints
4. Locate encryption keys
5. Demonstrate backend access using extracted secrets

---

## 🛠️ Recommended Tools

### Lab 4 (SSRF)
```
- Burp Suite (Repeater, Intruder)
- OWASP ZAP
- curl command line
- Firefox DevTools
```

### Lab 5 (File Upload)
```
- Burp Suite (modify uploads on-the-fly)
- apktool (for image testing)
- exiftool (metadata manipulation)
- Python requests library
```

### Lab 7 (SQL Injection)
```
- Burp Suite (Intruder for fuzzing)
- sqlmap (automated scanner)
- DB client tools (MySQL Workbench, pgAdmin)
- Python requests
```

### Lab 8 (XSS)
```
- Browser DevTools (Console, Inspector)
- Burp Suite (Repeater)
- OWASP ZAP
- Manual browser testing
```

### Lab 9 (Mobile Analysis)
```
- JADX (decompilation)
- apktool (resource extraction)
- strings command
- MobSF (automated analysis)
- 7-Zip or unzip
```

---

## 📊 Learning Path

### Beginner (Start Here)
1. **Lab 8** - XSS: Visual, straightforward payloads
2. **Lab 4** - SSRF: Clear cause-effect chain
3. **Lab 5** - File Upload: Multiple simple techniques

### Intermediate (Next)
4. **Lab 7** - SQL Injection: More complex, requires DB knowledge
5. **Lab 9** - Mobile: Tools vs technique-heavy

### Advanced (Mastery)
- Combine multiple labs
- Create exploitation chains
- Develop automated tools
- Customize payloads

---

## 🎓 Knowledge Domains Covered

### Web Security Fundamentals
- HTTP protocol & requests
- HTML/CSS/JavaScript interaction
- Browser security model (SOP, CSP)
- Server-client communication

### Injection Attacks
- Code injection principles
- Context-specific payload crafting
- Filter bypass techniques
- Encoding/decoding options

### Authentication & Access Control
- Session management
- Credential handling
- Admin panel abuse
- Privilege escalation

### Data & Secrets
- Sensitive data identification
- Storage security
- Encryption concepts
- Secret management

### Mobile Security
- APK structure
- Decompilation & analysis
- Hardcoded credentials
- Binary security

---

## 🔍 How Each Lab Builds Knowledge

```
Lab 4: SSRF
  ├─ Learn: Server-side operations
  ├─ Understand: Network isolation failures
  └─ Skill: URL manipulation, request interception

Lab 5: File Upload
  ├─ Learn: Validation bypass techniques
  ├─ Understand: File handling security
  └─ Skill: Polyglot files, execution paths

Lab 7: SQL Injection
  ├─ Learn: Database query manipulation
  ├─ Understand: Input validation importance
  └─ Skill: Query analysis, data extraction

Lab 8: XSS
  ├─ Learn: Context-aware coding
  ├─ Understand: Browser execution model
  └─ Skill: Payload crafting, context detection

Lab 9: Mobile Analysis
  ├─ Learn: Binary analysis tools
  ├─ Understand: Application packaging
  └─ Skill: Decompilation, secret extraction
```

---

## 📋 Success Criteria

### For Each Lab You Should:

✅ **Understand**
- Why the vulnerability exists
- How attackers exploit it
- What the impact is

✅ **Demonstrate**
- Successful exploitation
- Data extraction/modification
- Complete attack chain

✅ **Learn**
- Root causes
- Prevention techniques
- Detection methods

✅ **Document**
- Every step taken
- Payloads used
- Results achieved
- Security implications

---

## 🚨 Important Reminders

### During Exploitation:
1. **Follow the guide** - Each challenge has step-by-step instructions
2. **Debug failures** - Tools like Burp Suite help identify issues
3. **Experiment** - Try variations of payloads
4. **Document** - Screenshot/log everything for review
5. **Persist** - Some attacks require multiple attempts

### When Stuck:
1. Re-read the "How It Works" section
2. Check the "Expected Discoveries" section
3. Verify you're using correct syntax
4. Test payload in isolati first
5. Review tool settings

### Flag Submission:
- Each lab provides endpoints for flag validation
- Flags are usually returned via alert() or in response
- Copy exact flag format
- Submit to the platform for credit

---

## 🎯 Quick Navigation

### Find Your Lab

**I want to learn about**: → **Read this case study**
- Accessing internal systems → Lab 4
- Uploading malicious files → Lab 5
- Breaking database security → Lab 7
- Running JavaScript in users' browsers → Lab 8
- Extracting app secrets → Lab 9

---

## 📚 Related Materials

Also check:
- `LAB_8.1_SIMPLE_PAYLOADS.md` - Pre-made XSS payloads for testing
- Application logs in templates/ - HTML structure for understanding
- app.py - Backend implementation (understand vulnerability root causes)

---

## 🏁 Final Checklist

Before starting:
- [ ] Read entire case study
- [ ] Understand business context
- [ ] Review technical concepts
- [ ] Gather necessary tools
- [ ] Prepare for documentation
- [ ] Clear browser cache/cookies

During exploitation:
- [ ] Follow step-by-step guide
- [ ] Document each success
- [ ] Note variations that work/fail
- [ ] Screenshot key steps
- [ ] Extract flags

After completion:
- [ ] Submit all flags
- [ ] Review defense strategies
- [ ] Understand root causes
- [ ] Plan improvements
- [ ] Share learnings

---

## 💡 Pro Tips

1. **Burp Suite Intruder** is your best friend for fuzzing multiple payloads
2. **Browser DevTools Console** helps diagnose XSS payloads in real-time
3. **Capture the request** before crafting payloads - understand the structure
4. **Test in stages** - start simple, escalate complexity
5. **Automate repetitive tasks** - write scripts for blind/time-based attacks
6. **Read error messages** - they reveal database type, file system, etc.
7. **Take breaks** - fresh perspective helps when stuck

---

**You now have everything needed to complete all five labs. Good luck! 🚀**
