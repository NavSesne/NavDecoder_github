"""
 static test for PPP (BeiDou PPP)
"""
from binascii import unhexlify
from copy import deepcopy
import numpy as np
import  os

from B2b_HAS_decoder.gnss import *
from B2b_HAS_decoder.peph import peph
from B2b_HAS_decoder.cssr_bds_um982 import cssr_bdsC
from B2b_HAS_decoder.rinex import rnxdec
from B2b_HAS_decoder.cssrlib import sCSSR, sCType, local_corr
from datetime import datetime, timedelta
from download.down_PPP_products import *
from copy import deepcopy
from B2b_UM980_decoder.ext124 import extract_all_pppb2binfo_content


class B2BData:
    def __init__(self):
        self.init_empty()

    def init_empty(self):
        self.cssrmode = None
        self.sat_n = []
        self.iodssr = None
        self.iodssr_c = {}
        self.lc = []
        self.nav_mode = {}
        self.subtype = None

    def update_value_from(self, source_object):
        self.cssrmode = getattr(source_object, 'cssrmode', None)
        self.sat_n = deepcopy(getattr(source_object, 'sat_n', []))
        self.iodssr = getattr(source_object, 'iodssr', None)
        self.iodssr_c = deepcopy(getattr(source_object, 'iodssr_c', []))
        self.nav_mode = deepcopy(getattr(source_object, 'nav_mode', []))
        self.subtype = getattr(source_object, 'subtype', None)
        # self.lc = deepcopy(getattr(source_object, 'lc', []))

        if len(self.lc) == 0:
            self.lc.append(local_corr())
            inet = 0
            self.lc[inet].dclk = {}
            self.lc[inet].dorb = {}
            self.lc[inet].iode = {}
            self.lc[inet].iodc = {}
            self.lc[inet].iodc_c = {}
            self.lc[inet].cbias = {}
            self.lc[inet].t0 = {}
        # self.lc[0].iode=source_object.lc[0].iode
        self.lc[0].iode = deepcopy(getattr(source_object.lc[0], 'iode', {}))
        for j, sat in enumerate(source_object.sat_n):
            if source_object.iodssr >= 0 and source_object.iodssr_c[sCType.ORBIT] == source_object.iodssr:
                if sat not in source_object.sat_n:
                    continue
            if sat not in source_object.lc[0].iode.keys():
                continue
            if source_object.lc[0].dorb[sat] is None:
                continue
            if sat not in self.lc[0].t0:
                self.lc[0].t0[sat] = {}
            if source_object.lc[0].iodc[sat] == source_object.lc[0].iodc_c[sat]:
                self.lc[0].iode[sat] = deepcopy(source_object.lc[0].iode[sat])
                self.lc[0].dorb[sat] = deepcopy(source_object.lc[0].dorb[sat])
                self.lc[0].iodc[sat] = deepcopy(source_object.lc[0].iodc[sat])
                self.lc[0].t0[sat][sCType.ORBIT] = deepcopy(source_object.lc[0].t0[sat][sCType.ORBIT])

                self.lc[0].dclk[sat] = deepcopy(source_object.lc[0].dclk[sat])
                self.lc[0].iodc_c[sat] = deepcopy(source_object.lc[0].iodc_c[sat])
                self.lc[0].t0[sat][sCType.CLOCK] = deepcopy(source_object.lc[0].t0[sat][sCType.CLOCK])
            else:
                self.lc[0].iode[sat] = deepcopy(source_object.lc[0].iode[sat])
                self.lc[0].dorb[sat] = deepcopy(source_object.lc[0].dorb[sat])
                self.lc[0].iodc[sat] = deepcopy(source_object.lc[0].iodc[sat])
                self.lc[0].t0[sat][sCType.ORBIT] = deepcopy(source_object.lc[0].t0[sat][sCType.ORBIT])

    def deletePRN(self, sat):
        self.lc[0].iode[sat] = 0
        self.lc[0].dorb[sat] = []
        self.lc[0].iodc[sat] = 0
        self.lc[0].t0[sat][sCType.ORBIT] = None

        self.lc[0].dclk[sat] = np.nan
        self.lc[0].iodc_c[sat] = 0
        self.lc[0].t0[sat][sCType.CLOCK] = None


