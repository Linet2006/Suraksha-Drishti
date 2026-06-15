import sys
import os
import json

# Fix for printing unicode characters on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure Python can find our package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.agents.salary_slip_agent.main import process_verification

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_real_photo.py <path_to_image>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Could not find image at {image_path}")
        sys.exit(1)
        
    print(f"\nProcessing actual photo: {image_path}")
    print("Running Image Forensics (ELA, EXIF, Paper Texture) and all DNA layers...\n")
    
    # We pass the image path and tell the orchestrator it's an image.
    # Note: For the prototype, Account Aggregator data is mocked as None here.
    result = process_verification(image_path, is_image=True)
    
    print("\n" + "="*60)
    
    # ANSI Colors for beautiful formatting
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    decision = result['routing']['decision']
    score = result['routing']['score']
    
    if "APPROVE" in decision:
        color = GREEN
    elif "REJECT" in decision:
        color = RED
    else:
        color = YELLOW
        
    print(f"{BOLD}{color}  FINAL DECISION: {decision} {RESET}")
    print(f"{BOLD}{color}  RISK SCORE:     {score} / 100 {RESET}")
    print("="*60 + "\n")
    
    issues = result['explainability']['issues']
    highlighted_path = result['explainability'].get('highlighted_image_path')
    
    if issues:
        print(f"{BOLD}🚨 ANOMALIES DETECTED:{RESET}")
        for issue in issues:
            # Highlight CRITICAL vetoes in red
            if "CRITICAL" in issue or "violation" in issue.lower() or "tampering" in issue.lower():
                print(f"  {RED}✖ {issue}{RESET}")
            else:
                print(f"  {YELLOW}⚠ {issue}{RESET}")
                
        if highlighted_path:
            print(f"\n  {BOLD}{CYAN}[✔] HIGHLIGHTED HEATMAP AUTO-GENERATED: {highlighted_path}{RESET}")
    else:
        print(f"{BOLD}{GREEN}✅ No Anomalies Found. Document is Clean.{RESET}")
        
    print(f"\n{BOLD}{CYAN}📊 LAYER BREAKDOWN:{RESET}")
    for layer, l_score in result['layer_breakdown'].items():
        layer_name = layer.replace('_', ' ').title()
        
        # Determine if this was truly skipped or just happened to score exactly 50
        # A truly skipped layer will have 50 points but NO issues attached to it.
        # Since we just have a flat list of issues, we can check specific layers that are known to skip.
        is_skipped = (l_score == 50 and layer in ["cross_verify", "typography"])
        
        if l_score == 0:
            print(f"  [{GREEN}PASS{RESET}] {layer_name}: 0 penalty points")
        elif l_score >= 100:
            print(f"  [{RED}VETO{RESET}] {layer_name}: {l_score} penalty points")
        elif is_skipped:
            print(f"  [{CYAN}SKIP{RESET}] {layer_name}: Neutral (Missing Data)")
        else:
            print(f"  [{YELLOW}WARN{RESET}] {layer_name}: {l_score} penalty points")
    print("\n")
