"""
Anki Audio Enabler

This script connects to Anki via the AnkiConnect API to find all cards in the
"Polish" deck that use the "Word" template from the "Words" model. It retrieves
these cards and processes them to create a categorised list of words based on
their tags, which is then saved to a text file.

Requirements:
- Anki must be running
- AnkiConnect addon must be installed in Anki
- The deck "Polish" must exist with "Words" model containing "Word" template
"""

import requests
from typing import List, Dict, Any, Optional
from tqdm import tqdm

import logging

logger = logging.getLogger(__name__)

ANKI_CONNECT_URL = "http://localhost:8765"

def invoke(action: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Send a request to AnkiConnect API."""
    try:
        logger.debug(f"Invoking AnkiConnect action: {action} with params: {params}")
        response = requests.post(ANKI_CONNECT_URL, json={
            "action": action,
            "version": 6,
            "params": params or {}
        })
        response.raise_for_status()
        result = response.json()
        
        if result.get("error"):
            logger.error(f"AnkiConnect action '{action}' failed: {result['error']}")
            raise RuntimeError(f"AnkiConnect error: {result['error']}")
            
        logger.debug(f"AnkiConnect action '{action}' completed successfully")
        return result["result"]
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to AnkiConnect - check if Anki is running with AnkiConnect addon")
        raise ConnectionError("Could not connect to AnkiConnect. Is Anki running with AnkiConnect addon installed?")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to AnkiConnect failed: {e}")
        raise RuntimeError(f"Request failed: {e}")

def find_notes(deck_name: str) -> List[int]:
    """Find all note IDs in the specified deck."""
    logger.debug(f"Searching for notes in deck: {deck_name}")
    return invoke("findNotes", {"query": f'deck:"{deck_name}"'})

def get_note_info(note_ids: List[int]) -> List[Dict[str, Any]]:
    """Get detailed information for the specified notes."""
    logger.debug(f"Retrieving info for {len(note_ids)} notes")
    return invoke("notesInfo", {"notes": note_ids})

def get_model_templates(model_name: str) -> Dict[str, str]:
    """Get template names and content for a given model."""
    logger.debug(f"Retrieving templates for model: {model_name}")
    return invoke("modelTemplates", {"modelName": model_name})

def get_words() -> List[Dict[str, Any]]:
    """
    Main function that enables audio for qualifying cards.
    
    Returns a list of notes from the Polish deck using the "Words" model.
    """
    try:
        logger.info("Starting audio enablement process for Polish deck")
        
        # Get the template information for the "Words" model
        logger.debug("Retrieving template information for 'Words' model")
        templates_dict = get_model_templates("Words")
        template_names = list(templates_dict.keys())
        logger.debug(f"Found templates: {template_names}")

        # Get the order of the "Word" template in the templates list
        if "Word" not in template_names:
            logger.warning("'Word' template not found in the 'Words' model")
            return
            
        word_template_ord = template_names.index("Word")
        logger.debug(f"'Word' template order: {word_template_ord}")

        # Get all notes in the Polish deck
        logger.info("Searching for notes in Polish deck")
        note_ids = find_notes("Polish")
        if not note_ids:
            logger.warning("No notes found in Polish deck")
            return
            
        logger.info(f"Found {len(note_ids)} notes in Polish deck")
        notes = get_note_info(note_ids)

        # Get the notes with the model name "Words"
        logger.debug("Filtering notes by 'Words' model")
        notes = [note for note in notes if note["modelName"] == "Words"]
        if not notes:
            logger.warning("No notes found with 'Words' model in Polish deck")
            return

        logger.info(f"Found {len(notes)} notes with 'Words' model")

        return notes
            
    except Exception as e:
        logger.error(f"Error during audio enablement process: {e}", exc_info=True)

def process_and_store(words: List[Dict[str, Any]]) -> None:
    """Process the words and store them in a text file categorized by tags."""
    tag_dict = {"all": [], "no-tag": []}
    for word in words:
        tag_dict["all"].append(word["fields"]["Word"]["value"])
        if not word["tags"]:
            tag_dict["no-tag"].append(word["fields"]["Word"]["value"])
            continue

        for tag in word["tags"]:
            if tag not in tag_dict:
                tag_dict[tag] = []
            tag_dict[tag].append(word["fields"]["Word"]["value"])

    # Sort the words alphabetically
    tag_dict = {tag: sorted(words) for tag, words in tag_dict.items()}

    # Store the words in a text file
    with open("words.txt", "w", encoding="utf-8") as f:
        for tag, words in tag_dict.items():
            f.write(f"{tag}:\n")
            first = True
            for word in words:
                if not first:
                    f.write(", ")
                f.write(f"{word}")
                first = False

            f.write("\n\n")

if __name__ == "__main__":
    # Configure logging with more detailed format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # To enable debug logging, uncomment the line below:
    # logger.setLevel(logging.DEBUG)
    
    logger.info("=== Starting Anki Fetch ===")
    words: list[Dict[str, Any]] = get_words()
    logger.info("=== End of Anki Fetch ===")

    if not words:
        logger.warning("No words were retrieved from Anki.")
        exit(0)

    process_and_store(words)