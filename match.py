import os
import re
import json
from rapidfuzz import fuzz, process

# ==================== CONFIGURATION ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MELBET_ROOT = os.path.join(BASE_DIR, "melbet")
MOSTBET_ROOT = os.path.join(BASE_DIR, "mostbet")
OUTPUT_FILE = os.path.join(BASE_DIR, "matched_data.txt")
MATCH_THRESHOLD = 85
MARKET_THRESHOLD = 85

# Term mappings for market matching
TERM_MAPPINGS = {
    'total 1': 'home team total',
    'total 2': 'away team total',
    'shots on target': 'shots on goal',
    'asian team total 1': 'asian home team total',
    'asian team total 2': 'asian away team total',
    'team 1': 'home team',
    'team 2': 'away team',
    '1x2': 'winner',
    'both teams to score runs': 'both teams to score points'
}

# ==================== MATCH NAME FUNCTIONS ====================
def normalize_match_name(name):
    name = re.sub(r'\d+', '', name)
    name = re.sub(r'[^a-zA-Z ]+', '', name)
    words = name.lower().split()
    words.sort()
    return ' '.join(words)

def get_folders(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

def match_folders(melbet_folders, mostbet_folders, threshold=MATCH_THRESHOLD):
    mapping = {}
    for melbet in melbet_folders:
        melbet_norm = normalize_match_name(melbet)
        best_match, score, _ = process.extractOne(
            melbet_norm, [normalize_match_name(m) for m in mostbet_folders], scorer=fuzz.ratio
        )
        if score >= threshold:
            idx = [normalize_match_name(m) for m in mostbet_folders].index(best_match)
            mapping[melbet] = mostbet_folders[idx]
    return mapping

# ==================== MARKET HEADING FUNCTIONS ====================
def normalize_market_name(name):
    name = os.path.splitext(name)[0]
    name = name.replace('_', ' ').replace('.', ' ')
    name = re.sub(r'\s+', ' ', name)
    return name.strip().lower()

def remove_extra_info(text):
    text = re.sub(r'\(incl\.\s*extra\s*innings\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(incl\s*ot\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'incl\s*extra\s*innings', '', text, flags=re.IGNORECASE)
    text = re.sub(r'incl\s*ot', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def apply_term_mappings(text):
    text_lower = text.lower()
    text_lower = remove_extra_info(text_lower)
    for melbet_term, mostbet_term in TERM_MAPPINGS.items():
        text_lower = re.sub(r'\b' + re.escape(melbet_term) + r'\b', mostbet_term, text_lower)
    return text_lower

def words_set(name):
    normalized = normalize_market_name(name)
    mapped = apply_term_mappings(normalized)
    return set(mapped.split())

def match_files_exact_only(melbet_files, mostbet_files):
    mapping = {}
    used_mostbet = set()
    for melbet in melbet_files:
        melbet_words = words_set(melbet)
        for idx, mostbet in enumerate(mostbet_files):
            if idx in used_mostbet:
                continue
            mostbet_words = words_set(mostbet)
            if melbet_words == mostbet_words:
                mapping[melbet] = mostbet
                used_mostbet.add(idx)
                break
    return mapping

# ==================== MAIN FUNCTION ====================
def main():
    print("="*80)
    print("STEP 1: MATCHING EVENTS AND MARKETS")
    print("="*80)
    
    # Step 1: Match folders
    melbet_matches = get_folders(MELBET_ROOT)
    mostbet_matches = get_folders(MOSTBET_ROOT)
    match_mapping = match_folders(melbet_matches, mostbet_matches)
    
    print(f"\nFound {len(match_mapping)} matching events")
    
    # Prepare data structure to save
    all_matches = []
    
    # Step 2: For each matched event, match markets
    for melbet_match, mostbet_match in match_mapping.items():
        print(f"\nProcessing: {melbet_match} <=> {mostbet_match}")
        
        melbet_path = os.path.join(MELBET_ROOT, melbet_match)
        mostbet_path = os.path.join(MOSTBET_ROOT, mostbet_match)
        
        # Get all txt files
        melbet_files = [f for f in os.listdir(melbet_path) if f.endswith('.txt')]
        mostbet_files = [f for f in os.listdir(mostbet_path) if f.endswith('.txt')]
        
        # Match market files
        file_mapping = match_files_exact_only(melbet_files, mostbet_files)
        
        print(f"  Found {len(file_mapping)} matching markets")
        
        # Save match data
        match_data = {
            'melbet_event': melbet_match,
            'mostbet_event': mostbet_match,
            'markets': []
        }
        
        for melbet_file, mostbet_file in file_mapping.items():
            market_data = {
                'melbet_file': melbet_file,
                'mostbet_file': mostbet_file,
                'melbet_path': os.path.join(melbet_path, melbet_file),
                'mostbet_path': os.path.join(mostbet_path, mostbet_file)
            }
            match_data['markets'].append(market_data)
        
        all_matches.append(match_data)
    
    # Save to file (always in Ace folder)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Matching complete! Data saved to: {OUTPUT_FILE}")
    print(f"Total events matched: {len(all_matches)}")
    total_markets = sum(len(m['markets']) for m in all_matches)
    print(f"Total markets matched: {total_markets}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()