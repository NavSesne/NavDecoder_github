#! python3
#coding:utf-8
"""
@Description 	:   PPP-RTK processing/plotting library for POS/TRO/IONO
@Author      	:   Lewen Zhao
@Version     	:   1.0
@Contact     	:   lwzhao@nuist.edu.cn
@Contact     	:   navsense_support@163.com
@OnlineService :	http://1.13.180.60:8800/login2
@Time        	:   2024/03/29 12:13:18
"""

import datetime,os
from dateutil.relativedelta import relativedelta
from down_tools import *
from rtkcmn import *
from concurrent.futures import ThreadPoolExecutor, as_completed
URL_IGN = "ftp://igs.ign.fr/pub/igs/products/mgex/"
URL_WHU = "ftp://igs.gnsswhu.cn/pub/gnss/products/mgex/"
URL_Default = URL_WHU
URL_CNT = "http://www.ppp-wizard.net/products/REAL_TIME/"
prd_enum_set = {"IGS", "GRM", "COM", "WUM", "GFR", "WHR", "CNT"}
# Generate the filename and download URL based on the center and time tmn
def generate_filenames_and_url(center, tmn):
    # Check if the center is valid
    if center not in prd_enum_set:
        raise ValueError(f"Center '{center}' is not recognized. Please use one of the following: {', '.join(prd_enum_set)}")
    year= tmn.year  
    time0=epoch2time([tmn.year, tmn.month, tmn.day, tmn.hour, tmn.minute, tmn.second])
    week,dow=time2gpst(time0)
    doy=time2doy(time0)
    ephf_name = clkf_name = biaf_name = attf_name = suffix=""
    download_url = ""
    current_date = datetime.now()
    ddays = (current_date - tmn).days
    dataNRT,dataRAP,dataFIN=False,False,False
    default=None
    if ddays<=2:
        dataNRT=True
    elif 2<ddays and ddays<7:  #Rapied products
        dataNRT=True
        dataRAP=True
    elif ddays>=7: #Final products
        dataNRT=True
        dataRAP=True
        dataFIN=True
    if dataNRT or dataRAP or dataFIN: #Real-time prodcuts from B2b and HAS
        if center == "B2B" or center == "HAS":
            print("Download real-time archive of PPP-B2b and Galileo HAS products")
        if center == "WHR":
            ephf_name = f"WUM0MGXRTS_{year}{doy:03d}0000_01D_05M_ORB.SP3"
            clkf_name = f"WUM0MGXRTS_{year}{doy:03d}0000_01D_05S_CLK.CLK"
            biaf_name = f"WUM0MGXRTS_{year}{doy:03d}0000_01D_05M_OSB.BIA"
            attf_name=""
            URL_WHU="ftp://igs.gnsswhu.cn/pub/whu/phasebias/"
            download_url = f"{URL_WHU}{year}/"
            suffix='.gz'
        elif center=="WUM" or (dataNRT==True and dataRAP==False and dataFIN==False):
            t_NRT=tmn+relativedelta(days=-1) # the orbit and clock in the file starts one-day ago
            time0=epoch2time([t_NRT.year, t_NRT.month, t_NRT.day, t_NRT.hour, t_NRT.minute, t_NRT.second])
            week0,dow0=time2gpst(time0)
            doy0=time2doy(time0)
            ephf_name = f"WUM0MGXNRT_{year}{doy0:03d}{t_NRT.hour:02d}00_02D_05M_ORB.SP3"
            attf_name = f"WUM0MGXNRT_{year}{doy0:03d}{t_NRT.hour:02d}00_02D_30S_ATT.OBX"
            clkf_name = f"WUM0MGXNRT_{year}{doy0:03d}{t_NRT.hour:02d}00_02D_30S_CLK.CLK"
            biaf_name = f"WUM0MGXNRT_{year}{doy0:03d}0000_01D_01D_OSB.BIA"
            download_url = f"{URL_Default}{week0}/"
            suffix='.gz'
            if (dataNRT==True and dataRAP==False and dataFIN==False):
                print(f"Specificted products not found, {center}==>WUM_NRT")

    if dataRAP or dataFIN:  #Rapied products
        if center == "GFR":
            ephf_name = f"GFZ0MGXRAP_{year}{doy:03d}0000_01D_05M_ORB.SP3"
            clkf_name = f"GFZ0MGXRAP_{year}{doy:03d}0000_01D_30S_CLK.CLK"
            download_url = f"{URL_Default}{week}/"
            suffix='.gz'
        elif center == "CNT":
            ephf_name = f"cnt{week}{dow}.sp3"
            clkf_name = f"cnt{week}{dow}.clk"
            biaf_name = f"cnt{week}{dow}.bia"
            URL_CNT ="http://www.ppp-wizard.net/products/REAL_TIME/"
            download_url = URL_CNT
            suffix='.gz'        
        elif center == "WHR" or (dataRAP==True and dataFIN==False):
            ephf_name = f"WUM0MGXRAP_{year}{doy:03d}0000_01D_05M_ORB.SP3"
            clkf_name = f"WUM0MGXRAP_{year}{doy:03d}0000_01D_30S_CLK.CLK"
            biaf_name = f"WUM0MGXRAP_{year}{doy:03d}0000_01D_01D_OSB.BIA"
            attf_name = f"WUM0MGXRAP_{year}{doy:03d}0000_01D_30S_ATT.OBX"
            URL_WHU="ftp://igs.gnsswhu.cn/pub/whu/phasebias/"
            download_url = f"{URL_WHU}{year}/"
            suffix='.gz'
            if (dataRAP==True and dataFIN==False):
                print(f"Specificted products not found, {center}==>WHR")

    if dataFIN: #Final products
        if center == "GRM":
            ephf_name = f"GRG0MGXFIN_{year}{doy:03d}0000_01D_05M_ORB.SP3"
            clkf_name = f"GRG0MGXFIN_{year}{doy:03d}0000_01D_30S_CLK.CLK"
            biaf_name = f"GRG0MGXFIN_{year}{doy:03d}0000_01D_30S_OSB.BIA"
            download_url = f"{URL_Default}{week}/"
            suffix='.gz'
        elif center == "IGS":
            ephf_name = f"igs{year}{doy:03d}.sp3"
            clkf_name = f"igs{year}{doy:03d}.clk_30s"
            URL_IGS ="ftp://igs.gnsswhu.cn/pub/gps/products/"
            download_url = f"{URL_IGS}{week}/"
            suffix='.Z'
        elif center == "WUM" :
            ephf_name = f"WUM0MGXFIN_{year}{doy:03d}0000_01D_05M_ORB.SP3"
            attf_name = f"WUM0MGXFIN_{year}{doy:03d}0000_01D_30S_ATT.OBX"
            clkf_name = f"WUM0MGXFIN_{year}{doy:03d}0000_01D_30S_CLK.CLK"
            biaf_name = f"WUM0MGXFIN_{year}{doy:03d}0000_01D_30S_OSB.BIA"
            download_url = f"{URL_Default}{week}/"
            suffix='.gz'

    return ephf_name, clkf_name, biaf_name, attf_name, download_url,suffix

