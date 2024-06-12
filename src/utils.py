import subprocess

def exec_cmd(cmd, env=None):
    print(cmd)
    p = subprocess.run(cmd, capture_output=True, shell=True, text=True, env=env)
    return p.stdout
