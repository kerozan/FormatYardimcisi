import subprocess

with open("test_pnputil_output.txt", "wb") as f:
    result = subprocess.run(["pnputil", "/enum-drivers"], capture_output=True)
    f.write(result.stdout)