def wget_eph_clk(tmn,local_dir,center):
    ephf_name, clkf_name, biaf_name, attf_name, remote_path,suffix = generate_filenames_and_url(center, tmn)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    if ephf_name:
        download_url=remote_path
        if "whu/phasebias"in download_url:
            download_url = f"{download_url}orbit/"
        download_compress(download_url,local_dir, ephf_name,suffix)
    if attf_name:
        download_url=remote_path
        if "whu/phasebias"in download_url:
            download_url = f"{download_url}orbit/"
        download_compress(download_url,local_dir, attf_name,suffix)
    if clkf_name:
        download_url=remote_path
        if "whu/phasebias"in download_url:
            download_url = f"{download_url}clock/"
        download_compress(download_url,local_dir, clkf_name,suffix)
    if biaf_name:
        download_url=remote_path
        if "whu/phasebias"in download_url:
            download_url = f"{download_url}bias/"
        download_compress(download_url,local_dir, biaf_name,suffix)

if __name__ == "__main__":
    tstart = datetime(2024, 5, 1, 0, 0, 0)
    tlen=120
    dir_dst = r'E:\MGEX_Data\eph'
    tmn=tstart

    max_workers = 5  # Adjust the maximum number of worker threads as needed
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for day in range(tlen):
            future = executor.submit(wget_eph_clk, tmn, dir_dst, "WUM")
            futures.append(future)
            tmn = tmn + relativedelta(days=1)

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred during the download task: {e}")                
    print("All download tasks are complete!")