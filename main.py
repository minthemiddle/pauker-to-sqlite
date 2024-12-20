import os
import click
import gzip
import xml.etree.ElementTree as ET
import sqlite3
import uuid
import logging
import traceback
import html
import re
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.command()
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True), required=True, help='Input Pauker .pau.gz file')
@click.option('-o', '--output', 'output', type=click.Path(), required=True, help='Output SQLite database file')
@click.option('--example', is_flag=True, help='Generate an example story using vocabulary from cards not in batch 1')
@click.option('--model', type=click.Choice(['openai', 'gemini'], case_sensitive=False), default='openai', help='Specify the model to use for generating the example story')
def convert_pauker_to_sqlite(input_file, output, example, model):
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
                            front_text = f'"{front_text_elem.text or ""}"'
                        learned_timestamp = front_side.get('LearnedTimestamp', 0)
                    
                    # Extract reverse side details with logging
                    reverse_side = card.find('ReverseSide')
                    back_text = ''
                    
                    if reverse_side is not None:
                        back_text_elem = reverse_side.find('Text')
                        if back_text_elem is not None:
                            back_text = f'"{back_text_elem.text or ""}"'

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
                story = generate_example_story(conn, batch_index=1, model=model)  # Default to batch 1
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

def generate_example_story(conn, batch_index, model):
    if model.lower() == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            return None

        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    else:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return None

        client = OpenAI(
            api_key=api_key
        )

    # Query database for cards not in batch 1, sorted by learned_timestamp
    cursor = conn.cursor()
    cursor.execute('''
        SELECT front_text, back_text 
        FROM cards 
        WHERE batch_number != 1 
        ORDER BY random()
        LIMIT 15
    ''')
    
    vocab_list = []
    for front_text, back_text in cursor.fetchall():
        # Only add non-empty entries
        if front_text or back_text:
            vocab_list.append(f"{front_text},{back_text}")

    prompt = f"""
Create a natural dialogue between two people (A and B) following these strict rules:
1. Input Vocabulary Format:
- Items to be provided in format (front/back side): Sentence with clozed phrase/word in square brackets,definition for cloze in round bracket;Sentence with clozed phrase/word in square brackets,definition for cloze in round bracket
- Example (2 cards): "His [w…] have always been critical of modern scientific research. (academic criticism)","worldview";"I'm searching for a [l…] to help me understand the hidden meanings in this poem. (book or website)","lexicon"
- Vocabulary items will serve as INSPIRATION for unique dialogue content

2. Cloze Format Rules:
- Each vocabulary item MUST be converted to a cloze using this format: [vocabulary item](brief definition)
- Cloze replacement happens dynamically in the dialogue
- Only provided vocabulary items should become clozes
- Each cloze definition must be 1-4 words maximum
- Preserve the original form of the vocabulary item exactly

3. Dialogue Creation Guidelines:
- Begin each line with 'A:' or 'B:'
- Maintain natural, logical conversation flow
- USE ALL provided vocabulary items exactly once
- Distribute vocabulary items RANDOMLY throughout dialogue
- CRUCIAL REQUIREMENT: Create ENTIRELY NEW contexts and examples
    - NO direct repetition of input scenarios
    - RADICAL transformation of original context
    - Generate completely original dialogue scenarios
- Avoid ANY literal translation or direct adaptation of input examples

4. Creativity Mandate:
- Invent fresh narrative contexts
- Demonstrate linguistic creativity
- Demonstrate expert knowledge on the right useage of idioms (i.e. with the right meaning)
- Ensure vocabulary items feel organic and spontaneous in use

Example Transformation Principle:
Input: "This milk smells like it has gone off."
FORBIDDEN: Repeating milk/spoilage scenario
REQUIRED: Completely different context (e.g., discussing a bizarre work situation, personal anecdote, etc.)

Objective: Generate a dialogue that feels natural, surprising, and completely divorced from the original input while faithfully incorporating all provided vocabulary items.

Items:
{';'.join(vocab_list)}
"""
    
    if model.lower() == 'gemini':
        response = client.chat.completions.create(
            model="gemini-1.5-pro",
            n=1,
            messages=[
                {"role": "system", "content": "You are an expert in dialog creation. You can tell great, consistent stories that make sense. You are great at using the right idiom at the right time with the right meaning for the given context."},
                {"role": "user", "content": prompt}
            ]
        )
    else:
        response = client.chat.completions.create(
            model="gpt-4o",
            n=1,
            messages=[
                {"role": "system", "content": "You are an expert in dialog creation. You can tell great, consistent stories that make sense. You are great at using the right idiom at the right time with the right meaning for the given context."},
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
    
    # Generate static HTML

    def process_cloze(match):
        full_text = match.group(0)
        try:
            content, hint = full_text[1:-1].split('](')
            escaped_content = html.escape(content)
            escaped_hint = html.escape(hint)
            return f'<span class="cloze" onclick="revealCloze(this)" data-original="{escaped_content}" title="{escaped_hint}">[…]</span><span class="hint">({escaped_hint})</span>'
        except ValueError:
            # Fallback if split fails
            return full_text

    # Ensure dialog parts start on new lines
    story_with_line_breaks = re.sub(r'^(A:|B:)', r'<br>\1', story, flags=re.MULTILINE)
    story_with_clozes = re.sub(r'\[.*?\]\(.*?\)', process_cloze, story_with_line_breaks)

    script_content = """
    <script>
        let clozeElements = [];
        let currentClozeIndex = 0;

        document.addEventListener('DOMContentLoaded', () => {
            clozeElements = Array.from(document.querySelectorAll('.cloze'));
            
            document.addEventListener('keydown', (event) => {
                if (event.key === 'ArrowRight') {
                    event.preventDefault();
                    revealNextCloze();
                }
            });
        });

        function revealNextCloze() {
            if (clozeElements.length === 0) return;

            let currentElement = clozeElements[currentClozeIndex];
            let original = currentElement.getAttribute('data-original');

            if (!currentElement.getAttribute('data-revealed')) {
                // First interaction: show first character
                currentElement.textContent = original.charAt(0) + '…';
                currentElement.setAttribute('data-revealed', 'partial');
            } else if (currentElement.getAttribute('data-revealed') === 'partial') {
                // Second interaction: show full solution
                currentElement.textContent = original;
                currentElement.classList.remove("cloze");
                currentElement.classList.add("revealed");
                currentElement.setAttribute('data-revealed', 'full');
                // Move to next cloze
                currentClozeIndex = (currentClozeIndex + 1) % clozeElements.length;
                revealNextCloze();
            }
        }

        function revealCloze(element) {
            // Maintain existing click behavior
            if (!element.getAttribute('data-revealed')) {
                let original = element.getAttribute('data-original');
                element.textContent = original.charAt(0) + '…';
                element.setAttribute('data-revealed', 'partial');
            } else if (element.getAttribute('data-revealed') === 'partial') {
                element.textContent = element.getAttribute('data-original');
                element.classList.remove("cloze");
                element.classList.add("revealed");
                element.setAttribute('data-revealed', 'full');
            }
        }
    </script>
"""

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Language Exercise</title>
    <style>
        .cloze {{
            cursor: pointer;
            background-color: #f0f0f0;
            padding: 0 4px;
            border-radius: 3px;
        }}
        
        html, body {{
            font-size: 21px;
            max-width: 32rem;
            line-height: 1.5;
            margin-top: -25px;
            padding: 1rem;
            font-family: Arial, sans-serif;
        }}
        
        br {{
            margin-bottom: 16px;
        }}
            

        .revealed {{
            font-style: italic;
            background-color: hsl(56, 100%, 80%);
            padding: 5px
        }}
        
        .hint {{
            color: #999;
            font-size: 0.9em;
            margin-left: 0.5em;
        }}
    </style>
{script_content}
</head>
<body>
    <div>{story_with_clozes}</div>
</body>
</html>"""

    # Ensure the out/ directory exists
    os.makedirs('out', exist_ok=True)
    
    # Write static HTML using the example ID as the filename
    html_filename = f"out/{example_id.split('-')[0]}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info(f"Successfully created example story with ID: {example_id} in {html_filename}")
    
    # Open the HTML file with the default web browser
    os.system(f'open {html_filename}')
    
    return story

if __name__ == '__main__':
    convert_pauker_to_sqlite()
