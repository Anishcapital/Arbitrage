import os
import re
import json

# ==================== CONFIGURATION ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "matched_data.txt")

# Arbitrage configurations
TWO_WAY_PAIRS = [("w1", "w2"), ("yes", "no"), ("1", "2"), ("home", "away")]
THREE_WAY_SETS = [("w1", "x", "w2"), ("1x", "12", "2x")]
NORM_MAP = {
    "w1": "w1", "1": "w1", "home": "w1",
    "w2": "w2", "2": "w2", "away": "w2",
    "x": "x", "draw": "x",
    "yes": "yes", "no": "no",
    "1x": "1x", "12": "12", "2x": "2x"
}

# ==================== PARSING FUNCTIONS ====================
def normalize_outcome(outcome):
    outcome = outcome.lower().replace("-", "").replace(" ", "")
    return NORM_MAP.get(outcome, outcome)

def parse_file(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines) - 1:
        outcome = lines[i]
        try:
            odd = float(lines[i+1].replace(',', '.'))
            norm = normalize_outcome(outcome)
            data[norm] = {
                'original': outcome,
                'odd': odd,
                'file': os.path.basename(filepath)
            }
            i += 2
        except Exception:
            i += 1
    return data

def parse_handicap_file(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines) - 1:
        outcome = lines[i]
        try:
            odd = float(lines[i+1].replace(',', '.'))
            outcome_norm = outcome.lower().replace('handicap', '').strip()
            outcome_norm = outcome_norm.replace('[', '(').replace(']', ')')
            outcome_norm = re.sub(r'\s+', ' ', outcome_norm)
            data[outcome_norm] = {
                'original': outcome,
                'odd': odd,
                'file': os.path.basename(filepath)
            }
            i += 2
        except Exception:
            i += 1
    return data

def parse_total_file(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines) - 1:
        outcome = lines[i]
        try:
            odd = float(lines[i+1].replace(',', '.'))
            outcome_lower = outcome.lower()
            outcome_lower = outcome_lower.replace('total', '').replace('(', ' ').replace(')', ' ')
            outcome_lower = re.sub(r'\s+', ' ', outcome_lower).strip()
            match = re.search(r'(over|under)\s*([0-9]+\.?[0-9]*)', outcome_lower)
            if match:
                norm = (match.group(1), float(match.group(2)))
            else:
                match = re.search(r'([0-9]+\.?[0-9]*)\s*(over|under)', outcome_lower)
                if match:
                    norm = (match.group(2), float(match.group(1)))
                else:
                    norm = None
            if norm:
                data[norm] = {
                    'original': outcome,
                    'odd': odd,
                    'file': os.path.basename(filepath)
                }
            i += 2
        except Exception:
            i += 1
    return data

# ==================== ARBITRAGE CALCULATORS ====================
def arbitrage_calc_2way(odd1, odd2):
    return ((1 / ((1/odd1) + (1/odd2))) - 1) * 100

def arbitrage_calc_3way(odd1, odd2, odd3):
    return ((1 / ((1/odd1) + (1/odd2) + (1/odd3))) - 1) * 100

def detect_market_type(filename):
    filename_lower = filename.lower()
    if 'handicap' in filename_lower:
        return 'handicap'
    elif 'total' in filename_lower:
        return 'total'
    elif any(term in filename_lower for term in ['1x2', 'winner', 'double chance']):
        return '3way'
    else:
        return '2way'

