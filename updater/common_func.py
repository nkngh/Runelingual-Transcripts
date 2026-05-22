import os
import shutil

"""
edit below to add/remove languages
"""
# must mach lang code in LangCodeSelectableList.java
LANG = ['pt_br', 'no', 'es_ag', 'ja', 'ru', 'tr', 'zh', 'hu'] # add language codes here to add new language, then use update_nonEn_transcripts.py (and update_char_images.py if its non alphabet characters)
LANG_CODE_STANDARD = ['pt-BR', 'no', 'es-AR', 'ja', 'ru', 'tr', 'zh-CN', 'hu'] #  language codes follow the ISO 639 standard
# files not to list on hash file
EXTENSION_IGNORE = ['.xlsx', '.xliff']

"""
dont edit anything else below (unless you know what youre doing)
"""

current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
DRAFT_DIR = os.path.join(parent_dir, 'draft')
PUBLIC_DIR = os.path.join(parent_dir, 'public')
TRANSCRIPT_PATH = os.path.join(current_dir, 'transcript.db')

import shutil
from datetime import datetime
import os

def create_backup(file_path):
    """
    Creates a backup of a file in a 'backup' folder within the same directory as the original file.
    The backup file is named with the original filename and the datetime of the backup.
    
    Args:
    - file_path (str): The path to the file to back up.
    """
    # Extract directory and filename from the file_path
    directory, filename = os.path.split(file_path)
    file_name_no_ext, file_extension = os.path.splitext(filename)

    # Create a 'backup' folder if it doesn't exist
    backup_dir = os.path.join(directory, 'backup')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Format the current datetime to append to the backup filename
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"{file_name_no_ext}_{datetime_str}{file_extension}"
    
    # Construct the backup file path
    backup_file_path = os.path.join(backup_dir, backup_filename)
    
    # Copy the original file to the backup location
    shutil.copy(file_path, backup_file_path)
    print(f"Backup created at: {backup_file_path}")

def get_target_language():
    """
    This function prompts the user to select a target language from a list of languages.

    It first prints a list of languages with corresponding numbers. Then, it asks the user to enter
    a number corresponding to the language they wish to update/create transcript files for. It returns
    the selected language.

    Args:
        LANG (list): A list of languages.

    Returns:
        target_language (str): The selected target language, declared in common_func.py.
    """
    while True:
        print("Enter a number:")
        print("0 for every languages")
        for i, lang in enumerate(LANG):
            print(f"{i+1} for {lang}")
        target_language_num = input("to choose the target language: ")
        if target_language_num.isdigit() and int(target_language_num) < len(LANG) + 1 and int(target_language_num) > -1:
            if int(target_language_num) == 0:
                return 0
            else:
                target_language = LANG[int(target_language_num)-1]
                return target_language
        else:
            print("Invalid input. Please enter a valid number.")


def remove_existing_dir(directory_path, folder_name):
    # Construct the path to the folder
    folder_path = os.path.join(directory_path, folder_name)
    
    # Check if the folder exists
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Use shutil.rmtree to recursively delete the folder
        shutil.rmtree(folder_path)
        print(f"The folder '{folder_name}' has been deleted.")
    else:
        print(f"The folder '{folder_name}' does not exist.")

def create_directories_if_not_exist(output_dir_base):
    # Split the directory path into individual directories
    directories = output_dir_base.split("/")
    
    # Construct the full path gradually
    current_path = ""
    for directory in directories:
        current_path = os.path.join(current_path, directory)
        
        # Check if the directory exists
        if not os.path.exists(current_path):
            # Create the directory if it doesn't exist
            os.makedirs(current_path)
            print(f"Created directory: {current_path}")
        else:
            print(f"Directory already exists: {current_path}")

def get_list_files_in_directory(target_path:str) -> list:
    entries = os.listdir(target_path)
    files = [entry for entry in entries if os.path.isfile(os.path.join(target_path,entry))]
    return files

def is_file_empty(file_path):
    """Check if a file is empty."""
    return os.path.exists(file_path) and os.path.getsize(file_path) == 0