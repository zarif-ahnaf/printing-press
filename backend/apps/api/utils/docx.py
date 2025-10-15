from pathlib import Path
import subprocess
import shutil


LOEXE = shutil.which("soffice")


def doc2pdf(filein: Path):
    if not LOEXE:
        raise EnvironmentError("LibreOffice not found")

    cmd = [LOEXE, "--convert-to", "pdf", "--outdir", str(filein.parent), str(filein)]

    subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