def calculate_arbitrage(melbet_path, mostbet_path, market_type):
    results = []
    
    if market_type == 'handicap':
        data1 = parse_handicap_file(melbet_path)
        data2 = parse_handicap_file(mostbet_path)
        pattern = re.compile(r'(\d)\s*\(([+-]?\d+\.?\d*)\)')
        
        for key1, info1 in data1.items():
            m1 = pattern.search(key1)
            if not m1:
                continue
            team1, hcap1 = m1.group(1), float(m1.group(2))
            for key2, info2 in data2.items():
                m2 = pattern.search(key2)
                if not m2:
                    continue
                team2, hcap2 = m2.group(1), float(m2.group(2))
                if team1 != team2 and abs(hcap1 + hcap2) < 0.01:
                    arb = arbitrage_calc_2way(info1['odd'], info2['odd'])
                    if arb > -100:
                        results.append(f"Handicap: {info1['original']} ({info1['odd']}) + {info2['original']} ({info2['odd']}) = {arb:.2f}%")
    
    elif market_type == 'total':
        data1 = parse_total_file(melbet_path)
        data2 = parse_total_file(mostbet_path)
        
        for (ou1, val1), info1 in data1.items():
            ou2 = 'under' if ou1 == 'over' else 'over'
            key2 = (ou2, val1)
            if key2 in data2:
                info2 = data2[key2]
                arb = arbitrage_calc_2way(info1['odd'], info2['odd'])
                if arb > -100:
                    results.append(f"Total: {info1['original']} ({info1['odd']}) + {info2['original']} ({info2['odd']}) = {arb:.2f}%")
    
    elif market_type == '3way':
        data1 = parse_file(melbet_path)
        data2 = parse_file(mostbet_path)
        
        for triple in THREE_WAY_SETS:
            out1, out2, out3 = triple
            combos = [(data1, data2, data2), (data1, data1, data2), (data2, data1, data1),
                      (data2, data2, data1), (data2, data1, data2), (data1, data2, data1)]
            for idx, (dA, dB, dC) in enumerate(combos):
                if out1 in dA and out2 in dB and out3 in dC:
                    info1 = dA[out1]
                    info2 = dB[out2]
                    info3 = dC[out3]
                    arb = arbitrage_calc_3way(info1['odd'], info2['odd'], info3['odd'])
                    if arb > -100:
                        results.append(f"3-Way: {info1['original']} ({info1['odd']}) + {info2['original']} ({info2['odd']}) + {info3['original']} ({info3['odd']}) = {arb:.2f}%")
    
    else:  # 2way
        data1 = parse_file(melbet_path)
        data2 = parse_file(mostbet_path)
        
        for pair in TWO_WAY_PAIRS:
            out1, out2 = pair
            if out1 in data1 and out2 in data2:
                info1 = data1[out1]
                info2 = data2[out2]
                arb = arbitrage_calc_2way(info1['odd'], info2['odd'])
                if arb > -100:
                    results.append(f"2-Way: {info1['original']} ({info1['odd']}) + {info2['original']} ({info2['odd']}) = {arb:.2f}%")
            if out2 in data1 and out1 in data2:
                info1 = data1[out2]
                info2 = data2[out1]
                arb = arbitrage_calc_2way(info1['odd'], info2['odd'])
                if arb > -100:
                    results.append(f"2-Way: {info1['original']} ({info1['odd']}) + {info2['original']} ({info2['odd']}) = {arb:.2f}%")
    
    return results

# ==================== MAIN FUNCTION ====================
def main():
    print("="*80)
    print("STEP 2: CALCULATING ARBITRAGE FROM MATCHED DATA")
    print("="*80)
    
    # Load matched data (always from Ace folder)
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        all_matches = json.load(f)
    
    print(f"\nLoaded {len(all_matches)} matched events")
    
    total_arbitrage_found = 0
    
    # Process each matched event
    for match_data in all_matches:
        melbet_event = match_data['melbet_event']
        mostbet_event = match_data['mostbet_event']
        
        print(f"\n{'='*60}")
        print(f"Event: {melbet_event} <=> {mostbet_event}")
        print(f"{'='*60}")
        
        event_arbitrage_found = False
        
        # Process each matched market
        for market in match_data['markets']:
            melbet_file = market['melbet_file']
            mostbet_file = market['mostbet_file']
            melbet_path = market['melbet_path']
            mostbet_path = market['mostbet_path']
            
            # Detect market type
            market_type = detect_market_type(melbet_file)
            
            print(f"\nMarket: {melbet_file} <=> {mostbet_file} (Type: {market_type})")
            
            # Calculate arbitrage
            results = calculate_arbitrage(melbet_path, mostbet_path, market_type)
            
            if results:
                event_arbitrage_found = True
                for result in results:
                    print(f"  {result}")
                    if "=" in result and float(result.split("=")[-1].strip().replace("%", "")) > 0:
                        total_arbitrage_found += 1
            else:
                print("  No arbitrage opportunities found")
        
        if not event_arbitrage_found:
            print("\nNo arbitrage found for this event")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"Total positive arbitrage opportunities found: {total_arbitrage_found}")
    print(f"{'='*80}")

if __name__ == "__main__":
    # Save all print output to Output.txt as well as console
    import sys

    class Logger(object):
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "w", encoding="utf-8")

        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)

        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = Logger("Output.txt")
    main()
    sys.stdout.log.close()