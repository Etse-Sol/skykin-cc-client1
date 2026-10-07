<?php
/**
 * Fix agent-to-agent calls on fresh FusionPBX installs:
 * default local_extension bridge lacks WebRTC flags -> bridge fails -> 900_voicemail steals the call.
 *
 * Run inside skykin-web:
 *   php /tmp/skykin_patch_webrtc_dialplan.php
 */
require "/var/www/fusionpbx/resources/require.php";

$database = new database;
$domain_name = getenv("FS_DOMAIN") ?: "client1.skykin.local";
$ext_ip = getenv("EXTERNAL_RTP_IP") ?: getenv("EXTERNAL_SIP_IP") ?: "";
$bridge = "{rtp_secure_media=optional,media_webrtc=true";
if ($ext_ip !== "") {
	$bridge .= ",rtp_advertise_ip={$ext_ip},include_external_ip=true";
}
$bridge .= "}user/\${destination_number}@\${domain_name}";

echo "domain={$domain_name}\n";
echo "bridge={$bridge}\n";

// Ensure default FusionPBX dialplans exist
$cnt = (int) $database->select("select count(*) from v_dialplans", null, "column");
if ($cnt < 10) {
	echo "Running upgrade.php (dialplans sparse: {$cnt})...\n";
	passthru("php /var/www/fusionpbx/core/upgrade/upgrade.php");
}

$rows = $database->select(
	"select dd.dialplan_detail_uuid, dd.dialplan_detail_data, d.dialplan_name, d.dialplan_order
	 from v_dialplan_details dd
	 join v_dialplans d on d.dialplan_uuid = dd.dialplan_uuid
	 where dd.dialplan_detail_type = 'action'
	   and dd.dialplan_detail_data like 'bridge%user/%'
	   and (d.dialplan_name = 'local_extension' or dd.dialplan_detail_tag = 'action')
	 order by d.dialplan_order",
	null,
	"all"
);

$updated = 0;
if (is_array($rows)) {
	foreach ($rows as $row) {
		if (($row["dialplan_name"] ?? "") !== "local_extension") {
			continue;
		}
		if (strpos($row["dialplan_detail_data"] ?? "", "media_webrtc=true") !== false) {
			echo "local_extension already patched\n";
			continue;
		}
		$p = permissions::new();
		$p->add("dialplan_detail_edit", "temp");
		$array = [];
		$array["dialplan_details"][0]["dialplan_detail_uuid"] = $row["dialplan_detail_uuid"];
		$array["dialplan_details"][0]["dialplan_detail_data"] = $bridge;
		$database->save($array);
		$p->delete("dialplan_detail_edit", "temp");
		$updated++;
		echo "patched local_extension bridge\n";
	}
}

// Disable catch-all voicemail dialplan that runs after failed bridge (order 900)
$vm = $database->select(
	"select dialplan_uuid, dialplan_enabled from v_dialplans where dialplan_name = 'voicemail' limit 5",
	null,
	"all"
);
if (is_array($vm)) {
	foreach ($vm as $row) {
		if (($row["dialplan_enabled"] ?? "") === "false") {
			continue;
		}
		$p = permissions::new();
		$p->add("dialplan_edit", "temp");
		$array = [];
		$array["dialplans"][0]["dialplan_uuid"] = $row["dialplan_uuid"];
		$array["dialplans"][0]["dialplan_enabled"] = "false";
		$database->save($array);
		$p->delete("dialplan_edit", "temp");
		echo "disabled dialplan voicemail uuid={$row['dialplan_uuid']}\n";
	}
}

if ($updated === 0 && !is_array($rows)) {
	echo "WARNING: local_extension bridge row not found — check Dialplan Manager\n";
}

// Reload FS dialplan cache
passthru("php /var/www/fusionpbx/core/upgrade/upgrade.php 2>/dev/null");
echo "DONE — retry 101 -> 102 call\n";
