<?php
require_once __DIR__ . "/resources/require.php";

if (!empty($_SESSION["authorized"]) && !empty($_SESSION["username"])) {
	header("Location: /app/agent_dashboard/skyconnect_land.php");
	exit;
}

require __DIR__ . "/app/agent_dashboard/skyconnect_signin.php";
exit;
