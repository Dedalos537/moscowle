"""Deploy frontend build to cPanel via FTP.

Usage:
    python scripts/deploy_frontend.py

Alternative: push to main branch of Dedalos537/moscowle_ia
with changes under edysync/ to trigger GitHub Actions workflow.
"""
import ftplib
import os

FTP_HOST = "ftp.centrojuanpabloii.com"
FTP_USER = "centroju"
FTP_PASS = "+LC6OXpm0dq6@4"
REMOTE_DIR = "/public_html/moscowle"
LOCAL_DIR = "edysync/dist/edysync/browser"


def upload_dir(ftp, local, remote):
    ftp.cwd("/")
    for root, dirs, files in os.walk(local):
        rel = os.path.relpath(root, local)
        rem = os.path.join(remote, rel).replace("\\", "/") if rel != "." else remote
        ftp.cwd("/")
        for part in rem.split("/"):
            if not part:
                continue
            try:
                ftp.cwd(part)
            except:
                ftp.mkd(part)
                ftp.cwd(part)
        for f in files:
            local_path = os.path.join(root, f)
            remote_path = os.path.join(rem, f).replace("\\", "/")
            try:
                with open(local_path, "rb") as fh:
                    ftp.storbinary(f"STOR {remote_path}", fh)
                print(f"  OK  {remote_path}")
            except Exception as e:
                print(f"  FAIL {remote_path}: {e}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_dir = os.path.join(script_dir, LOCAL_DIR)

    print(f"Connecting to {FTP_HOST}...")
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    print("Uploading...")
    upload_dir(ftp, local_dir, REMOTE_DIR)
    ftp.quit()
    print("Done!")
