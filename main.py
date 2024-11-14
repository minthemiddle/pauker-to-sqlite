import click
import gzip
import xml.etree.ElementTree as ET
import sqlite3
import uuid

@click.command()
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True), required=True, help='Input Pauker .pau.gz file')
@click.option('-o', '--output', default='pauker_cards.sqlite', help='Output SQLite database filename')
def convert_pauker_to_sqlite(input_file, output):
    """
    Convert Pauker .pau.gz flashcard file to SQLite database
    """
    # Open the gzipped file
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        # Parse the XML
        tree = ET.parse(f)
        root = tree.getroot()

    # Create/connect to SQLite database
    conn = sqlite3.connect(output)
    cursor = conn.cursor()

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

    # Process batches
    for batch_index, batch in enumerate(root.findall('.//Batch'), 1):
        cards = batch.findall('Card')
        
        for card_index, card in enumerate(cards, 1):
            # Generate unique ID
            card_id = str(uuid.uuid4())
            
            # Extract front side details
            front_side = card.find('FrontSide')
            front_text = front_side.find('Text').text if front_side is not None and front_side.find('Text') is not None else ''
            learned_timestamp = front_side.get('LearnedTimestamp', 0) if front_side is not None else 0

            # Extract reverse side details
            reverse_side = card.find('ReverseSide')
            back_text = reverse_side.find('Text').text if reverse_side is not None and reverse_side.find('Text') is not None else ''

            # Create card name
            card_name = f'card{card_index}'

            # Insert into database
            cursor.execute('''
                INSERT INTO cards 
                (id, batch_number, card_name, front_text, back_text, learned_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (card_id, batch_index, card_name, front_text, back_text, learned_timestamp))
