<?php
/**
 * Fix FusionPBX menu parent links using the stable "uuid" column from app_menu.php.
 * Also ensure en-us language rows and superadmin group links exist.
 */
require "/var/www/fusionpbx/resources/require.php";

$database = new database;
$menu_uuid = "b4750c3f-2a86-b00d-b7d0-345c14eca286";

// original_uuid => menu_item_uuid
$rows = $database->select(
	"select menu_item_uuid, uuid, menu_item_title, menu_item_parent_uuid, menu_item_link
	 from v_menu_items where menu_uuid = :m",
	["m" => $menu_uuid],
	"all"
);
$map = [];
foreach ($rows as $r) {
	if (!empty($r["uuid"])) {
		$map[$r["uuid"]] = $r["menu_item_uuid"];
	}
}
echo "menu items=" . count($rows) . " uuid_map=" . count($map) . "\n";

// Build expected parent from app_menu.php files
$apps = [];
$x = 0;
$list = glob("/var/www/fusionpbx/{core,app}/*/app_menu.php", GLOB_BRACE);
sort($list);
// core/menu first so parent definitions exist conceptually
usort($list, function ($a, $b) {
	$ac = str_contains($a, "/core/menu/") ? 0 : 1;
	$bc = str_contains($b, "/core/menu/") ? 0 : 1;
	return $ac <=> $bc ?: strcmp($a, $b);
});
foreach ($list as $path) {
	include $path;
	$x++;
}

$fixed = 0;
$missing_parent = 0;
$missing_item = 0;
if (is_array($apps)) {
	foreach ($apps as $app) {
		if (empty($app["menu"]) || !is_array($app["menu"])) {
			continue;
		}
		foreach ($app["menu"] as $m) {
			$ouuid = $m["uuid"] ?? null;
			$oparent = $m["parent_uuid"] ?? null;
			if (empty($ouuid) || empty($map[$ouuid])) {
				$missing_item++;
				continue;
			}
			$item_uuid = $map[$ouuid];
			$parent_item_uuid = null;
			if (!empty($oparent)) {
				if (empty($map[$oparent])) {
					$missing_parent++;
					echo "MISSING parent uuid $oparent for {$m['title']['en-us']} ($ouuid)\n";
					continue;
				}
				$parent_item_uuid = $map[$oparent];
			}
			$database->execute(
				"update v_menu_items
				 set menu_item_parent_uuid = :p
				 where menu_item_uuid = :i and menu_uuid = :m",
				["p" => $parent_item_uuid, "i" => $item_uuid, "m" => $menu_uuid]
			);
			$fixed++;
		}
	}
}
echo "updated parent links for $fixed items (missing_item=$missing_item missing_parent=$missing_parent)\n";

// Ensure en-us language row for every item
$langs_added = 0;
foreach ($rows as $r) {
	$n = $database->select(
		"select count(*) from v_menu_languages
		 where menu_item_uuid = :i and menu_language = 'en-us'",
		["i" => $r["menu_item_uuid"]],
		"column"
	);
	if ((int)$n === 0) {
		$title = $r["menu_item_title"] ?: "Item";
		$database->execute(
			"insert into v_menu_languages
			 (menu_language_uuid, menu_item_uuid, menu_uuid, menu_language, menu_item_title)
			 values (:id, :i, :m, 'en-us', :t)",
			[
				"id" => uuid(),
				"i" => $r["menu_item_uuid"],
				"m" => $menu_uuid,
				"t" => $title,
			]
		);
		$langs_added++;
	}
}
echo "added $langs_added en-us language rows\n";

// Ensure superadmin on every item
$super = $database->select(
	"select group_uuid from v_groups where group_name = 'superadmin' and domain_uuid is null",
	null,
	"column"
);
$linked = 0;
if ($super) {
	$missing = $database->select(
		"select i.menu_item_uuid, i.menu_item_title
		 from v_menu_items i
		 where i.menu_uuid = :m
		   and not exists (
		     select 1 from v_menu_item_groups g
		     where g.menu_item_uuid = i.menu_item_uuid and g.group_uuid = :g
		   )",
		["m" => $menu_uuid, "g" => $super],
		"all"
	);
	if (is_array($missing)) {
		foreach ($missing as $row) {
			$database->execute(
				"insert into v_menu_item_groups
				 (menu_item_group_uuid, menu_uuid, menu_item_uuid, group_name, group_uuid)
				 values (:id, :m, :i, 'superadmin', :g)",
				[
					"id" => uuid(),
					"m" => $menu_uuid,
					"i" => $row["menu_item_uuid"],
					"g" => $super,
				]
			);
			$linked++;
		}
	}
}
echo "linked $linked items to superadmin\n";

// Show Accounts children after fix
$accounts = $database->select(
	"select menu_item_uuid, menu_item_title from v_menu_items
	 where menu_uuid = :m and uuid = 'bc96d773-ee57-0cdd-c3ac-2d91aba61b55'",
	["m" => $menu_uuid],
	"row"
);
echo "Accounts menu_item_uuid=" . ($accounts["menu_item_uuid"] ?? "MISSING") . "\n";
if (!empty($accounts["menu_item_uuid"])) {
	$kids = $database->select(
		"select c.menu_item_title, c.menu_item_link,
		        (select count(*) from v_menu_languages l where l.menu_item_uuid=c.menu_item_uuid and l.menu_language='en-us') as langs,
		        (select count(*) from v_menu_item_groups g where g.menu_item_uuid=c.menu_item_uuid and g.group_name='superadmin') as groups
		 from v_menu_items c
		 where c.menu_uuid = :m and c.menu_item_parent_uuid = :p
		 order by c.menu_item_title",
		["m" => $menu_uuid, "p" => $accounts["menu_item_uuid"]],
		"all"
	);
	echo "Accounts children:\n";
	if (is_array($kids) && count($kids)) {
		foreach ($kids as $k) {
			echo "  - {$k['menu_item_title']} ({$k['menu_item_link']}) langs={$k['langs']} groups={$k['groups']}\n";
		}
	} else {
		echo "  STILL NONE\n";
	}
}

echo "DONE — logout / private window / login again, then hover Accounts\n";
