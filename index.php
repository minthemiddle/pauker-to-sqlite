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
 $sql = "SELECT body FROM examples ORDER BY id DESC LIMIT 1";
 $result = $conn->query($sql);

 if ($result) {
     $row = $result->fetchArray(SQLITE3_ASSOC);
     if ($row) {
         $body = $row["body"];

         // Replace cloze text with hidden spans
         $body = preg_replace('/\[(.*?)\]/', '<span class="cloze" onclick="revealCloze(this)">$1</span>', $body);
 ?>

 <!DOCTYPE html>
 <html>
 <head>
     <title>Cloze Text Example</title>
     <style>
         .cloze {
             background-color: #ccc;
             padding: 2px 4px;
             cursor: pointer;
         }
     </style>
     <script>
         function revealCloze(element) {
             element.classList.remove("cloze");
             element.style.backgroundColor = "transparent";
         }
     </script>
 </head>
 <body>
     <h1>Latest Example</h1>
     <p><?php echo $body; ?></p>
 </body>
 </html>

 <?php
     } else {
         echo "No examples found.";
     }

     $conn->close();
 ?>
