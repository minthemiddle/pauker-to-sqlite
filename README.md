# Pauker to SQLite Converter

**About this project**: Convert Pauker flashcard files to an SQLite database for easier management and querying.

This script converts Pauker flashcard files (`.pau.gz`) into an SQLite database, making it easier to manage and query flashcard data.

## Prerequisites

Before using this script, ensure you have the following installed:
- Python 3.x
- `click` library (`pip install click`)
- `gzip` library (usually included with Python)
- `xml.etree.ElementTree` library (usually included with Python)
- `sqlite3` library (usually included with Python)

## Usage

To convert a Pauker file to an SQLite database, use the following command:

```bash
python main.py -i <input_file.pau.gz> -o <output_file.sqlite>
```

### Options
- `-i, --input`: Path to the input Pauker `.pau.gz` file. This is required.
- `-o, --output`: Path to the output SQLite database file. Defaults to `pauker_cards.sqlite`.

## Example

Suppose you have a Pauker file named `my_flashcards.pau.gz` and you want to convert it to an SQLite database named `my_flashcards.sqlite`. You would run:

```bash
python main.py -i my_flashcards.pau.gz -o my_flashcards.sqlite
```

## Changes to the Original Pauker File

During the conversion process, the following changes are made to the original Pauker file:
- **File Format**: The `.pau.gz` file is decompressed and parsed as an XML file.
- **Data Structure**: The XML structure is traversed to extract relevant information, which is then stored in an SQLite database.
- **Card IDs**: Each card is assigned a unique identifier (`id`) in the SQLite database.
- **Learned Timestamp**: The `LearnedTimestamp` attribute from the Pauker file is preserved and stored in the SQLite database.

## Processing Different Information

The script processes different types of information as follows:
- **Front Text**: Extracted from the `<FrontSide>` element and stored in the `front_text` column of the SQLite database.
- **Back Text**: Extracted from the `<ReverseSide>` element and stored in the `back_text` column of the SQLite database.
- **Learned Timestamp**: Extracted from the `LearnedTimestamp` attribute of the `<FrontSide>` element and stored in the `learned_timestamp` column of the SQLite database.
- **Batch Number**: Each card is associated with a batch number, which is derived from its position within the XML structure.
- **Font Info**: The font for front or back of a card is not being transformed (as of now)

## Troubleshooting

- **Error: File not found**: Ensure the input file path is correct and the file exists.
- **Error: SQLite database error**: Ensure the output directory exists and is writable.
- **Error: XML Parsing error**: Ensure the input file is a valid Pauker `.pau.gz` file.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.
