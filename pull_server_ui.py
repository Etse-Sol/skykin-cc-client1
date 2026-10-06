import os
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REMOTE = "/opt/call-center-deployement/call-center/app/agent_dashboard"
LOCAL = r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard"
SKIP = {
    "skykin_local.db",
    "sipjs.bundle.js",
    "skykin_local_config.php.example",
}

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "196.189.236.140",
    username="root",
    password="Pass@1234",
    timeout=25,
    allow_agent=False,
    look_for_keys=False,
)
sftp = c.open_sftp()


def walk(remote_dir, rel=""):
    for attr in sftp.listdir_attr(remote_dir):
        name = attr.filename
        if name.endswith(".bak") or ".bak-" in name or name in SKIP:
            continue
        rpath = remote_dir + "/" + name
        lrel = os.path.join(rel, name) if rel else name
        mode = attr.st_mode
        if mode & 0o40000:
            walk(rpath, lrel)
        else:
            yield rpath, lrel, attr.st_size


os.makedirs(LOCAL, exist_ok=True)
for rpath, lrel, size in walk(REMOTE):
    if lrel.replace("\\", "/").endswith("js/sipjs.bundle.js"):
        continue
    lpath = os.path.join(LOCAL, lrel)
    os.makedirs(os.path.dirname(lpath), exist_ok=True)
    sftp.get(rpath, lpath)
    print("pulled", lrel, size)

sftp.close()
c.close()
print("done")
