#! python3
"""
@Description 	:   PPP-RTK processing/plotting library for POS/TRO/IONO
@Author      	:   Lewen Zhao
@Version     	:   1.0
@Contact     	:   lwzhao@nuist.edu.cn
@Contact     	:   navsense_support@163.com
@OnlineService :	http://1.13.180.60:8800/login2
@Time        	:   2024/03/29 12:14:41
"""
from datetime import datetime
import os
import shutil
import platform
from dateutil.relativedelta import relativedelta

if platform.system() == "Linux":
    tools = {
        "wget": "sudo apt install wget  # For Debian/Ubuntu\nsudo yum install wget  # For CentOS/RHEL",
        "curl": "sudo apt install curl  # For Debian/Ubuntu\nsudo yum install curl  # For CentOS/RHEL",
        "gzip": "sudo apt install gzip  # For Debian/Ubuntu\nsudo yum install gzip  # For CentOS/RHEL"
    }

    for tool, install_cmd in tools.items():
        tool_path = shutil.which(tool)
        if tool_path:
            print(f"{tool} found: {tool_path}")
        else:
            print(f"Error: {tool} not found.")
            print(f"To install it, run:\n{install_cmd}")

    # 打印所有工具检测结果
    print("\nEnvironment check completed.")

else:
    print("Please check the existance of the download exe file.")

currentpath = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(currentpath)

if platform.system() == "Linux":
    bin_wget = shutil.which("wget") or "wget"
    bin_curl = shutil.which("curl") or "curl"
    bin_gzip = shutil.which("gzip") or "gzip"
    bin_crx=""
    bin_gfzrnx=""
else:
    bin_wget = os.path.join(root_path, "bin", "wget")
    bin_curl = os.path.join(root_path, "bin", "curl")
    bin_gzip = os.path.join(root_path, "bin", "gzip")
    bin_crx = os.path.join(root_path, "bin", "crx2rnx")
    bin_gfzrnx = os.path.join(root_path, "bin", "gfzrnx_x64")


def ymd2doy(year, mon, day):
    dn = datetime(year, mon, day, 0, 0, 0)
    return int(dn.strftime("%j"))

def call_wget_(dir_dst, url):
    if not os.path.exists(dir_dst):
        os.makedirs(dir_dst)
    cmd = '%s  -P %s %s' % (bin_wget,dir_dst, url)
    print (cmd)
    os.system(cmd)

def call_curl_(dir_dst, url):
    if not os.path.exists(dir_dst):
        os.makedirs(dir_dst)
    os.chdir(dir_dst)
    cmd = '%s  -s -S -c .cookie -n -L -O %s' % (bin_curl,url)
    print ("curl cmd="+cmd)
    os.system(cmd)
def download_compress(rpath,local_dir,name,suffix):
    compressed_name = name + suffix
    local_file_path = os.path.join(local_dir, name)
    local_compressed_file_path = os.path.join(local_dir, compressed_name)
    
    if os.path.exists(local_file_path):
        print(f"File {name} already exists.")
        return local_file_path
    if os.path.exists(local_compressed_file_path):
        os.remove(local_compressed_file_path)
        print(f"Compressed file {compressed_name} found and deleted.")
    
    # call_wget_(dir_dst, obsfs)
    remote_path=f"{rpath}{compressed_name}"
    call_curl_(local_dir, remote_path)    
    if os.path.exists(local_compressed_file_path):
        cmd='%s -d %s' %(bin_gzip,local_compressed_file_path)
        os.system(cmd)
    return local_file_path