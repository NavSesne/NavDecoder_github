"""
Galileo HAS correction data decoder

[1] Galileo High Accuracy Service Signal-in-Space
  Interface Control Document (HAS SIS ICD), Issue 1.0, May 2022

"""

import numpy as np
import bitstruct as bs
import galois
from B2b_HAS_decoder.cssrlib import cssr, sCSSR, sCSSRTYPE
from B2b_HAS_decoder.peph import peph,peph_t
from B2b_HAS_decoder.gnss import *
from B2b_HAS_decoder.ephemeris import eph2pos, findeph,eph2rel
from B2b_HAS_decoder.cssrlib import cssr, sCSSR, sCSSRTYPE, sCType

class cssr_has(cssr):
    def __init__(self, foutname=None):  # Initialize attributes
        super().__init__(foutname)
        self.MAXNET = 1
        self.cssrmode = sCSSRTYPE.GAL_HAS_SIS
        self.dorb_scl = [0.0025, 0.0080, 0.0080]
        self.dclk_scl = 0.0025
        self.dorb_blen = [13, 12, 12]
        self.dclk_blen = 13
        self.cb_blen = 11
        self.cb_scl = 0.02
        self.pb_blen = 11
        self.pb_scl = 0.01  # cycles

        self.GF = galois.GF(256)

    """
    Calculate the signed value for a given n-bit integer
    u: Input n-bit integer value.
    n: Number of bits in the integer.
    scl: Scaling factor for scaling the integer value.
    """
    def sval(self, u, n, scl):
        """ calculate signed value based on n-bit int, lsb """
        invalid = -2 ** (n - 1)
        dnu = 2 ** (n - 1) - 1
        y = np.nan if u == invalid or u == dnu else u * scl
        return y

    '''The Clock message provides clock corrections for all satellites specified in the Mask block. 
     This means that for each satellite in the Mask, there is a clock correction value. 
     The Clock Subset message, on the other hand, provides clock corrections for only a subset of satellites. 
     This subset is specified by an additional subset mask in the Clock Subset Corrections Block, 
     which indicates which satellites are included in this subset. 
     This allows updating clock corrections for only a portion of satellites when needed, rather than for all satellites.'''

    def decode_cssr_clk_sub(self, msg, i=0):
        head, i = self.decode_head(msg, i)  # Call the decode_head function to decode the iodssr
        self.flg_net = False
        if self.iodssr != head['iodssr']:  # Check if the iodssr field in the message header matches the stored iodssr in the object
            return -1

        nclk_sub = bs.unpack_from('u4', msg, i)[0]  # Unpack a 4-byte unsigned integer from the byte stream starting at i to get the clock subset type
        i += 4
        for j in range(nclk_sub):
            gnss, dcm = bs.unpack_from('u4u2', msg, i)  # Unpack gnss (GPS, Galileo) and dcm (Delta Clock Multipliers) values
            # These values are the parameters for the full clock correction block in the HAS message. 
            # It indicates the multipliers for clock corrections for different GNSS.
            i += 6
            idx_s = np.where(np.array(self.gnss_n) == gnss)  # Find the index of gnss in self.gnss_n
            mask_s = bs.unpack_from('u' + str(self.nsat_g[gnss]), msg, i)[0]  # Decode the satellite mask from the byte stream
            i += self.nsat_g[gnss]  # Move to the next satellite
            idx, nclk = self.decode_mask(mask_s, self.nsat_g[gnss])  # Decode the mask and get the indices of the valid satellites
            for k in range(nclk):  # Loop for the number of available satellites
                dclk = bs.unpack_from('s' + str(self.dclk_blen), msg, i) \
                       * self.dclk_scl * (dcm + 1)  # Decode the clock correction value
                self.lc[0].dclk[idx_s[idx[k]]] = dclk  # Store the clock correction value
                i += self.dclk_blen
        return i

    # Decode the header information for each message
    def decode_head(self, msg, i, st=-1):

        if st == sCSSR.MASK:
            ui = 0
        else:
            ui = bs.unpack_from('u4', msg, i)[0]  # Decode the first element and assign to ui
            i += 4

        if self.tow0 >= 0:
            self.tow = self.tow0 + self.toh
            if self.week >= 0:
                self.time = gpst2time(self.week, self.tow)  # Calculate and convert the time

        head = {'uint': ui, 'mi': 0, 'iodssr': self.iodssr}  # Information type SSR version
        return head, i
    def decode_cssr(self, msg, i=0):
        if self.msgtype != 1:  # Only MT=1 is defined, check message type. If not 1, decoding fails
            print(f"invalid MT={self.msgtype}")
            return False
        # Time of hour
        # Flags: mask, orbit, clock, clock subset, cbias, pbias, mask_id, iodset_id
        self.toh, flags, res, mask_id, self.iodssr = \
            bs.unpack_from('u12u6u4u5u5', msg, i)  # The decoded values are assigned to time of hour, flags, res, mask ID, and iodssr.
        i += 32

        if self.monlevel > 0 and self.fh is not None:
            self.fh.write("##### Galileo HAS SSR: TOH{:6d} flags={:12s} mask_id={:2d} iod_s={:1d}\n"
                        .format(self.toh, bin(flags), mask_id, self.iodssr))

        if self.toh >= 3600:  # Check if toh is greater than or equal to 3600. If it is, return False to indicate decoding failure.
            print(f"invalid TOH={self.toh}")
            return False
        '''Check the 6th bit in the flags, which indicates whether the mask information (mask block) exists. 
        If it exists, set mask_id to the decoded mask identifier, and set subtype to sCSSR.MASK.
        Then, call decode_cssr_mask to decode the mask block of the HAS message.'''
        if (flags >> 5) & 1:  #
            self.mask_id = mask_id
            self.subtype = sCSSR.MASK
            i = self.decode_cssr_mask(msg, i)
        '''Check the 5th bit in the flags, which indicates whether the orbit (orbit block) information exists.
        If it exists, set subtype to sCSSR.ORBIT. Then call decode_cssr_orb to decode the orbit part of the HAS message to get orbit corrections. 
        If monlevel is greater than 0 and the file handle fh is not None, call out_log to output the decoded content.'''
        if (flags >> 4) & 1:  # orbit block
            self.subtype = sCSSR.ORBIT
            i = self.decode_cssr_orb(msg, i)
            if self.monlevel > 0 and self.fh is not None:
                self.out_log()
        '''Check the 4th bit in the flags, which indicates whether the clock (clock block) information exists.
        If it exists, set mask_id_clk to the decoded clock mask identifier, and set subtype to sCSSR.CLOCK.
        Then call decode_cssr_clk to decode the clock part of the HAS message to get clock corrections. 
        If monlevel is greater than 0 and the file handle fh is not None, call out_log to output the decoded content.'''
        if (flags >> 3) & 1:  # clock block
            self.mask_id_clk = mask_id
            self.subtype = sCSSR.CLOCK
            i = self.decode_cssr_clk(msg, i)
            if self.monlevel > 0 and self.fh is not None:
                self.out_log()
        '''Check the 3rd bit in the flags, which indicates whether the clock subset block (clock subset block) exists.
        If it exists, call decode_cssr_clk_sub to decode the clock subset part of the HAS message.'''
        if (flags >> 2) & 1:  # clock subset block
            i = self.decode_cssr_clk_sub(msg, i)
        '''Check the 2nd bit in the flags, which indicates whether the code bias (code bias block) exists.
        If it exists, set subtype to sCSSR.CBIAS. Then call decode_cssr_cbias to decode the code bias part of the HAS message.
        If monlevel is greater than 0 and the file handle fh is not None, call out_log to output the decoded content.'''
        if (flags >> 1) & 1:  # code bias block
            self.subtype = sCSSR.CBIAS
            i = self.decode_cssr_cbias(msg, i)
            if self.monlevel > 0 and self.fh is not None:
                self.out_log()
        '''Check the 1st bit in the flags, which indicates whether the phase bias (phase bias block) exists.
        If it exists, set subtype to sCSSR.PBIAS. Then call decode_cssr_pbias to decode the phase bias part of the HAS message.
        If monlevel is greater than 0 and the file handle fh is not None, call out_log to output the decoded content.'''
        if (flags >> 0) & 1:  # phase bias block
            self.subtype = sCSSR.PBIAS
            i = self.decode_cssr_pbias(msg, i)
            if self.monlevel > 0 and self.fh is not None:
                self.out_log()

    # Extract fields from the HAS page header
    def decode_has_header(self, buff, i):
        if bs.unpack_from('u24', buff, i)[0] == 0xaf3bc3:  # Decode the 24-bit unsigned integer and compare it with the predefined value 0xaf3bc3. If equal, it's an empty message, return a set of all zeros.
            return 0, 0, 0, 0, 0

        hass, res, mt, mid, ms, pid = bs.unpack_from('u2u2u2u5u5u8', buff, i)
        # If not an empty message, continue unpacking the HAS message header. This line uses unpack_from to decode six integers, each with 2, 2, 2, 5, 5, and 8 bits, 
        # corresponding to hass, res, mt, mid, ms, and pid.
        # hass indicates the HAS status, which is a 2-bit field in the HAS page header. It shows the status of the HAS service, e.g., "00" means test mode, "01" means operation mode.
        # If mt is not 1, decoding fails. res is reserved information. mid represents the message ID, a 5-bit field in the HAS page header, which uniquely identifies the message being transmitted.
        # ms represents the message size, indicating the size of the unencoded message in terms of pages.
        # pid represents the page ID, an 8-bit field in the HAS page header, which uniquely identifies the HAS encoded page being transmitted.

        ms += 1
        return hass, mt, mid, ms, pid

    # This method is very important because it recovers the complete HAS message from the received pages and extracts satellite correction information.
    def decode_has_page(self, idx, has_pages, gMat, ms):
        """ HPVRS decoding for RS(255,32,224) """
        HASmsg = bytes()
        k = len(idx)
        '''Use the generator matrix and page content to decode the HAS message. First, extract the corresponding page content from has_pages using the index list, 
        then represent this page content as a matrix Wd in the Galois field with dimensions k x 53. 
        At the same time, extract the corresponding part from the generator matrix, then perform an inverse matrix operation on it to get the inverse matrix Dinv with dimensions k x k.
        Next, multiply Dinv by Wd to get the decoded message Md with dimensions k x 53. Finally, convert Md to a byte object and assign it to HASmsg.'''
        if k >= ms:
            Wd = self.GF(has_pages[idx, :])  # kx53
            Dinv = np.linalg.inv(self.GF(gMat[idx, :k]))  # kxk
            Md = Dinv @ Wd  # decoded message (kx53)
            HASmsg = np.array(Md).tobytes()

        return HASmsg

    def log_msg(self,msg):
        if self.monlevel > 0 and self.fh is not None:
            self.fh.write(msg+"\n")

    def encode_SP3(self,HASData0,orb,nav,epoch_time,sp_out,nav_out,file_ssr):
        max_orbit_delay = 300
        max_clock_delay = 30
        encodeRTCM=1
        orbit_data = {}
        clock_data = {}
        ns = len(HASData0.sat_n)
        rs = np.ones((ns, 3))*np.nan
        vs = np.ones((ns, 3))*np.nan
        dts = np.ones((ns, 1))*np.nan

        d_rs = np.ones((ns, 3))*np.nan
        d_dts = np.ones((ns, 1))*np.nan
        peph = peph_t(epoch_time)
        for j, sat in enumerate(HASData0.sat_n):
            sys, prn = sat2prn(sat)
            sat_id= sat2id(sat)
            if not (sys == uGNSS.GPS or sys==uGNSS.GAL):
                continue

            if HASData0.iodssr_c[sCType.ORBIT] == HASData0.iodssr:
                if sat not in HASData0.sat_n:
                    continue
            else:
                continue

            iode = HASData0.lc[0].iode[sat]
            dorb = HASData0.lc[0].dorb[sat]  # radial,along-track,cross-track

            if HASData0.cssrmode == sCSSRTYPE.GAL_HAS_SIS:  # HAS only
                if HASData0.mask_id != HASData0.mask_id_clk:  # mask has changed
                    if sat not in HASData0.sat_n_p: #clock sat list
                        continue
            else:
                print("=======>Error: unrecongnized format for PPP")

            dclk = HASData0.lc[0].dclk[sat]

            if np.isnan(dclk) or np.isnan(dorb@dorb):
                continue

            if sys in HASData0.nav_mode.keys():
                mode = HASData0.nav_mode[sys]
            else:
                continue

            eph = findeph(nav.eph, epoch_time, sat, iode=iode, mode=mode)
            if eph is None:
                """
                print("ERROR: cannot find BRDC for {} mode {} iode {} at {}"
                      .format(sat2id(sat), mode, iode, time2str(time)))
                """
                continue
            if HASData0.mask_id != HASData0.mask_id_clk:  # mask has changed
                self.log_msg("ERROR: not matching id for orbit and clock, oribt_id= "+str(HASData0.mask_id)+" clock_id= "+str(HASData0.mask_id_clk)+"  "+time2str(epoch_time))
                continue
            rs[j, :], vs[j, :], dts[j] = eph2pos(epoch_time, eph, True)
            drel=eph2rel(epoch_time,eph)
            # Along-track, cross-track and radial conversion
            #
            er = vnorm(rs[j, :])
            rc = np.cross(rs[j, :], vs[j, :])
            ec = vnorm(rc)
            ea = np.cross(ec, er)
            A = np.array([er, ea, ec])
            # Convert orbit corrections from orbital frame to ECEF
            #
            dorb_e = dorb@A

            # Apply SSR correction
            #
            rs[j, :] -= dorb_e
            dts_brdc=dts[j]*rCST.CLIGHT
            dts[j] += dclk/rCST.CLIGHT  # [m] -> [s]


            peph.pos[sat-1,0]=rs[j,0]
            peph.pos[sat-1,1]=rs[j,1]
            peph.pos[sat-1,2]=rs[j,2]
            peph.pos[sat-1,3]=dts[j,0]-drel
            if sat not in sp_out.sat:
                sp_out.sat.append(sat)


            dtclk=timediff(epoch_time,HASData0.lc[0].t0[sat][sCType.CLOCK])
            dtorb=timediff(epoch_time,HASData0.lc[0].t0[sat][sCType.ORBIT])
            str_iod="nav_iod={:4d} mask_iod={:4d} ".format(HASData0.lc[0].iode[sat],HASData0.iodssr)
            if dtclk>max_clock_delay or dtorb>max_orbit_delay:
                self.log_msg("ERROR: large orbit/clock difference")
                self.log_msg("ERROR Data: "+str_iod)
                HASData0.deletePRN(sat)
                continue

            #encode orbit and clock products
            str_orbit = ('{}  {:4d} {:11.4f} {:11.4f} {:11.4f} {:11.4f} {:11.4f} {:11.4f}\n'. \
                         format(sat_id, iode, dorb[0], dorb[1], dorb[2], 0.0,0.0, 0.0))
            str_clock = ('{}  {:6d} {:11.4f} {:11.4f} {:11.4f} \n'.format(sat_id, iode, dclk, 0.0, 0.0))
            clock_data[sat_id] = str_clock
            orbit_data[sat_id] = str_orbit

        nsat_clock = len(clock_data)
        nsat_orbit = len(orbit_data)
        if nsat_orbit != nsat_clock or nsat_clock<15:
            str_error=">>>>error_time={} nsat_orbit={:4d} nsat_clock={:4d}".format(time2str(epoch_time),nsat_orbit,nsat_clock)
            self.log_msg(str_error)
            return

        nav_out.peph.append(peph)
        nav_out.ne+=1

        if encodeRTCM==1:
            e = time2epoch(epoch_time)
            str_time = "{:04d} {:02d} {:02d} {:02d} {:02d} {:02d}".format(e[0], e[1], e[2], e[3], e[4], int(e[5]))
            with open(file_ssr, 'a') as fp:
                fp.write('> CLOCK {} {}  {:4d} {} \n'.format(str_time, 0, nsat_clock, "HAS"))
                for sat_id, data in clock_data.items():
                    fp.write(data)
                fp.write('> ORBIT {} {}  {:4d} {} \n'.format(str_time, 0, nsat_orbit, "HAS"))
                for sat_id, data in orbit_data.items():
                    fp.write(data)