def read_um982_b2b_info(file_bds):
    output_file_path = file_bds+"_b2b"  #Save the decoded files
    extract_all_pppb2binfo_content(file_bds, output_file_path)

    # 定义数据类型
    dtype1 = [
        ('week', 'i4'), ('tow', 'i4'), ('prn', 'i4'), ('iodssr', 'i4'), ('iodp', 'i4'),
        ('tod', 'i4'), ('BDS', 'U63'), ('GPS', 'U37'), ('Galileo', 'U37'), ('GLONASS', 'U37')
    ]

    dtype2 = [
        ('week', 'i4'), ('tow', 'i4'), ('prn', 'i4'), ('iodssr', 'i4'), ('iodp', 'i4'),
        ('tod', 'i4'), ('satslot', 'i4', (6,)), ('iodn', 'i4', (6,)), ('Rorb', 'f8', (6,)),
        ('Aorb', 'f8', (6,)), ('Corb', 'f8', (6,)), ('iodcorr', 'i4', (6,)), ('URAI', 'U2', (6,))
    ]

    dtype4 = [
        ('week', 'i4'), ('tow', 'i4'), ('prn', 'i4'), ('sub', 'i4'), ('iodssr', 'i4'), ('iodp', 'i4'),
        ('tod', 'i4'), ('iodcorr', 'i4', (23,)), ('sc0', 'f8', (23,))
    ]

    # 数据列表初始化为空
    data1, data2, data4 = [], [], []
    v_all = []

    with open(output_file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(' ')
            msg_type = int(parts[0])

            if msg_type == 1:
                # Process bdsmsg1 type messages
                week, tow, prn, iodssr, iodp, tod = map(int, [part.split(':')[1] for part in parts[1:7]])
                BDS, GPS, Galileo, GLONASS = [part.split(':')[1] for part in parts[7:]]
                data1.append((week, tow, prn, iodssr, iodp, tod, BDS, GPS, Galileo, GLONASS))
                v_all.append(np.array([data1[-1]], dtype=dtype1))

            elif msg_type == 2:
                # Process bdsmsg2 type messages
                week, tow, prn, iodssr, iodp, tod = map(int, [part.split(':')[1] for part in parts[1:7]])
                pairs = parts[7:]
                satslot, iodn, Rorb, Aorb, Corb, iodcorr, URAI = [], [], [], [], [], [], []
                for i in range(0, len(pairs), 7):
                    satslot.append(int(pairs[i].split(':')[1]))
                    iodn.append(int(pairs[i + 1].split(':')[1]))
                    Rorb.append(float(pairs[i + 2].split(':')[1]))
                    Aorb.append(float(pairs[i + 3].split(':')[1]))
                    Corb.append(float(pairs[i + 4].split(':')[1]))
                    iodcorr.append(int(pairs[i + 5].split(':')[1]))
                    URAI.append(pairs[i + 6].split(':')[1])
                data2.append((week, tow, prn, iodssr, iodp, tod, satslot, iodn, Rorb, Aorb, Corb, iodcorr, URAI))
                v_all.append(np.array([data2[-1]], dtype=dtype2))
            elif msg_type == 4:
                # Process bdsmsg4 type messages
                week, tow, prn, sub, iodssr, iodp, tod = map(int, [part.split(':')[1] for part in parts[1:8]])
                iodcorr_sc0_pairs = parts[8:]
                iodcorr = []
                sc0 = []
                for i in range(0, len(iodcorr_sc0_pairs), 2):
                    iodcorr.append(int(iodcorr_sc0_pairs[i].split(':')[1]))
                    sc0.append(float(iodcorr_sc0_pairs[i + 1].split(':')[1]))
                data4.append((week, tow, prn, sub, iodssr, iodp, tod, iodcorr, sc0))
                v_all.append(np.array([data4[-1]], dtype=dtype4))

    return v_all

def relative_to_absolute(relative_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, relative_path)

# Start for the configuration
max_orbit_delay=300
max_clock_delay=30
start_date = datetime(2024, 4, 15)
process_days = 1
file_bds_template = r'test_data\log_UM982_{}_00.txt'
nav_file_template = r'test_data\eph\BRD400DLR_S_{}0000_01D_MN.rnx'
corr_dir_template = r'test_data\UM982{}_B2BRTCM'
#End for the configuration
B2b_BDS = relative_to_absolute(file_bds_template)
nav_BDS = relative_to_absolute(nav_file_template)
sol_BDS = relative_to_absolute(corr_dir_template)

for i in range(process_days):
    current_date = start_date + timedelta(days=i)
    previous_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    ep = [current_date.year, current_date.month, current_date.day,
                  current_date.hour, current_date.minute, current_date.second]
    doy = current_date.timetuple().tm_yday
    year = current_date.year
    formatted_date = f"{year}{str(doy).zfill(3)}" 
    down_NAV_data(previous_date,3,os.path.dirname(nav_BDS))
    obs_date = f"{year}{str(current_date.month).zfill(2)}{str(current_date.day).zfill(2)}"
    file_bds = B2b_BDS.format(obs_date)
    nav_file = nav_BDS.format(formatted_date)

    # generate the output file
    corr_dir = sol_BDS.format(formatted_date)
    parent_dir = os.path.dirname(corr_dir)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    print("=============Saving sp3/ssr/log to dir: " + corr_dir)
    file_sp3 = corr_dir + '.sp3'
    file_ssr = corr_dir + '.ssr'
    file_log = corr_dir + '.log'
    cs = cssr_bdsC(file_log)
    cs.monlevel = 2
    prn_ref = 59  # satellite PRN to receive BDS PPP collection

    time = epoch2time(ep)
    current_time = time
    week, tow = time2gpst(time)
    doy = time2doy(time)
    cs.week = week
    cs.tow0 = tow // 86400 * 86400
    #Read UM982 corrections from the file
    v = read_um982_b2b_info(file_bds)
    # Read UM982 corrections from the TCP or serial
    # To be implemented

    rnx = rnxdec()
    nav = Nav()
    orb = peph()
    nav = rnx.decode_nav(nav_file, nav)
    nav_out = Nav()
    sp_out = peph()

    record_orbit_update_time = None
    record_clock_update_time = None
    orbit_data = {}
    clock_data = {}
    B2BData0 = B2BData()
    delay = 0
    for row in v:
        # if row['tow']>=tow or row['tow']<tow-120:
        #     continue
        # print(row)
        # corr_str = np.array2string(row, separator=', ')
        # cs.log_msg(corr_str)
        buff = row
        cs.decode_cssr(buff)
        intervals = 5
        # if (cs.lc[0].cstat & 0xf) == 0xf:
        if True:
            if cs.subtype == sCSSR.CLOCK:
                if record_clock_update_time is None:
                    record_clock_update_time = cs.time
                time_clock_sat = cs.time
                str_obs1 = time2str(time_clock_sat)
                str_obs2 = time2str(record_clock_update_time)
                time_test = epoch2time([2023, 12, 3, 0, 1, 55])
                if timediff(time_clock_sat,
                            record_clock_update_time) >= 1: 
                    str_obs = time2str(current_time)
                    if abs(timediff(current_time, time_test)) < 1:
                        print(time2str(time_test))
                    while timediff(current_time, time_clock_sat) < 0:
                        time_corr = timeadd(current_time, -delay)
                        debug_obs = time2str(current_time)
                        if timediff(time_corr, record_clock_update_time) < 0:
                            current_time = timeadd(time_corr, intervals)
                            continue
                        if timediff(time_corr, record_clock_update_time) > max_clock_delay:
                            cs.log_msg(">>>>ERROR: large clock difference[obst-clkt] : " + time2str(
                                time_corr) + " " + time2str(record_clock_update_time))
                            current_time = timeadd(time_corr, intervals)
                            continue
                        if timediff(time_corr, record_orbit_update_time) < 0 or timediff(time_corr,
                                                                                         record_orbit_update_time) > max_orbit_delay:
                            cs.log_msg(">>>>ERROR: large orbit difference [obst-orbt]: " + time2str(
                                time_corr) + " " + time2str(record_orbit_update_time))
                            current_time = timeadd(time_corr, intervals)
                            continue
                        cs.encode_SP3(B2BData0, orb, nav, current_time, record_clock_update_time, sp_out, nav_out,
                                      file_ssr)
                        current_time = timeadd(time_corr, intervals)
                    record_clock_update_time = time_clock_sat
                else:
                    B2BData0.update_value_from(cs)

            if cs.subtype == sCSSR.ORBIT:
                if record_orbit_update_time is None:
                    record_orbit_update_time = cs.time
                time_orbit_sat = cs.time
                if abs(timediff(time_orbit_sat, record_orbit_update_time)) > 1:
                    record_orbit_update_time = time_orbit_sat
                    B2BData0.update_value_from(cs)

    sp_out.write_sp3(file_sp3, nav_out)
