import os
import subprocess
import sys

TARGET_DIRS = [
    r"Project\Content\ScriptBytecode\MOBILE",
    r"Project\Content\ScriptBytecode\PC"
]

def run_p4(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    
def get_file_changelist(file_path):
    cmd = f'p4 -Ztag opened "{file_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    for line in result.stdout.splitlines():
        if line.startswith("... change"):
            return line.split()[-1]
    return None

## 添加文件到 Perforce
def add_file_to_p4(cl_num, file_path):
    p4_add_result = run_p4(f'p4 add -c {cl_num} "{file_path}"')
    if not p4_add_result:
        print(f"!!!!!!!! [Error] Failed to p4 add {file_path}, result: [{p4_add_result}]")
        return False
    
    add_results = p4_add_result.split('-')
    add_result = add_results[1]
    add_path_result = add_results[0]
    if add_result == " opened for add":
        print(f"[ADD OK] p4 add result for {add_path_result}: [{add_result}]")
        return True

    print(f"[Warning] p4 add result for {add_path_result}: [{add_result}]")
    return False

## 将文件从一个 CL 挪到目标 CL
def reopen_file_to_cl(file_path, cur_cl_num, target_cl):
    p4_reopen_result = run_p4(f'p4 reopen -c {target_cl} "{file_path}"')
    if not p4_reopen_result:
        print(f"!!!!!!!! [Error] Failed to p4 reopen {file_path} from CL {cur_cl_num} to CL {target_cl}, result: [{p4_reopen_result}]")
        return False
    
    reopen_result = p4_reopen_result.split('-')[1]
    print(f"[REOPEN OK] p4 reopen result for {file_path} from CL {cur_cl_num} to CL {target_cl}: [{reopen_result}]")
    return True

def main():
    if len(sys.argv) < 2:
        print("Error: Missing Changelist ID.")
        sys.exit(1)

    ## 获取 CL ID
    cl_num = sys.argv[1]

    ## 获取是否要允许挪到目标 CL, 如果没有参数则默认为 False
    allow_reopen = False
    if len(sys.argv) >= 3:
        allow_reopen = sys.argv[2].lower() == 'true'

    targetDirs = [os.path.abspath(dir) for dir in TARGET_DIRS]

    print(f"--- WORKING DIR: {os.getcwd()} ---")
    print(f"--- MOBILE PATH: {targetDirs[0]} ---")
    print(f"--- PC PATH: {targetDirs[1]} ---")
    print(f"--- Processing CL: {cl_num} ---")

    luaDepots = run_p4(f"p4 opened -c {cl_num}")
    if not luaDepots:
        print("No files in this CL.")
        return

    print("--- Processing Files ---")
    for lua_depot in luaDepots.split('\n'):
        fileInfo = os.path.basename(lua_depot)
        lua_file_name = fileInfo.split('#')[0]
        if not lua_file_name.endswith('.lua'):
            continue

        luac_file_name = lua_file_name + 'c'
        print(f"--------------------")
        print(f"--- Start. {lua_file_name} ---")
        
        for targetDir in targetDirs:
            luac_path = os.path.join(targetDir, luac_file_name)
            if os.path.isfile(luac_path):
                p4_edit_result = run_p4(f'p4 edit -c {cl_num} "{luac_path}"')
                if not p4_edit_result:
                    add_file_to_p4(cl_num, luac_path)
                    continue

                edit_results = p4_edit_result.split('-')
                edit_result = edit_results[1]
                edit_path_result = edit_results[0]
                if edit_result == " opened for edit":
                    print(f"[OPENED OK] p4 edit result for {edit_path_result}: [{edit_result}]")
                    continue

                cur_cl_num = get_file_changelist(luac_path)
                if cur_cl_num == cl_num:
                    print(f"[Warning] p4 edit result for {edit_path_result}: [{edit_result}]")
                    continue

                if allow_reopen and cur_cl_num != cl_num:
                    if reopen_file_to_cl(luac_path, cur_cl_num, cl_num):
                        continue

                print(f"!!!!!!!! [Error] p4 edit result for {edit_path_result}: [{edit_result}], current CL: {cur_cl_num}")

        print(f"--- End. {lua_file_name} ---")
        print(f"--------------------")

    print("--------------------")

if __name__ == "__main__":
    main()