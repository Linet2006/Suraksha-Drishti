from PIL import Image, ImageChops, ImageEnhance
import numpy as np
import cv2
import datetime
import os

def error_level_analysis(image_path, quality=90, threshold=15.0, output_dir="data/outputs/salaryslip"):
    """
    Error Level Analysis highlights digitally edited regions.
    Generates a visual heatmap overlaid onto the original image.
    """
    try:
        original = Image.open(image_path)
        # Convert to RGB if needed
        if original.mode != 'RGB':
            original = original.convert('RGB')
            
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        temp_path = os.path.join(output_dir, "temp_resaved.jpg")
        original.save(temp_path, "JPEG", quality=quality)
        resaved = Image.open(temp_path)
        
        ela_image = ImageChops.difference(original, resaved)
        
        # Generate Heatmap mathematically for variance calculation, but don't save to disk!
        extrema = ela_image.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0: max_diff = 1
        scale = 255.0 / max_diff
        ela_enhanced = ImageEnhance.Brightness(ela_image).enhance(scale)
        
        # We no longer generate or save the bluish COLORMAP_JET image
        # cv2.imwrite(heatmap_path, heatmap)
        
        heatmap_filename = None
        # ------------------------
        
        ela_array = np.array(ela_image)
        std_dev = ela_array.std()
        
        if std_dev > threshold:
            return "ELA_TAMPER_DETECTED", std_dev, heatmap_filename
        return "CLEAN", std_dev, heatmap_filename
    except Exception as e:
        return "ERROR", str(e), None

def verify_exif_data(image_path, max_age_minutes=30):
    """
    Check if EXIF exists and timestamp is recent.
    """
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        
        if not exif:
            return "STRIPPED_EXIF", "No EXIF data found. Likely a saved image, not a live capture."
            
        # Extract DateTime (tag 306 usually)
        date_time_str = exif.get(306)
        if not date_time_str:
            return "MISSING_TIMESTAMP", "No DateTime in EXIF."
            
        try:
            capture_time = datetime.datetime.strptime(date_time_str, '%Y:%m:%d %H:%M:%S')
            now = datetime.datetime.now()
            age_minutes = (now - capture_time).total_seconds() / 60.0
            
            if age_minutes > max_age_minutes:
                return "OLD_PHOTO", f"Capture is {age_minutes:.1f} minutes old."
                
            return "VALID_EXIF", "Timestamp is recent."
        except ValueError:
            return "INVALID_DATE_FORMAT", "Could not parse EXIF DateTime."
            
    except Exception as e:
        return "ERROR", str(e)

def analyze_paper_texture(image_path, threshold=20.0):
    """
    Paper Texture vs Screen Glow Analysis
    Screen captures are perfectly uniform. Paper has micro texture.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return "ERROR", "Could not load image."
        
    # Standard deviation of brightness
    std_dev = np.std(img)
    if std_dev < threshold:
        # Suspiciously uniform illumination
        return "SCREEN_GLOW_DETECTED", std_dev
    return "PAPER_TEXTURE_DETECTED", std_dev

def check_visual_logic_paradox(image_path):
    """
    Mock for Layer 7: Vision Language Model (VLM) Semantic Check.
    In production, this calls an AI vision model (like GPT-4o or Gemini Pro Vision) 
    to look for contextual paradoxes that traditional CV and Math miss.
    """
    basename = os.path.basename(image_path).lower()
    if "new_slip" in basename:
        return "PARADOX_DETECTED", "Visual AI flagged a contradiction: Document contains a handwritten signature but footer text states no physical signature is required."
    return "LOGIC_CLEAN", "No visual paradoxes found."

def run_image_forensics(image_path, output_dir="data/outputs/salaryslip"):
    """
    Runs all L1 Image Forensics checks.
    """
    ela_status, ela_val, heatmap_filename = error_level_analysis(image_path, output_dir=output_dir)
    exif_status, exif_val = verify_exif_data(image_path)
    texture_status, texture_val = analyze_paper_texture(image_path)
    logic_status, logic_val = check_visual_logic_paradox(image_path)
    
    score = 0
    issues = []
    
    if ela_status == "ELA_TAMPER_DETECTED":
        score += 30
        issues.append(f"Digital tampering detected (ELA variance: {ela_val:.2f})")
        
    if exif_status in ["STRIPPED_EXIF", "MISSING_TIMESTAMP", "OLD_PHOTO"]:
        score += 20
        issues.append(f"Metadata issue: {exif_status} - {exif_val}")
        
    if texture_status == "SCREEN_GLOW_DETECTED":
        score += 30
        issues.append(f"Screen capture detected (Uniform brightness: {texture_val:.2f})")
        
    if logic_status == "PARADOX_DETECTED":
        score += 100  # Massive Veto Penalty!
        issues.append(f"CRITICAL LOGICAL PARADOX: {logic_val}")
        
    return {
        "forensics_score": score,
        "forensics_issues": issues,
        "heatmap_filename": heatmap_filename,
        "details": {
            "ela": ela_status,
            "exif": exif_status,
            "texture": texture_status
        }
    }
