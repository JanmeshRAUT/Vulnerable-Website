import os
import glob
import re

html_files = glob.glob(r'e:\AS LAb\vulnerable_ecommerce\templates\lab2\sub*_menu.html')

template = """{% extends 'base.html' %}
{% block title %}MOD_TITLE{% endblock %}

{% block content %}
<div class="lab-index-container">
    <div class="lab-header-premium" style="padding: 2rem; margin-bottom: 2rem;">
        <a href="{{ url_for('lab2') }}" class="back-link-premium">&larr; Back to Module 2</a>
        <div class="lab-title-wrapper" style="margin-top: 1.5rem;">
            <h1 class="lab-main-title">Lab Variation Selection</h1>
            <h2 class="lab-sub-title" style="font-size: 2.5rem;">H2_HEADING</h2>
        </div>
    </div>

    <!-- Alert Banner -->
    <div class="lab-alert-banner" style="margin-bottom: 2rem;">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            BANNER_TEXT
        </div>
    </div>

    <!-- Lab Grid -->
    <div class="premium-lab-grid">
CARD_BLOCKS
    </div>
</div>

<style>
/* Specific Styles for Lab Index Pages to make them look Premium */
.lab-index-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.lab-header-premium {
    text-align: center;
    margin-bottom: 3rem;
    padding: 3rem;
    background: radial-gradient(circle at top, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.4) 100%);
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    position: relative;
    overflow: hidden;
}

.lab-header-premium::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at center, rgba(139, 92, 246, 0.05) 0%, transparent 40%);
    pointer-events: none;
}

.back-link-premium {
    position: absolute;
    top: 2rem;
    left: 2rem;
    color: #94a3b8;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.3s ease;
    background: rgba(255, 255, 255, 0.05);
    padding: 0.5rem 1rem;
    border-radius: 99px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.back-link-premium:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
    transform: translateX(-3px);
}

.lab-main-title {
    font-size: 1.25rem;
    color: #8b5cf6;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 800;
    margin-bottom: 0.5rem;
}

.lab-sub-title {
    font-size: 3.5rem;
    font-weight: 900;
    color: white;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #ffffff, #c4b5fd);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.lab-alert-banner {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 1.5rem 2rem;
    border-radius: 16px;
    margin-bottom: 3.5rem;
    box-shadow: 0 10px 25px rgba(245, 158, 11, 0.1);
}

.alert-icon {
    font-size: 2rem;
    filter: drop-shadow(0 0 10px rgba(245, 158, 11, 0.5));
}

.alert-content {
    color: #fcd34d;
    font-size: 1.05rem;
    line-height: 1.5;
}

.premium-lab-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 2rem;
    padding-bottom: 4rem;
}

.premium-lab-card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    text-decoration: none;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
}

.premium-lab-card:hover {
    transform: translateY(-10px);
    background: rgba(30, 41, 59, 0.9);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.premium-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.5rem;
}

.premium-card-icon {
    width: 60px;
    height: 60px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    transition: transform 0.3s ease;
    background: rgba(6, 182, 212, 0.1); 
    color: #06b6d4; 
    border: 1px solid rgba(6, 182, 212, 0.2);
}

.premium-lab-card:nth-child(2) .premium-card-icon {
    background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2);
}

.premium-lab-card:nth-child(3) .premium-card-icon {
    background: rgba(236, 72, 153, 0.1); color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.2);
}

.premium-lab-card:hover .premium-card-icon {
    transform: scale(1.1) rotate(-5deg);
}

.premium-card-body h3 {
    font-size: 1.35rem;
    font-weight: 800;
    color: white;
    margin-bottom: 0.75rem;
    line-height: 1.3;
}

.premium-card-body p {
    color: #94a3b8;
    font-size: 0.95rem;
    line-height: 1.6;
    margin-bottom: 2rem;
}

.premium-card-footer {
    margin-top: auto;
    display: flex;
    align-items: center;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.premium-card-action {
    color: #06b6d4;
    font-weight: 700;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.3s ease;
}

.premium-lab-card:nth-child(2) .premium-card-action { color: #8b5cf6; }
.premium-lab-card:nth-child(3) .premium-card-action { color: #ec4899; }

.premium-lab-card:hover .premium-card-action {
    gap: 1rem;
}
</style>
{% endblock %}
"""

for filepath in html_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title
    title_match = re.search(r'{% block title %}(.*?){% endblock %}', content)
    mod_title = title_match.group(1) if title_match else 'Lab Variation Selection'
    
    # Extract h2
    h2_match = re.search(r'<h2.*?>(.*?)</h2>', content)
    h2_heading = h2_match.group(1) if h2_match else mod_title
    
    # Extract banner
    banner_match = re.search(r'<div class="banner">(.*?)</div>', content, re.DOTALL)
    banner_text = banner_match.group(1).strip() if banner_match else 'Select a variation to proceed.'
    
    # Extract cards
    cards_str = ""
    cards = re.finditer(r'<div class="card">(.*?)</div>\s*(?=<div class="card">|</div>\s*{% endblock %})', content, re.DOTALL)
    
    card_idx = 0
    colors = ["#06b6d4", "#8b5cf6", "#ec4899"]
    
    for match in cards:
        card_content = match.group(1)
        # Extract icon
        icon_match = re.search(r'<div class="variation-preview.*?>(.*?)</div>', card_content)
        icon = icon_match.group(1) if icon_match else '⚙️'
        
        # Extract h3
        h3_match = re.search(r'<h3>(.*?)</h3>', card_content)
        h3 = h3_match.group(1) if h3_match else 'Variation'
        
        # Extract p
        p_match = re.search(r'<p.*?>(.*?)</p>', card_content)
        p = p_match.group(1) if p_match else ''
        
        # Extract link
        a_match = re.search(r'<a href="(.*?)".*?>(.*?)</a>', card_content)
        href = a_match.group(1) if a_match else '#'
        btn_text = a_match.group(2) if a_match else 'Start Variation'
        
        cards_str += f"""
        <a href="{href}" class="premium-lab-card">
            <div class="premium-card-header">
                <div class="premium-card-icon">{icon}</div>
            </div>
            <div class="premium-card-body">
                <h3>{h3}</h3>
                <p>{p}</p>
            </div>
            <div class="premium-card-footer">
                <span class="premium-card-action">{btn_text} &rarr;</span>
            </div>
        </a>"""
        card_idx += 1
        
    new_content = template.replace('MOD_TITLE', mod_title).replace('H2_HEADING', h2_heading).replace('BANNER_TEXT', banner_text).replace('CARD_BLOCKS', cards_str)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Updated {filepath}")
