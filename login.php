<?php
/*
	FusionPBX
	Version: MPL 1.1

	The contents of this file are subject to the Mozilla Public License Version
	1.1 (the "License"); you may not use this file except in compliance with
	the License. You may obtain a copy of the License at
	http://www.mozilla.org/MPL/

	Software distributed under the License is distributed on an "AS IS" basis,
	WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
	for the specific language governing rights and limitations under the
	License.

	The Original Code is FusionPBX

	The Initial Developer of the Original Code is
	Mark J Crane <markjcrane@fusionpbx.com>
	Portions created by the Initial Developer are Copyright (C) 2008-2023
	the Initial Developer. All Rights Reserved.

	Contributor(s):
	Mark J. Crane <markjcrane@fusionpbx.com>
*/
//includes files
	require_once __DIR__ . "/resources/require.php";

// SkyKin: IP host (196.189.x.x) is not a FusionPBX domain. Login form has no domain field.
	if (empty($_REQUEST['domain_name'])) {
		$_POST['domain_name'] = 'client1.skykin.local';
		$_REQUEST['domain_name'] = 'client1.skykin.local';
	}

// SkyKin: if already logged in, do not silently bounce away from login.
// Show a chooser so the user can continue or sign in as someone else.
	if (!empty($_SESSION['authorized'])) {
		// Switch-user must be an explicit POST. As a GET link it could be
		// triggered by a link prefetch or a background redirect, which silently
		// destroyed a working login.
		if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['switch'] ?? '') === '1') {
			$_SESSION = [];
			if (ini_get('session.use_cookies')) {
				$params = session_get_cookie_params();
				setcookie(session_name(), '', time() - 42000,
					$params['path'] ?? '/',
					$params['domain'] ?? '',
					false,
					true
				);
				if (!empty($_COOKIE['remember'])) {
					setcookie('remember', '', time() - 42000, '/');
				}
			}
			session_destroy();
			session_start();
			$_SESSION['authorized'] = false;
			// fall through to check_auth → login form
		}
		else {
			header('Location: /app/agent_dashboard/skyconnect_land.php');
			exit;
		}
	}

//additional includes — shows login form when not authorized; redirects after successful login
	require_once "resources/check_auth.php";

//redirect to the dashboard (reached only when already authorized after login)
	header("Location: ".$settings->get('login', 'destination', PROJECT_PATH.'/core/dashboard/'));

?>
