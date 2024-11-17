<?php
 // Database connection details
 $servername = "localhost";
 $username = "your_username";
 $password = "your_password";
 $dbname = "out";

 // Create connection
 $conn = new mysqli($servername, $username, $password, $dbname);

 // Check connection
 if ($conn->connect_error) {
     die("Connection failed: " . $conn->connect_error);
 }

 // Query to get the latest example
 $sql = "SELECT body FROM examples ORDER BY id DESC LIMIT 1";
 $result = $conn->query($sql);

 if ($result->num_rows > 0) {
     $row = $result->fetch_assoc();
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
