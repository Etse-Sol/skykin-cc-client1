<?php
/**
 * Create SkyKin supervisor group + user on a fresh install.
 * Login: supervisor / Supervisor123! @ client1.skykin.local
 * Dashboard: /app/agent_dashboard/supervisor.php
 */
require "/var/www/fusionpbx/resources/require.php";

$database = new database;
$domain_name = "client1.skykin.local";
$username = "supervisor";
$password = "Supervisor123!";

$domain_uuid = $database->select(
	"select domain_uuid from v_domains where domain_name = :d",
	["d" => $domain_name],
	"column"
);
if (empty($domain_uuid)) {
	fwrite(STDERR, "domain missing: $domain_name\n");
	exit(1);
}

// group
$group_uuid = $database->select(
	"select group_uuid from v_groups where group_name = 'supervisor' and domain_uuid is null",
	null,
	"column"
);
if (empty($group_uuid)) {
	$group_uuid = uuid();
	$p = permissions::new();
	$p->add("group_add", "temp");
	$array = [];
	$array["groups"][0]["group_uuid"] = $group_uuid;
	$array["groups"][0]["domain_uuid"] = null;
	$array["groups"][0]["group_name"] = "supervisor";
	$array["groups"][0]["group_level"] = "40";
	$array["groups"][0]["group_description"] = "SkyKin Call Center Supervisor";
	$array["groups"][0]["group_protected"] = "false";
	$database->save($array);
	$p->delete("group_add", "temp");
	echo "created group supervisor\n";
} else {
	echo "group supervisor exists\n";
}

// useful permissions so they can use FusionPBX lightly + agent dashboard
$want = [
	"login",
	"user_view",
	"extension_view",
	"xml_cdr_view",
	"dashboard_view",
];
$p = permissions::new();
$p->add("group_permission_add", "temp");
$x = 0;
$array = [];
foreach ($want as $perm) {
	$exists = $database->select(
		"select group_permission_uuid from v_group_permissions
		 where group_uuid = :g and permission_name = :n and domain_uuid is null",
		["g" => $group_uuid, "n" => $perm],
		"column"
	);
	if (empty($exists)) {
		$array["group_permissions"][$x]["group_permission_uuid"] = uuid();
		$array["group_permissions"][$x]["domain_uuid"] = null;
		$array["group_permissions"][$x]["permission_name"] = $perm;
		$array["group_permissions"][$x]["permission_protected"] = "false";
		$array["group_permissions"][$x]["permission_assigned"] = "true";
		$array["group_permissions"][$x]["group_name"] = "supervisor";
		$array["group_permissions"][$x]["group_uuid"] = $group_uuid;
		$x++;
	}
}
if (!empty($array)) {
	$database->save($array);
	echo "added $x group permissions\n";
}
$p->delete("group_permission_add", "temp");

// user
$user_uuid = $database->select(
	"select user_uuid from v_users where username = :u and domain_uuid = :d",
	["u" => $username, "d" => $domain_uuid],
	"column"
);
$user_salt = uuid();
$password_hash = md5($user_salt . $password);
$p = permissions::new();
if (empty($user_uuid)) {
	$user_uuid = uuid();
	$p->add("user_add", "temp");
	echo "created user $username\n";
} else {
	$p->add("user_edit", "temp");
	echo "reset password for $username\n";
}
$array = [];
$array["users"][0]["user_uuid"] = $user_uuid;
$array["users"][0]["domain_uuid"] = $domain_uuid;
$array["users"][0]["username"] = $username;
$array["users"][0]["password"] = $password_hash;
$array["users"][0]["salt"] = $user_salt;
$array["users"][0]["user_enabled"] = "true";
$database->save($array);
$p->delete("user_add", "temp");
$p->delete("user_edit", "temp");

// membership
$ug = $database->select(
	"select user_group_uuid from v_user_groups where user_uuid = :u and group_uuid = :g",
	["u" => $user_uuid, "g" => $group_uuid],
	"column"
);
if (empty($ug)) {
	$p = permissions::new();
	$p->add("user_group_add", "temp");
	$array = [];
	$array["user_groups"][0]["user_group_uuid"] = uuid();
	$array["user_groups"][0]["domain_uuid"] = $domain_uuid;
	$array["user_groups"][0]["group_name"] = "supervisor";
	$array["user_groups"][0]["group_uuid"] = $group_uuid;
	$array["user_groups"][0]["user_uuid"] = $user_uuid;
	$database->save($array);
	$p->delete("user_group_add", "temp");
	echo "added user to supervisor group\n";
}

echo "OK\n";
echo "FusionPBX login: $username / $password @ $domain_name\n";
echo "Supervisor board: /app/agent_dashboard/supervisor.php\n";
