import os
import shutil


def clear_folders():
    """
    Clears all contents of the 'downloads' and 'merged_properties' folders
    that are in the parent directory of this script.
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get parent directory (one level up)
    parent_dir = os.path.dirname(script_dir)
    
    # Define the paths to the folders in the parent directory
    downloads_path = os.path.join(parent_dir, 'downloads')
    merged_properties_path = os.path.join(parent_dir, 'merged_properties')
    
    folders_to_clear = [downloads_path, merged_properties_path]
    
    for folder_path in folders_to_clear:
        if os.path.exists(folder_path):
            # Check if it's a directory
            if os.path.isdir(folder_path):
                print(f"Clearing contents of {folder_path}...")
                
                # List all files and directories in the folder
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    
                    try:
                        if os.path.isfile(item_path):
                            # Remove file
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            # Remove directory and all its contents
                            shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"Error while deleting {item_path}: {e}")
                
                print(f"Finished clearing {folder_path}")
            else:
                print(f"Warning: {folder_path} exists but is not a directory")
        else:
            print(f"Warning: {folder_path} does not exist")


# Example usage - uncomment to run the function when script is executed directly
if __name__ == "__main__":
    clear_folders()