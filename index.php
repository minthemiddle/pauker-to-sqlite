<?php
// SQLite database file
$sqliteFile = "out.sqlite";

// Create connection
$conn = new SQLite3($sqliteFile);

// Check connection
if (!$conn) {
    die("Connection failed: " . $conn->lastErrorMsg());
}

// Query to get the latest example
$sql = "SELECT body FROM examples ORDER BY date DESC LIMIT 1";
$result = $conn->query($sql);

$body = "";
if ($result) {
    $row = $result->fetchArray(SQLITE3_ASSOC);
    if ($row) {
        $body = $row["body"];

        // Replace cloze text with hidden spans
        $body = preg_replace(
            "/\[(.*?)\]/",
            '<span class="cloze" onclick="revealCloze(this)" data-original="$1">[…]</span>',
            $body
        );
    } else {
        $body = "No examples found.";
    }
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>Cloze Text Example</title>
    <style>
        .cloze {
            cursor: pointer;
        }
        
        html, body {
            font-size: 21px;
            max-width: 32rem;
            line-height: 1.5;
            padding: 1rem;
        }

        .revealed {
            font-style: italic;
            color: #666;
        }
    </style>
    <script>
        function revealCloze(element) {
            if (!element.getAttribute('data-revealed')) {
                // First click: show first character
                let original = element.getAttribute('data-original');
                element.textContent = original.charAt(0) + '…';
                element.setAttribute('data-revealed', 'partial');
            } else if (element.getAttribute('data-revealed') === 'partial') {
                // Second click: show full solution
                element.textContent = element.getAttribute('data-original');
                element.classList.remove("cloze");
                element.classList.add("revealed");
                element.setAttribute('data-revealed', 'full');
            }
        }
    </script>
</head>
<body>
    <h1>Latest Example</h1>
    <p><?php echo $body; ?></p>
</body>
</html>

<?php $conn->close();
?>
