"""
Anki Audio Enabler

This script connects to Anki via the AnkiConnect API to find all cards in the
"Polish" deck that use the "Fill Blank" template from the "Custom Cloze" model. It retrieves
these cards which is then saved to a text file.

Requirements:
- Anki must be running
- AnkiConnect addon must be installed in Anki
- The deck "Polish" must exist with "Custom Cloze" model containing "Fill Blank" template
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

def get_sentences() -> List[Dict[str, Any]]:
    """
    Main function that enables audio for qualifying cards.
    
    Returns a list of notes from the Polish deck using the "Sentences" model.
    """
    try:
        logger.info("Starting audio enablement process for Polish deck")
        
        # Get the template information for the "Sentences" model
        logger.debug("Retrieving template information for 'Custom Cloze' model")
        templates_dict = get_model_templates("Custom Cloze")
        template_names = list(templates_dict.keys())
        logger.debug(f"Found templates: {template_names}")

        # Get the order of the "Fill Blank" template in the templates list
        if "Fill Blank" not in template_names:
            logger.warning("'Fill Blank' template not found in the 'Sentences' model")
            return
            
        word_template_ord = template_names.index("Fill Blank")
        logger.debug(f"'Fill Blank' template order: {word_template_ord}")
        # Get all notes in the Polish deck
        logger.info("Searching for notes in Polish deck")
        note_ids = find_notes("Polish")
        if not note_ids:
            logger.warning("No notes found in Polish deck")
            return
            
        logger.info(f"Found {len(note_ids)} notes in Polish deck")
        notes = get_note_info(note_ids)

        # Get the notes with the model name "Custom Cloze"
        logger.debug("Filtering notes by 'Custom Cloze' model")
        notes = [note for note in notes if note["modelName"] == "Custom Cloze"]
        if not notes:
            logger.warning("No notes found with 'Custom Cloze' model in Polish deck")
            return

        logger.info(f"Found {len(notes)} notes with 'Custom Cloze' model")

        return notes
            
    except Exception as e:
        logger.error(f"Error during audio enablement process: {e}", exc_info=True)

def process_and_store(sentences: List[Dict[str, Any]]) -> None:
    """Process the sentences and store them in a text file categorized by tags."""
    processed_sentences = []
    for sentence in sentences:
        processed_sentences.append(
            sentence["fields"]["Words Before"]["value"]
            + sentence["fields"]["Cloze Word"]["value"]
            + sentence["fields"]["Words Between"]["value"]
            + sentence["fields"]["Cloze Word Second Part"]["value"]
            + sentence["fields"]["Words After"]["value"]
        )

    # Sort the sentences alphabetically
    processed_sentences = sorted(processed_sentences)

    # Remove duplicates
    processed_sentences = list(dict.fromkeys(processed_sentences))

    # Store the sentences in a text file
    with open("sentences.txt", "w", encoding="utf-8") as f:
        for sentence in processed_sentences:
            f.write(sentence + "\n")

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
    sentences: list[Dict[str, Any]] = get_sentences()
    logger.info("=== End of Anki Fetch ===")

    if not sentences:
        logger.warning("No sentences were retrieved from Anki.")
        exit(0)

    process_and_store(sentences)