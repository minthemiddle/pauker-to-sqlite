import click
import gzip
import xml.etree.ElementTree as ET
import sqlite3
import uuid
import os
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.command()
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True), required=True, help='Input Pauker .pau.gz file')
@click.option('-o', '--output', default='pauker_cards.sqlite', help='Output SQLite database filename')
def convert_pauker_to_sqlite(input_file, output):
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

            # Create table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    batch_number INTEGER,
                    card_name TEXT,
                    front_text TEXT,
                    back_text TEXT,
                    learned_timestamp INTEGER
                )
            ''')
            logger.debug("Cards table created")

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
                    # Generate unique ID
                    card_id = str(uuid.uuid4())
                    
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

                    # Create card name
                    card_name = f'card{card_index}'

                    # Log card details before insertion
                    logger.debug(f"Card details - ID: {card_id}, Batch: {batch_index}, Name: {card_name}")
                    logger.debug(f"Front text: {front_text[:50]}...")
                    logger.debug(f"Back text: {back_text[:50]}...")

                    # Insert into database
                    try:
                        cursor.execute('''
                            INSERT INTO cards 
                            (id, batch_number, card_name, front_text, back_text, learned_timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (card_id, batch_index, card_name, front_text, back_text, learned_timestamp))
                        total_cards += 1
                    except sqlite3.Error as sql_err:
                        logger.error(f"SQLite insertion error: {sql_err}")
                        logger.error(traceback.format_exc())

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

if __name__ == '__main__':
    convert_pauker_to_sqlite()
