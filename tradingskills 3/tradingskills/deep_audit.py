import os
import re

files = ['agent.md', 'skill.md', 'soul.md']
print("Starting Deep Structural Audit (Phase 2)...\n")

issues_found = 0

def check_rule(file_content, filename, pattern, rule_name, expected_context):
    global issues_found
    matches = re.finditer(pattern, file_content, re.IGNORECASE)
    found = False
    for match in matches:
        found = True
        start = max(0, match.start() - 100)
        end = min(len(file_content), match.end() + 100)
        context = file_content[start:end]
        if expected_context not in context.lower():
            print(f"[!] STRUCTURAL FLAW IN {filename}: '{rule_name}' mentioned without strict quantitative limit.")
            print(f"    Context: ...{context.strip()}...\n")
            issues_found += 1
            
for f in files:
    if os.path.exists(f):
        with open(f, 'r') as file:
            content = file.read()
            # Check 1: DEX TVL Caps
            if 'dex' in content.lower() or 'pool' in content.lower():
                check_rule(content, f, r'(tvl|pool size|liquidity pool)', 'DEX TVL Capacity Limits', '1%')
                
            # Check 2: Funding Rate Hard Stop
            if 'funding' in content.lower():
                check_rule(content, f, r'(funding bleed|accumulated funding)', 'Funding Carry Hard Stop', '0.5r')
                
            # Check 3: Cross Margin Stress Test
            if 'cross margin' in content.lower() or 'cross' in content.lower():
                check_rule(content, f, r'(cross margin)', 'Cross Margin Correlation=1 Stress', 'correlation=1')

if issues_found == 0:
    print("No structural flaws found in this pass.")
else:
    print(f"Total Flaws Found: {issues_found}. Applying fixes required.")
