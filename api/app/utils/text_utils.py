import re
from typing import List, Dict, Any
from datetime import datetime

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\-\:\;\!\?\(\)\[\]\{\}]', '', text)
    
    return text.strip()

def extract_dates(text: str) -> List[str]:
    """Extract date patterns from text"""
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or MM/DD/YY
        r'\d{4}-\d{2}-\d{2}',        # YYYY-MM-DD
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'\d{1,2}\.\d{1,2}\.\d{2,4}' # MM.DD.YYYY
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        dates.extend(matches)
    
    return list(set(dates))  # Remove duplicates

def extract_amounts(text: str) -> List[str]:
    """Extract monetary amounts from text"""
    amount_patterns = [
        r'\$\d+\.?\d*',              # $123.45
        r'\d+\.?\d*\s*(?:USD|EUR|GBP)', # 123.45 USD
        r'\d+\.?\d*\s*(?:dollars?|euros?|pounds?)', # 123.45 dollars
    ]
    
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        amounts.extend(matches)
    
    return list(set(amounts))

def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def extract_phone_numbers(text: str) -> List[str]:
    """Extract phone numbers from text"""
    phone_patterns = [
        r'\+?1?\s*\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}',  # US format
        r'\+?[0-9]{1,4}[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,4}',  # International
    ]
    
    phones = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    
    return list(set(phones))

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity using word overlap"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def normalize_text_for_search(text: str) -> str:
    """Normalize text for better search results"""
    # Convert to lowercase
    text = text.lower()
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = text.split()
    filtered_words = [word for word in words if word not in stop_words]
    
    return ' '.join(filtered_words)

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract important keywords from text"""
    # Simple keyword extraction based on frequency
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Remove common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
    filtered_words = [word for word in words if word not in common_words and len(word) > 2]
    
    # Count frequency
    word_count = {}
    for word in filtered_words:
        word_count[word] = word_count.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]
