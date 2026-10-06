#!/bin/bash
# Test / wire SkyKin fraud alert email (LF only). Run on ecs-cc as root.
set -eu

TO="${1:-solomonetsegenet7@gmail.com}"

echo "===== 1) FusionPBX email settings (if any) ====="
docker exec skykin-db psql -U fusionpbx -d fusionpbx -c "
SELECT default_setting_subcategory, default_setting_name, default_setting_value
FROM v_default_settings
WHERE default_setting_category ILIKE 'email'
ORDER BY 1,2;
" 2>/dev/null || echo "(no email settings query)"

echo
echo "===== 2) PHP mail() test via skykin-web → $TO ====="
docker exec -e TO="$TO" skykin-web php -r '
$to = getenv("TO");
$subj = "[SkyKin] test alert";
$body = "SkyKin fraud test via PHP mail() at ".date("c")."\nHost: ".gethostname()."\n";
$from = "noreply@skykintech.com";
$headers = "From: ".$from."\r\nContent-Type: text/plain; charset=UTF-8";
$ok = @mail($to, $subj, $body, $headers);
echo $ok ? "PHP mail() returned TRUE (may still be dropped if no MTA)\n" : "PHP mail() returned FALSE\n";
'

echo
echo "===== 3) Host MTA check ====="
command -v sendmail >/dev/null && echo "sendmail: $(command -v sendmail)" || echo "sendmail: missing"
command -v postfix >/dev/null && echo "postfix: present" || echo "postfix: missing"
ls /usr/sbin/sendmail 2>/dev/null || true

echo
echo "DONE — check inbox/spam for $TO"
echo "If nothing arrives, we need real SMTP (Gmail app password or company SMTP)."
