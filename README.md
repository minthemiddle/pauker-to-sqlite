# Pauker to SQLite Converter

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

## Troubleshooting

- **Error: File not found**: Ensure the input file path is correct and the file exists.
- **Error: SQLite database error**: Ensure the output directory exists and is writable.
- **Error: XML Parsing error**: Ensure the input file is a valid Pauker `.pau.gz` file.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
