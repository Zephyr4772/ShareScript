import os
import json
import zipfile
import tempfile

def create_zip_package(context: dict, visuals: dict, social_posts: dict, readme_content: str) -> dict:
    """
    Takes all generated content and zips it up into a temporary directory.
    Returns the path to the ZIP file.
    """
    out_dir = tempfile.mkdtemp(prefix="shipscript_zip_")
    repo_name = context.get('name', 'project').replace('/', '_')
    zip_path = os.path.join(out_dir, f"{repo_name}_launch_kit.zip")
    
    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Write social posts
            if social_posts:
                for platform, content in social_posts.items():
                    if isinstance(content, str):
                        zipf.writestr(f"social_posts/{platform}.txt", content)
                    else:
                        zipf.writestr(f"social_posts/{platform}.json", json.dumps(content, indent=2))
                        
            # Write README
            if readme_content:
                zipf.writestr("README_improved.md", readme_content)
                
            # Add visual files
            if visuals:
                for key, filepath in visuals.items():
                    if filepath and isinstance(filepath, str) and os.path.exists(filepath):
                        filename = os.path.basename(filepath)
                        zipf.write(filepath, arcname=f"visuals/{filename}")
                        
        return {"status": "success", "zip_path": zip_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}
