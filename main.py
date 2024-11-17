import click
import gzip
import xml.etree.ElementTree as ET
import sqlite3
import uuid
import os
import logging
import traceback
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.command()
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True), required=True, help='Input Pauker .pau.gz file')
@click.option('-o', '--output', 'output', type=click.Path(), required=True, help='Output SQLite database file')
@click.option('--example', is_flag=True, help='Generate an example story using vocabulary from cards not in batch 1')
def convert_pauker_to_sqlite(input_file, output, example):
    """
    Convert Pauker .pau.gz flashcard file to SQLite database
    """
    try:
        logger.debug(f"Starting conversion of {input_file}")
        
        # Log input file details
        logger.debug(f"Input file path: {input_file}")
        logger.debug(f"Input file exists: {os.path.exists(input_file)}")
        logger.debug(f"Input file size: {os.path.getsize(input_file)} bytes")

        # Ensure output directory exists
        output_dir = os.path.dirname(os.path.abspath(output))
        logger.debug(f"Output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        # Open the gzipped file with extensive logging
        try:
            logger.debug("Attempting to open gzipped file")
            with gzip.open(input_file, 'rt', encoding='utf-8') as f:
                logger.debug("Successfully opened gzipped file")
                
                # Parse the XML with detailed logging
                try:
                    logger.debug("Parsing XML")
                    tree = ET.parse(f)
                    root = tree.getroot()
                    logger.debug(f"XML root tag: {root.tag}")
                except ET.ParseError as xml_err:
                    logger.error(f"XML Parsing error: {xml_err}")
                    logger.error(traceback.format_exc())
                    raise

        except (IOError, gzip.BadGzipFile) as gz_err:
            logger.error(f"Error opening gzipped file: {gz_err}")
            logger.error(traceback.format_exc())
            raise

        # Create/connect to SQLite database with logging
        try:
            logger.debug(f"Attempting to create SQLite database: {output}")
            conn = sqlite3.connect(output)
            cursor = conn.cursor()
            logger.debug("SQLite connection established")

            # Create tables if they don't exist
            # Drop and recreate cards table to ensure fresh start
            cursor.execute('DROP TABLE IF EXISTS cards')
            cursor.execute('''
                CREATE TABLE cards (
                    id TEXT PRIMARY KEY,
                    batch_number INTEGER,
                    front_text TEXT,
                    back_text TEXT,
                    learned_timestamp INTEGER
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS examples (
                    id TEXT PRIMARY KEY,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    body TEXT
                )
            ''')
            logger.debug("Cards and Examples tables created")

            # Track number of cards processed
            total_cards = 0
            total_batches = 0

            # Process batches with detailed logging
            batches = root.findall('.//Batch')
            logger.debug(f"Total batches found: {len(batches)}")

            for batch_index, batch in enumerate(batches, 1):
                total_batches += 1
                logger.debug(f"Processing batch {batch_index}")
                
                cards = batch.findall('Card')
                logger.debug(f"Cards in batch {batch_index}: {len(cards)}")
                
                for card_index, card in enumerate(cards, 1):
                    # Extract front side details with logging
                    front_side = card.find('FrontSide')
                    front_text = ''
                    learned_timestamp = 0
                    
                    if front_side is not None:
                        front_text_elem = front_side.find('Text')
                        if front_text_elem is not None:
                            front_text = front_text_elem.text or ''
                        learned_timestamp = front_side.get('LearnedTimestamp', 0)
                    
                    # Extract reverse side details with logging
                    reverse_side = card.find('ReverseSide')
                    back_text = ''
                    
                    if reverse_side is not None:
                        back_text_elem = reverse_side.find('Text')
                        if back_text_elem is not None:
                            back_text = back_text_elem.text or ''

                    # Create simple sequential card identifier
                    card_id = f'card{total_cards + 1}'

                    # Log card details before insertion
                    logger.debug(f"Card details - Batch: {batch_index}, ID: {card_id}")
                    logger.debug(f"Front text: {front_text[:50]}...")
                    logger.debug(f"Back text: {back_text[:50]}...")

                    # Insert into database
                    try:
                        cursor.execute('''
                            INSERT INTO cards 
                            (id, batch_number, front_text, back_text, learned_timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (card_id, batch_index, front_text, back_text, learned_timestamp))
                        total_cards += 1
                    except sqlite3.Error as sql_err:
                        logger.error(f"SQLite insertion error: {sql_err}")
                        logger.error(traceback.format_exc())

            if example:
                story = generate_example_story(conn, batch_index=1)  # Default to batch 1
                if story is None:
                    logger.warning("Skipping example story generation due to missing API key")

            # Commit the transaction and close the connection
            conn.commit()
            conn.close()
            logger.info(f"Successfully created SQLite database: {output}")
            logger.info(f"Total batches processed: {total_batches}")
            logger.info(f"Total cards processed: {total_cards}")

        except sqlite3.Error as db_err:
            logger.error(f"SQLite database error: {db_err}")
            logger.error(traceback.format_exc())
            raise

    except Exception as e:
        logger.error(f"Unexpected error converting Pauker file: {e}")
        logger.error(traceback.format_exc())
        raise

import os

def generate_example_story(conn, batch_index):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return None

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    # Query database for cards not in batch 1, sorted by learned_timestamp
    cursor = conn.cursor()
    cursor.execute('''
        SELECT front_text, back_text 
        FROM cards 
        WHERE batch_number != 1 
        ORDER BY learned_timestamp ASC 
        LIMIT 15
    ''')
    
    vocab_list = []
    for front_text, back_text in cursor.fetchall():
        # Only add non-empty entries
        if front_text or back_text:
            vocab_list.append(f"{front_text},{back_text}")

    prompt = f"""Create a short exciting story that incorporates as many of these vocabulary words as possible. Vocabs must appear in random order.
Make it a consistent cloze story where the vocabulary words are hidden. 

Vocabulary format: 
- Each vocabulary entry is separated by a semicolon (;)
- Within each entry, the word and its translation are separated by a comma (,)

Cloze format:
[CONTENT TO BE DISCLOSED]
Only the needed verb is put there, NOT the explanation.

Vocabulary list:
{';'.join(vocab_list)}"""
    
    response = client.chat.completions.create(
        model="gemini-1.5-flash",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    story = response.choices[0].message.content
    
    # Insert story into examples table
    cursor = conn.cursor()
    example_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO examples (id, body)
        VALUES (?, ?)
    ''', (example_id, story))
    conn.commit()
    
    logger.info(f"Successfully created example story with ID: {example_id}")
    return story

if __name__ == '__main__':
    convert_pauker_to_sqlite()
