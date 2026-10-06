<?php
/**
 * Rebuild FusionPBX defaults for a fresh client1 install:
 * - default groups + full group_permissions
 * - default menu with all items + superadmin links
 * - domain menu setting
 *
 * Run inside skykin-web:
 *   php /tmp/skykin_bootstrap_full_access.php
 */
require "/var/www/fusionpbx/resources/require.php";

$database = new database;
$menu_uuid = "b4750c3f-2a86-b00d-b7d0-345c14eca286";
$domain_name = "client1.skykin.local";

function count_sql($database, $sql, $params = null) {
	return (int) $database->select($sql, $params, "column");
}

echo "== BEFORE ==\n";
echo "group_permissions=" . count_sql($database, "select count(*) from v_group_permissions") . "\n";
echo "menu_items=" . count_sql($database, "select count(*) from v_menu_items") . "\n";
echo "menu_item_groups=" . count_sql($database, "select count(*) from v_menu_item_groups") . "\n";

// --- groups + full permissions ---
$group_rows = $database->select(
	"select group_uuid, group_name from v_groups where domain_uuid is null",
	null,
	"all"
);
$group_uuids = [];
if (is_array($group_rows)) {
	foreach ($group_rows as $row) {
		$group_uuids[$row["group_name"]] = $row["group_uuid"];
	}
}

// ensure base groups exist
$g = new groups;
$g->defaults();

$group_rows = $database->select(
	"select group_uuid, group_name from v_groups where domain_uuid is null",
	null,
	"all"
);
$group_uuids = [];
foreach ($group_rows as $row) {
	$group_uuids[$row["group_name"]] = $row["group_uuid"];
}

// rebuild ALL global group permissions from app_config.php
$database->execute("delete from v_group_permissions where domain_uuid is null", null);
$apps = [];
$config_list = glob("/var/www/fusionpbx/{core,app}/*/app_config.php", GLOB_BRACE);
$x = 0;
foreach ($config_list as $config_path) {
	include $config_path;
}
$array = [];
if (is_array($apps)) {
	foreach ($apps as $app) {
		if (empty($app["permissions"]) || !is_array($app["permissions"])) {
			continue;
		}
		foreach ($app["permissions"] as $row) {
			if (empty($row["groups"]) || !is_array($row["groups"])) {
				continue;
			}
			foreach ($row["groups"] as $group) {
				if (empty($group_uuids[$group])) {
					continue;
				}
				$array["group_permissions"][$x]["group_permission_uuid"] = uuid();
				$array["group_permissions"][$x]["domain_uuid"] = null;
				$array["group_permissions"][$x]["permission_name"] = $row["name"];
				$array["group_permissions"][$x]["permission_protected"] = "false";
				$array["group_permissions"][$x]["permission_assigned"] = "true";
				$array["group_permissions"][$x]["group_name"] = $group;
				$array["group_permissions"][$x]["group_uuid"] = $group_uuids[$group];
				$x++;
			}
		}
	}
}
if (!empty($array)) {
	$p = permissions::new();
	$p->add("group_permission_add", "temp");
	$database->save($array);
	$p->delete("group_permission_add", "temp");
}
echo "group_permissions now=" . count_sql($database, "select count(*) from v_group_permissions where domain_uuid is null") . "\n";

// --- wipe and rebuild default menu ---
$database->execute("delete from v_menu_item_groups where menu_uuid = :u", ["u" => $menu_uuid]);
$database->execute("delete from v_menu_languages where menu_uuid = :u", ["u" => $menu_uuid]);
$database->execute("delete from v_menu_items where menu_uuid = :u", ["u" => $menu_uuid]);
$database->execute("delete from v_menus where menu_uuid = :u", ["u" => $menu_uuid]);

$menu = new menu;
$menu->menu_uuid = $menu_uuid;
$menu->menu_language = "en-us";
$menu->menu_default();
$menu->restore_default();

echo "menu_items now=" . count_sql($database, "select count(*) from v_menu_items where menu_uuid = :u", ["u" => $menu_uuid]) . "\n";
echo "menu_item_groups now=" . count_sql($database, "select count(*) from v_menu_item_groups where menu_uuid = :u", ["u" => $menu_uuid]) . "\n";

