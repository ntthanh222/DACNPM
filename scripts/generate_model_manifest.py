import os
import glob
import hashlib
import json
import datetime

def main():
    # Since this file is in scripts/generate_model_manifest.py, its parent is scripts, and parent.parent is project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(project_root, "rasa", "models")
    
    # Find all tar.gz files
    pattern = os.path.join(models_dir, "*.tar.gz")
    files = glob.glob(pattern)
    if not files:
        print("[ERROR] No models found in rasa/models")
        return False
        
    # Get the newest file
    newest_file = max(files, key=os.path.getmtime)
    filename = os.path.basename(newest_file)
    
    # Calculate SHA-256
    sha256_hash = hashlib.sha256()
    with open(newest_file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    sha256 = sha256_hash.hexdigest()
    
    # Stats
    trained_at = datetime.datetime.fromtimestamp(os.path.getmtime(newest_file)).isoformat()
    
    manifest = {
        "filename": filename,
        "sha256": sha256,
        "trained_at": trained_at,
        "config_hash": "N/A",
        "training_data_hash": "N/A"
    }
    
    manifest_path = os.path.join(models_dir, "current-model.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[OK] Generated manifest at {manifest_path} for model {filename} with hash {sha256}")
    return True

if __name__ == "__main__":
    main()
