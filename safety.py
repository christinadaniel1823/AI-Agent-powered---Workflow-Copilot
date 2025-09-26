import re

def contains_phi(text):
    patterns = [r'\b\d{3}-\d{2}-\d{4}\b', r'\b\d{10}\b', r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b']
    return any(re.search(p, text) for p in patterns) or "patient" in text.lower()

def deidentify(text):
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', "XXX-XX-XXXX", text)
    text = re.sub(r'\b\d{10}\b', "XXXXXXXXXX", text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', "email@example.com", text)
    return text
