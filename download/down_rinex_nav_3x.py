#! python3
"""
@Description 	:   PPP-RTK processing/plotting library for POS/TRO/IONO
@Author      	:   Lewen Zhao
@Version     	:   1.0
@Contact     	:   navsense_support@163.com
@OnlineService :	http://1.13.180.60:8800/login2
@Time        	:   2024/03/20 23:47:21
"""

from dateutil.relativedelta import relativedelta
from down_tools import *

def wget_rinex3(tmn,local_dir):
    doy  = ymd2doy(tmn.year, tmn.month, tmn.day)
    yy = tmn.year-2000 if tmn.year>=2000 else tmn.year-1900
    
    # GOP broadcast center 
    # name = 'BRDC00GOP_R_%4d%03d0000_01D_MN.rnx' % (tmn.year, doy)
    # rpath = 'ftp://ftp.pecny.cz/LDC/orbits_brd/gop3/%d/' % (tmn.year)
    
    # IGN broadcast center
    # name = 'BRDC00IGN_R_%4d%03d0000_01D_MN.rnx' % (tmn.year, doy)
    # rpath = 'ftp://igs.ign.fr/pub/igs/data/%04d/%03d/' % (tmn.year,doy)

    #WHU broadcast center
    name = 'BRDC00IGS_R_%4d%03d0000_01D_MN.rnx' % (tmn.year, doy)
    rpath = 'ftp://igs.gnsswhu.cn/pub/gps/data/daily/%04d/%03d/%2dp/' % (tmn.year,doy,yy)

    download_compress(rpath,local_dir,name,'.gz')

        
if __name__ == "__main__":
    tstart = datetime(2024,  8,  5, 0, 0, 0)
    tlen=2
    dir_dst = r'D:\dataset_rtk\navcm_test'
    tmn=tstart
    for day in range(tlen):
        wget_rinex3(tmn,dir_dst)
        tmn = tmn + relativedelta(days=1)