// ensure every menu item is visible to superadmin (full access)
$super_uuid = $group_uuids["superadmin"] ?? null;
if ($super_uuid) {
	$missing = $database->select(
		"select i.menu_item_uuid
		 from v_menu_items i
		 where i.menu_uuid = :m
		   and not exists (
		     select 1 from v_menu_item_groups g
		     where g.menu_item_uuid = i.menu_item_uuid
		       and g.group_uuid = :g
		   )",
		["m" => $menu_uuid, "g" => $super_uuid],
		"all"
	);
	if (is_array($missing) && count($missing)) {
		$p = permissions::new();
		$p->add("menu_item_group_add", "temp");
		$array = [];
		$i = 0;
		foreach ($missing as $row) {
			$array["menu_item_groups"][$i]["menu_item_group_uuid"] = uuid();
			$array["menu_item_groups"][$i]["menu_uuid"] = $menu_uuid;
			$array["menu_item_groups"][$i]["menu_item_uuid"] = $row["menu_item_uuid"];
			$array["menu_item_groups"][$i]["group_name"] = "superadmin";
			$array["menu_item_groups"][$i]["group_uuid"] = $super_uuid;
			$i++;
		}
		$database->save($array);
		$p->delete("menu_item_group_add", "temp");
		echo "linked " . count($missing) . " menu items to superadmin\n";
	} else {
		echo "all menu items already linked to superadmin\n";
	}
}

// domain menu setting
$domain_uuid = $database->select(
	"select domain_uuid from v_domains where domain_name = :d",
	["d" => $domain_name],
	"column"
);
if (!empty($domain_uuid)) {
	$exists = $database->select(
		"select domain_setting_uuid from v_domain_settings
		 where domain_uuid = :d and domain_setting_category = 'domain'
		   and domain_setting_subcategory = 'menu' and domain_setting_name = 'uuid'",
		["d" => $domain_uuid],
		"column"
	);
	if (empty($exists)) {
		$p = permissions::new();
		$p->add("domain_setting_add", "temp");
		$array = [];
		$array["domain_settings"][0]["domain_setting_uuid"] = uuid();
		$array["domain_settings"][0]["domain_uuid"] = $domain_uuid;
		$array["domain_settings"][0]["domain_setting_category"] = "domain";
		$array["domain_settings"][0]["domain_setting_subcategory"] = "menu";
		$array["domain_settings"][0]["domain_setting_name"] = "uuid";
		$array["domain_settings"][0]["domain_setting_value"] = $menu_uuid;
		$array["domain_settings"][0]["domain_setting_enabled"] = true;
		$database->save($array);
		$p->delete("domain_setting_add", "temp");
	} else {
		$database->execute(
			"update v_domain_settings
			 set domain_setting_value = :v, domain_setting_enabled = true
			 where domain_setting_uuid = :u",
			["v" => $menu_uuid, "u" => $exists]
		);
	}
	echo "domain menu uuid set for $domain_name\n";
}

// sample Accounts children
$rows = $database->select(
	"select p.menu_item_title as parent, c.menu_item_title as child, c.menu_item_link
	 from v_menu_items c
	 left join v_menu_items p on p.menu_item_uuid = c.menu_item_parent_uuid
	 join v_menu_item_groups g on g.menu_item_uuid = c.menu_item_uuid and g.group_name = 'superadmin'
	 where c.menu_uuid = :u
	   and (
	     lower(coalesce(p.menu_item_title,'')) like '%account%'
	     or lower(c.menu_item_title) like '%extension%'
	     or c.menu_item_link like '%extensions%'
	   )
	 order by c.menu_item_title",
	["u" => $menu_uuid],
	"all"
);
echo "== Accounts / Extensions menu sample ==\n";
if (is_array($rows) && count($rows)) {
	foreach ($rows as $r) {
		echo "  {$r['parent']} -> {$r['child']} ({$r['menu_item_link']})\n";
	}
} else {
	echo "  (still missing — check app_menu.php files)\n";
}

echo "== DONE ==\n";
echo "Logout, clear site cookies, login as admin / Admin123! @ client1.skykin.local\n";
echo "Hover/click Accounts — Extensions should appear.\n";
