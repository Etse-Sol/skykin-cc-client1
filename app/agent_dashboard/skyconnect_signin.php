<?php
/**
 * SkyConnect Sign in — board “1. Sign in” from
 * SkyConnect Solutions – Contact Center Design.html (1280×760).
 */
require_once __DIR__ . '/session_bootstrap.php';

if (!empty($_SESSION['authorized']) && !empty($_SESSION['user_uuid'])) {
	header('Location: /app/agent_dashboard/skyconnect_land.php');
	exit;
}

$_SESSION['redirect_path'] = '/app/agent_dashboard/skyconnect_land.php';

header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');
$brand = '/app/agent_dashboard/assets/brand';
?>
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<title>Sign in · SkyConnect</title>
	<link rel="icon" type="image/png" href="<?php echo htmlspecialchars($brand, ENT_QUOTES, 'UTF-8'); ?>/skyconnect-mark.png" />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
	<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet" />
	<style>
		body{margin:0;font-family:Manrope,sans-serif;color:#10261F;background:#F5F7F4}
		h1,h2,h3,p{margin:0}
		.split{display:flex;flex-wrap:wrap;min-height:100vh}
		.hero{
			flex:1 1 420px;
			background:linear-gradient(160deg,#E4F2EA,#CDEBDD);
			color:#10261F;
			padding:56px;
			box-sizing:border-box;
			display:flex;
			flex-direction:column;
			gap:18px;
			justify-content:center;
		}
		.wordmark{height:48px;width:auto;max-width:min(420px,100%);display:block;object-fit:contain;object-position:left center}
		.hero h1{font-size:40px;font-weight:800;line-height:1.15;max-width:460px;letter-spacing:-0.02em}
		.lede{max-width:440px;line-height:1.5;color:#35453E;font-size:16px}
		.form-col{flex:1 1 420px;display:flex;align-items:center;justify-content:center;padding:32px;box-sizing:border-box;background:#F5F7F4}
		.c{background:#fff;border:1px solid #DDE5DF;border-radius:14px;width:100%;max-width:380px;padding:28px;display:flex;flex-direction:column;gap:14px;box-sizing:border-box}
		.b{min-height:44px;padding:0 18px;border-radius:10px;border:1px solid #0B7A5A;background:#0B7A5A;color:#fff;font:700 14px Manrope,sans-serif;cursor:pointer;width:100%}
		.b:hover{background:#0A6B4F}
		.in{min-height:44px;box-sizing:border-box;border:1px solid #B9C7BE;border-radius:10px;padding:0 12px;font:14px Manrope,sans-serif;width:100%;background:#fff;color:#10261F}
		.in:focus{outline:2px solid #0B7A5A;outline-offset:1px}
		label{font-size:12px;font-weight:700;display:block;margin:0 0 5px;color:#10261F}
		.field{display:flex;flex-direction:column}
		.sm{font-size:12.5px;color:#4D5F57;line-height:1.45}
		@media (max-width: 800px){
			.hero{padding:32px 24px}
			.form-col{padding:24px}
		}
	</style>
</head>
<body>
	<div class="split">
		<section class="hero">
			<img class="wordmark" src="<?php echo htmlspecialchars($brand, ENT_QUOTES, 'UTF-8'); ?>/skyconnect-logo.png" alt="SkyConnect Solutions" />
			<h1>One workspace for every conversation</h1>
			<p class="lede">Voice, digital and AI-assisted service in Amharic, English and Afaan Oromo, with live supervision and reporting built in.</p>
		</section>
		<section class="form-col">
			<div class="c">
				<h2 style="font-size:22px;font-weight:800">Sign in</h2>
				<form method="post" action="/login.php" name="frm" style="display:flex;flex-direction:column;gap:14px">
					<input type="hidden" name="path" value="/app/agent_dashboard/skyconnect_land.php" />
					<div class="field">
						<label for="username">Username or email</label>
						<input class="in" type="text" name="username" id="username" autocomplete="username" required />
					</div>
					<div class="field">
						<label for="password">Password</label>
						<input class="in" type="password" name="password" id="password" autocomplete="current-password" required />
					</div>
					<div class="field">
						<label for="sc_lang">Language</label>
						<select id="sc_lang" class="in">
							<option value="en">English</option>
							<option value="am">Amharic</option>
							<option value="om">Afaan Oromo</option>
						</select>
					</div>
					<button class="b" type="submit">Sign in</button>
					<p class="sm">After sign-in you land on the Agent workspace, Supervisor console or Admin studio, based on your role.</p>
				</form>
			</div>
		</section>
	</div>
</body>
</html>
