---
date_updated: "2024-11-22"
---

# Tutorial: How the `--example` Feature Works in the Interplay of HTML, JavaScript, and Python

## Overview

The `--example` feature in our script generates a natural dialogue using vocabulary from flashcards that are in learning process (i.e. not on the unlearned pile). This dialogue is then transformed into a cloze text format, where certain words or phrases are replaced with placeholders. The user can interact with these placeholders to reveal the original text. This feature involves Python for generating the story, HTML for structuring the content, and JavaScript for the interactive functionality.

## Python Code: Generating the Example Story

The Python function `generate_example_story` is responsible for creating the example story. It queries the SQLite database for vocabulary items not in batch 1, constructs a prompt for the AI model, and then processes the response to create a cloze-formatted story.

### Detailed Explanation of `generate_example_story`

1. **Database Query**: The function starts by querying the SQLite database for flashcards that are not in batch 1. This is done using a SQL query that selects the `front_text` and `back_text` from the `cards` table where the `batch_number` is not equal to 1.

2. **Prompt Construction**: The selected vocabulary items are then used to construct a prompt for the AI model. This prompt instructs the model to create a natural dialogue between two people (A and B) using the provided vocabulary items.

3. **AI Model Interaction**: The function calls the AI model to generate a story based on the constructed prompt. The response from the AI model is then processed to extract the generated story.

4. **Database Insertion**: Finally, the generated story is inserted into the `examples` table in the SQLite database for future reference.

### Example Python Code Snippet

```python
def generate_example_story(conn, batch_index, model):
    # Query database for cards not in batch 1
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
        if front_text or back_text:
            vocab_list.append(f"{front_text},{back_text}")

    prompt = f"""
    Create a natural dialogue between two people (A and B) following these strict rules:
    ...
    Items:
    {';'.join(vocab_list)}
    """
    
    # Call AI model to generate story
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    story = response.choices[0].message.content
    
    # Insert story into examples table
    example_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO examples (id, body)
        VALUES (?, ?)
    ''', (example_id, story))
    conn.commit()
    
    return story
```

## HTML Structure: Displaying the Example Story

The generated story is embedded into an HTML template. This template includes styles and scripts to handle the cloze interactions.

### Detailed Explanation of HTML Structure

1. **Styles**: The CSS styles define how the cloze text and revealed text will appear. The `.cloze` class styles the placeholder text, and the `.revealed` class styles the text once it has been revealed.

2. **JavaScript Initialization**: The JavaScript code initializes the cloze elements and sets up event listeners for keydown events to handle the interaction.

3. **Cloze Interaction**: The `revealNextCloze` function handles the interaction for revealing the next cloze element when the right arrow key is pressed. The `revealCloze` function handles the interaction for revealing a specific cloze element when clicked.

### Example HTML Code Snippet

```html
<!DOCTYPE html>
<html>
<head>
    <title>Cloze Text Example</title>
    <style>
        .cloze {
            cursor: pointer;
            background-color: #f0f0f0;
            padding: 0 4px;
            border-radius: 3px;
        }
        
        .revealed {
            font-style: italic;
            background-color: hsl(56, 100%, 80%);
            padding: 5px
        }
        
        .hint {
            color: #999;
            font-size: 0.9em;
            margin-left: 0.5em;
        }
    </style>
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
                currentElement.textContent = original.charAt(0) + '…';
                currentElement.setAttribute('data-revealed', 'partial');
            } else if (currentElement.getAttribute('data-revealed') === 'partial') {
                currentElement.textContent = original;
                currentElement.classList.remove("cloze");
                currentElement.classList.add("revealed");
                currentElement.setAttribute('data-revealed', 'full');
                currentClozeIndex = (currentClozeIndex + 1) % clozeElements.length;
                revealNextCloze();
            }
        }

        function revealCloze(element) {
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
</head>
<body>
    <div>
        <br>A: [This milk smells like it has gone off.](spoilage)<span class="hint">(spoilage)</span>
        <br>B: I agree, it does have a strange odor.
    </div>
</body>
</html>
```

## JavaScript Functionality: Revealing Clozes

The JavaScript code handles the interaction for revealing the clozes. When a user clicks on a cloze or presses the right arrow key, the original text is gradually revealed.

### Detailed Explanation of JavaScript Functions

1. **Initialization**: The `DOMContentLoaded` event listener initializes the cloze elements and sets up the keydown event listener for the right arrow key.

2. **Revealing Clozes**: The `revealNextCloze` function reveals the next cloze element in sequence. It checks the current state of the cloze element and updates its content and class accordingly.

3. **Revealing Specific Cloze**: The `revealCloze` function handles the interaction for revealing a specific cloze element when clicked. It follows a similar process to `revealNextCloze` but operates on a specific element.

### Example JavaScript Code Snippet

```javascript
function revealNextCloze() {
    if (clozeElements.length === 0) return;

    let currentElement = clozeElements[currentClozeIndex];
    let original = currentElement.getAttribute('data-original');

    if (!currentElement.getAttribute('data-revealed')) {
        currentElement.textContent = original.charAt(0) + '…';
        currentElement.setAttribute('data-revealed', 'partial');
    } else if (currentElement.getAttribute('data-revealed') === 'partial') {
        currentElement.textContent = original;
        currentElement.classList.remove("cloze");
        currentElement.classList.add("revealed");
        currentElement.setAttribute('data-revealed', 'full');
        currentClozeIndex = (currentClozeIndex + 1) % clozeElements.length;
        revealNextCloze();
    }
}

function revealCloze(element) {
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
```

## Practical Example Sentence

Let's consider a practical example sentence:

**Original Sentence:** "This milk smells like it has gone off."

**Cloze-Formatted Sentence:** "A: [This milk smells like it has gone off.](spoilage)<span class="hint">(spoilage)</span>"

When the user interacts with the cloze, the text will be revealed step-by-step:

1. Initial state: "A: […]<span class="hint">(spoilage)</span>"
2. After first interaction: "A: T…<span class="hint">(spoilage)</span>"
3. After second interaction: "A: This milk smells like it has gone off.<span class="hint">(spoilage)</span>"

This tutorial provides a comprehensive understanding of how the `--example` feature integrates Python, HTML, and JavaScript to create an interactive learning experience.
