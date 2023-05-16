import json
import glob
import ipaddress
import colorama
from colorama import Fore, Back, Style
from colorama import just_fix_windows_console
from colorama import init

###This function gathers imortant information from the txt files and creates a dictionary from it.######################
def create_dict(filename):
    with open(filename) as file:
        lines = file.readlines()
    conf = {}
    conf['Device Vlans'] = []
    conf['interfaces'] = {}
    conf['Routing Protocols'] = {}
    a = 0
    for item in lines:
        while (item.endswith('\n') or item.endswith('\t') or item.endswith(' ')) and len(item) > 1:
            item = item[:-1]
        if item.startswith('vlan '):
            conf['Device Vlans'] += [item[5:]]
        elif item.startswith('interface '):
            while not item[len(item) - 1].isdigit():
                item = item[:-1]
            a = 1
            intset = item[:]
            conf['interfaces'][intset] = {}
            conf['interfaces'][intset]['Shutdown'] = False
        elif a == 1:
            if item.__contains__('ip address '):
                while not item[len(item) - 1].isdigit():
                    item = item[:-1]
                if item[0] != ' ':
                    conf['interfaces'][intset]['ip address'] = item.split(' ')[2] + ' ' + item.split(' ')[3]
                else:
                    conf['interfaces'][intset]['ip address'] = item[12:]

            if item.startswith(' switchport mode'):
                conf['interfaces'][intset]['Switchport mode'] = item[17:]

            elif item.startswith(' channel-group'):
                conf['interfaces'][intset]['Channel-group'] = item[15:-8]

            elif item.startswith(' switchport trunk native vlan'):
                conf['interfaces'][intset]['Native Vlan'] = item[30:]

            elif item.startswith(' switchport trunk allowed vlan'):
                conf['interfaces'][intset]['Allowed vlans'] = item[31:]

            if item.startswith(' shutdown'):
                conf['interfaces'][intset]['Shutdown'] = True

            if item.__contains__('standby'):
                conf['interfaces'][intset]['standby id'] = item.split()[1]
                if item.__contains__('ip'):
                    conf['interfaces'][intset]['standby ip'] = item.split()[3]
                if item.__contains__('priority'):
                    conf['interfaces'][intset]['standby priority'] = item.split()[3]
                if item.__contains__('preempt'):
                    conf['interfaces'][intset]['standby preempt'] = True


        if item.startswith('router'):
            a = 2
            routeprot = item.split(' ')[1]
            protnum = item.split(' ')[2]
            if not routeprot in conf['Routing Protocols']:
                conf['Routing Protocols'][routeprot] = {}
            conf['Routing Protocols'][routeprot][protnum] = {}
            conf['Routing Protocols'][routeprot][protnum]['Networks'] = []
            if routeprot.startswith('bgp'):
                conf['Routing Protocols'][routeprot][protnum]['Neighbors'] = {}
        elif a == 2:
            if item.startswith(' network'):
                conf['Routing Protocols'][routeprot][protnum]['Networks'] += [item[9:]]
            if item.__contains__('redistribute'):
                if not 'Redistribute' in conf['Routing Protocols'][routeprot][protnum]:
                    conf['Routing Protocols'][routeprot][protnum]['Redistribute'] = []
                conf['Routing Protocols'][routeprot][protnum]['Redistribute'] += [item.split(' ')[2] + ' ' + item.split(' ')[3]]

            if item.__contains__(' remote-as'):
                conf['Routing Protocols'][routeprot][protnum]['Neighbors'][item.split(' ')[2]] = {}
                conf['Routing Protocols'][routeprot][protnum]['Neighbors'][item.split(' ')[2]]['ip'] = item.split(' ')[2]
                conf['Routing Protocols'][routeprot][protnum]['Neighbors'][item.split(' ')[2]]['remote-as'] = item.split(' ')[4]
            if item.__contains__(' update-source '):
                conf['Routing Protocols'][routeprot][protnum]['Neighbors'][item.split(' ')[2]]['update-source'] = item.split(' ')[4]

        # else:
        #     a = 0

    return conf

########################################################################################################################

def prittyfy(dict):
    json.dumps(dict, indent=4)



#input("Press Enter to start...")

# This part gathers all filenames inside of the same folder as the program and creates a dictionary with all of them.###


config = {}
txtfiles = []
txtfiles2 = []
for file in glob.glob("*.txt"):
    txtfiles.append(file)
for file in txtfiles:
    config[file[:-4]] = create_dict(file)
    txtfiles2.append(file[:-4])
txtfiles = txtfiles2
device_num = len(txtfiles)
# print(json.dumps(config, indent=4))

# config = {}
# txtfiles = []
# for folders in glob.glob("textfiles/*"):
#     print(folders)
#     for file in glob.glob(folders +"/*.txt"):
#         # file = file[len(folders)+1:]
#         txtfiles.append(file)
#         print(file)
#     for file in txtfiles:
#         config[file[len(folders)+1:]] = create_dict(file)
#         file = file[len(folders) + 1:]
#         print(file)
#         print(config)
#     device_num = len(txtfiles)



########################################################################################################################



#This part gives all those interfaces that have an ip address assigned, a connceted network to later check
#which interface is connected to which interface on another device.
#It then creates a neighbour list of which device every device is connected to.
topo = {}
for device in txtfiles:
    topo[device] = {}
    for item in config[device]['interfaces']:
        if 'ip address' in config[device]['interfaces'][item]:
            topo[device][item] = str(ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][item]['ip address'].split(' '))), strict=False))

#print(json.dumps(topo, indent=4))
### Neighbour list:

neighbours = {}
for device in topo:
    neighbours[device] = []
    for int, ip in topo[device].items():
        for device2 in topo:
            if device2 != device:
                for int2, ip2 in topo[device2].items():
                    if ip == ip2 and not device2 in neighbours[device]:
                        neighbours[device] += [device2]

#print(json.dumps(neighbours, indent=4))

# for device in topo:
#     print('\n', device)
#     for int, ip in topo[device].items():
#         for device2 in topo:
#             if device2 != device:
#                 for int2, ip2 in topo[device2].items():
#                     if ip == ip2:
#                         print('is connected to: ', device2)

########################################################################################################################


#This part checks if all portchannel-interfaces (that should be the same) are configured the same per device.###########

def portchannel_check(txtfiles, config):
    Pinfo_int_error = []
    portchannels = {}
    for device in txtfiles:
        portchannels[device] = {}
        for int in config[device]['interfaces']:
            if 'Channel-group' in config[device]['interfaces'][int]:
                if 'port-channel' + config[device]['interfaces'][int]['Channel-group'] in portchannels[device]:
                    prev_port += [int]
                    if config[device]['interfaces'][int] == portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']]:
                        portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']] = {}
                        portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']] = config[device]['interfaces'][int]
                    else:
                        for po_set in portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']]:
                            if portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']][po_set] != config[device]['interfaces'][int][po_set]:
                                Pinfo_int_error += (
                                '\n',
                                po_set, 'on', device, 'for', 'port-channel' + config[device]['interfaces'][int]['Channel-group'], 'is mismatched between these interfaces:'
                                )
                                for pp in prev_port:
                                    Pinfo_int_error += '\n ',pp, ': ', po_set, config[device]['interfaces'][pp][po_set]
                        portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']] = ['misconfigured']
                else:
                    portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']] = {}
                    portchannels[device]['port-channel' + config[device]['interfaces'][int]['Channel-group']] = config[device]['interfaces'][int]
                    prev_port = []
                    prev_port += [int]
    # print(json.dumps(portchannels, indent=4))

    ###This part compares the portchannels between the devices. ########################################################

    po_ch_problems = {}
    Pinfo_po_error = []
    for device in neighbours:
        for device2 in neighbours[device]:
            for po_ch, po_settings in portchannels[device].items():
                if po_ch in portchannels[device2]:
                    if po_settings != portchannels[device2][po_ch]:
                        if not device2 + ' and ' + device in po_ch_problems:
                            po_ch_problems[device + ' and ' + device2] = po_ch
                            Pinfo_po_error += ' \n', po_ch, 'between', device, 'and', device2, 'has mismatched configuration'
                            if 'misconfigured' in portchannels[device][po_ch]:
                                Pinfo_po_error += '\n ',device, 'has mismatched interfaces\n'
                            elif 'misconfigured' in portchannels[device2][po_ch]:
                                Pinfo_po_error += '\n ',device2, 'has mismatched interfaces'
                            else:
                                for po_check in po_settings:
                                    if portchannels[device][po_ch][po_check] != portchannels[device2][po_ch][po_check]:
                                        Pinfo_po_error += '\n ',device, po_check, portchannels[device][po_ch][po_check], '\n',' ','vs'
                                        Pinfo_po_error += '\n ',device2, po_check, portchannels[device2][po_ch][po_check], '\n'
    # print(prittyfy(po_ch_problems))
    return portchannels, Pinfo_int_error, Pinfo_po_error, po_ch_problems

########################################################################################################################


##This part will check bgp settings:####################################################################################

def bgp_tshoot_v2(txtfiles, config):
    bgp_connection_check = {}
    bgpentrycheck = {}
    bgpentrychecksource = {}
    Pinfo_bgp_error = []
    for device in txtfiles:
        if 'bgp' in config[device]['Routing Protocols']:
            for device2 in txtfiles:
                if 'bgp' in config[device2]['Routing Protocols'] and device != device2:
                    bgp_connection_check[device + device2] = {}
                    bgp_connection_check[device + device2]['as-matched'] = False
                    bgp_connection_check[device + device2]['ip-matched'] = False
                    bgp_connection_check[device + device2]['ip-matched2'] = False
                    bgp_connection_check[device + device2]['as-matched2'] = False
                    bgp_connection_check[device + device2]['info'] = []

    for device in txtfiles:
        if 'bgp' in config[device]['Routing Protocols']:
            bgpentrycheck[device] = {}
            bgpentrychecksource[device] = []
            for local_as in config[device]['Routing Protocols']['bgp']:
                for neighb in config[device]['Routing Protocols']['bgp'][local_as]['Neighbors']:
                    check = 0
                    for device2 in txtfiles:
                        if 'bgp' in config[device2]['Routing Protocols'] and device != device2:
                            if config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['remote-as'] in config[device2]['Routing Protocols']['bgp']:
                                check = 1
                                local_up_source = str(config[device]['interfaces']['interface ' + config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['update-source']]['ip address']).split(' ')[0]
                                bgp_connection_check[device + device2]['info'] += [local_as]
                                bgp_connection_check[device + device2]['info'] += [local_up_source]
                                remote_ip = neighb
                                bgp_connection_check[device + device2]['info'] += [remote_ip]
                                remote_as = config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['remote-as']
                                bgp_connection_check[device + device2]['info'] += [remote_as]
                                try: neighb_up_source = str(config[device2]['interfaces']['interface ' + config[device2]['Routing Protocols']['bgp'][config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['remote-as']]['Neighbors'][str(config[device]['interfaces']['interface ' + config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['update-source']]['ip address']).split(' ')[0]]['update-source']]['ip address']).split(' ')[0]
                                except: neighb_up_source = '0'
                                bgp_connection_check[device + device2]['info'] += [neighb_up_source]
                                try: neighb_remote_ip = config[device2]['Routing Protocols']['bgp'][remote_as]['Neighbors'][local_up_source]['ip']
                                except: neighb_remote_ip = '0'
                                bgp_connection_check[device + device2]['info'] += [neighb_remote_ip]
                                neighb_as = remote_as
                                bgp_connection_check[device + device2]['info'] += [neighb_as]
                                try: neighb_remote_as = config[device2]['Routing Protocols']['bgp'][remote_as]['Neighbors'][local_up_source]['remote-as']
                                except: neighb_remote_as = '0'
                                bgp_connection_check[device + device2]['info'] += [neighb_remote_as]
                                if local_as == neighb_remote_as:
                                    bgp_connection_check[device + device2]['as-matched2'] = True
                                if local_up_source == neighb_remote_ip:
                                    bgp_connection_check[device + device2]['ip-matched2'] = True
                                if remote_ip == neighb_up_source:
                                    bgp_connection_check[device + device2]['ip-matched'] = True
                                if remote_as == neighb_as:
                                    bgp_connection_check[device + device2]['as-matched'] = True
                            else: local_up_source = 0
                    bgpentrychecksource[device] += [local_up_source]
                    if check == 0:
                        bgpentrycheck[device][neighb] = ['\n no matches found for', device + "'s", 'bgp entry: ', 'neighbour', config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['ip'], 'remote-as', config[device]['Routing Protocols']['bgp'][local_as]['Neighbors'][neighb]['remote-as']]
    for device in bgpentrycheck:
        for device3 in bgpentrycheck:
            if device != device3:
                for entry in bgpentrychecksource[device]:
                    if entry in bgpentrycheck[device3]:
                        bgpentrycheck[device3].pop(entry)

    check_mem = []
    for device in txtfiles:
        for device2 in txtfiles:
            if device + device2 in bgp_connection_check and not device2 + device in check_mem:
                check_mem += [device + device2]
                check = 0
                for setting in 'as-matched2', 'ip-matched2', 'as-matched', 'ip-matched':
                    # print(setting)
                    if bgp_connection_check[device2 + device][setting] != bgp_connection_check[device + device2][setting]:
                        check += 1
                if check > 0:
                    Pinfo_bgp_error += '\n There is a pairing error between', device, 'and', device2
                    if bgp_connection_check[device + device2]['as-matched'] == False:
                        Pinfo_bgp_error += '\n  The remote-as of',bgp_connection_check[device + device2]['info'][6],'on', device2, 'did not match the AS of', bgp_connection_check[device + device2]['info'][7], 'on', device
                    if bgp_connection_check[device + device2]['as-matched2'] == False:
                        Pinfo_bgp_error += '\n  The remote-as of',bgp_connection_check[device + device2]['info'][7],'on', device2, 'did not match the AS of', bgp_connection_check[device + device2]['info'][0], 'on', device
                    if bgp_connection_check[device + device2]['ip-matched'] == False:
                        Pinfo_bgp_error += '\n  The neighbour ip of', bgp_connection_check[device + device2]['info'][2], 'on', device, 'did not match the update-source of', bgp_connection_check[device + device2]['info'][4], 'on', device2
                    if bgp_connection_check[device + device2]['ip-matched2'] == False:
                        Pinfo_bgp_error += '\n  The neighbour ip on', device2, 'did not match the interface or update-source on', device
                    Pinfo_bgp_error += '\n'
                if check == 0 and bgp_connection_check[device2 + device]['info'] != []:
                    Pinfo_bgp_error += '\n the bgp connection detected between', device, 'and', device2, 'looks good\n'

    for info in bgpentrycheck:
        for info3 in bgpentrycheck[info].values():
            Pinfo_bgp_error += info3

    # print(prittyfy(bgp_connection_check))

    return Pinfo_bgp_error






########################################################################################################################

### This part will make an ospf-networks list per device. ##############################################################

def ospflistmkr(txtfiles, config):
    ospflist = {}
    for device in txtfiles:
        ospflist[device] = {}
        if 'ospf' in config[device]['Routing Protocols']:
            for ospf_num in config[device]['Routing Protocols']['ospf']:
                ospflist[device][ospf_num] =[]
                for item in config[device]['Routing Protocols']['ospf'][ospf_num]['Networks']:
                    if item.split(' ')[1] == '0.0.0.0': ospfnet = (ipaddress.IPv4Network((ipaddress.IPv4Interface((item.split(' ')[0] + '/' + item.split(' ')[1])).with_hostmask), strict=False))
                    else: ospfnet = (ipaddress.IPv4Network((item.split(' ')[0] + '/' + item.split(' ')[1]), strict=False))
                    ospflist[device][ospf_num] += [str(ospfnet)]
    return ospflist



########################################################################################################################

### This part will check if all OSPF entries are directly connected networks.###########################################


def OSPF_Connected_net(txtfiles, config, topo):
    Pinfo_ospf_int_error = []
    for device in txtfiles:
        if 'ospf' in config[device]['Routing Protocols']:
            for ospf_num in config[device]['Routing Protocols']['ospf']:
                for item in config[device]['Routing Protocols']['ospf'][ospf_num]['Networks']:
                    check = 0
                    if item.split(' ')[1] == '0.0.0.0': ospfnet = (ipaddress.IPv4Network((ipaddress.IPv4Interface((item.split(' ')[0] + '/' + item.split(' ')[1])).with_hostmask), strict=False))
                    else: ospfnet = (ipaddress.IPv4Network((item.split(' ')[0] + '/' + item.split(' ')[1]), strict=False))
                    for int, network in topo[device].items():
                        if str(ospfnet) == str(network):
                            check = 1
                    if check == 0:
                        Pinfo_ospf_int_error += '\n', 'Failed to find a connected network for',device + "'s", 'ospf', ospf_num, 'entry', item

    return Pinfo_ospf_int_error

########################################################################################################################


### This part will check what interfaces with an ip does not have an ospf entry. #######################################
not_yet_routed = {}
def OSPF_int_check(txtfiles, config, topo):
    for device in txtfiles:
        if 'ospf' in config[device]['Routing Protocols']:
            for int, network in topo[device].items():
                check = 0
                for ospf_num in config[device]['Routing Protocols']['ospf']:
                    for item in config[device]['Routing Protocols']['ospf'][ospf_num]['Networks']:
                        if item.split(' ')[1] == '0.0.0.0':
                            ospfnet = (ipaddress.IPv4Network((ipaddress.IPv4Interface((item.split(' ')[0] + '/' + item.split(' ')[1])).with_hostmask), strict=False))
                        else:
                            ospfnet = (ipaddress.IPv4Network((item.split(' ')[0] + '/' + item.split(' ')[1]), strict=False))
                        if str(ospfnet) == str(network):
                            check = 1
                if check == 0:
                    if not device in not_yet_routed:
                        not_yet_routed[device] = []
                    # print('No ospf entry on', device, 'for', int, network)
                    not_yet_routed[device] += [network]



########################################################################################################################


###This part will compare ospf entries with neigbours to see if they share an entry (in order to create adjaceny). #####

def ospf_neighbors(config, txtfiles, ospflist):
    checked_err = []
    Pinfo_ospf_neighbours = []
    for device in txtfiles:
        for ospf_num in ospflist[device]:
            for device2 in neighbours[device]:
                if 'ospf' in config[device2]['Routing Protocols']:
                    check = 0
                    for entry in ospflist[device][ospf_num]:
                            for ospf_num2 in ospflist[device2]:
                                for entry2 in ospflist[device2][ospf_num2]:
                                    if entry == entry2:
                                        check = 1
                    if check == 0 and not device2 + device in checked_err:
                        Pinfo_ospf_neighbours += [" \n These two devices didn't share an ospf entry \n "]
                        Pinfo_ospf_neighbours += [device, 'and', device2]
                        checked_err += [device + device2]

    return Pinfo_ospf_neighbours

########################################################################################################################


### This part will make an eigrp-networks list per device. #########################################################################

def eigrplistmkr(txtfiles, config):
    eigrplist = {}
    for device in txtfiles:
        if 'eigrp' in config[device]['Routing Protocols']:
            eigrplist[device] = {}
            for eigrp_num in config[device]['Routing Protocols']['eigrp']:
                eigrplist[device][eigrp_num] =[]
                for item in config[device]['Routing Protocols']['eigrp'][eigrp_num]['Networks']:
                    if item.split(' ')[1] == '0.0.0.0': eigrpnet = (ipaddress.IPv4Network((ipaddress.IPv4Interface((item.split(' ')[0] + '/' + item.split(' ')[1])).with_hostmask), strict=False))
                    else: eigrpnet = (ipaddress.IPv4Network((item.split(' ')[0] + '/' + item.split(' ')[1]), strict=False))
                    eigrplist[device][eigrp_num] += [str(eigrpnet)]
    return eigrplist

########################################################################################################################



### This part will check if all OSPF entries are directly connected networks.###########################################

def EIGRP_Connected_net(topo, eigrplist):
    Pinfo_EIGRP_error = []
    for device in eigrplist:
        for eigrp_num in eigrplist[device]:
            for eigrpnet in eigrplist[device][eigrp_num]:
                check = 0
                for int, network in topo[device].items():
                    if str(eigrpnet) == str(network):
                        check = 1
                        if network in not_yet_routed[device]:
                            not_yet_routed[device] = list(set(not_yet_routed[device]) - set([network]))


                if check == 0:
                    Pinfo_EIGRP_error += '\n', device, 'Error: failed to find a connected network for the eigrp', eigrp_num, 'entry', eigrpnet, '\n'
                    if not device in not_yet_routed:
                        not_yet_routed[device] = []
                    if not network in not_yet_routed[device]:
                        Pinfo_EIGRP_error += '\n No eigrp entry on', device, 'for', int, network
                        not_yet_routed[device] += [network]

    return Pinfo_EIGRP_error

########################################################################################################################



### Here i will try to check if all vlans on trunks that should be between two devices are there. ######################

# Firts i create a dict of all vlans that two devices share.

def vlan_on_trunks():
    Pinfo_trunk_error = []
    vlans_between = {}
    for device in txtfiles:
        if config[device]['Device Vlans']:
            for device2 in neighbours[device]:
                if config[device2]['Device Vlans']:
                    if not device2 + ' and '+ device in vlans_between:
                        vlans_between[device + ' and '+ device2] = []
                        for vlan in config[device]['Device Vlans']:
                            if vlan in config[device2]['Device Vlans']:
                                vlans_between[device + ' and '+ device2] += [vlan]


# Then i create a dict of all allowed vlans per connection.
    checked = []
    allowed_vlan_list = {}
    for device in portchannels:
        for device2 in portchannels:
            if not device == device2:
                for po_ch in portchannels[device]:
                    if not po_ch in checked:
                        if po_ch in portchannels[device2]:
                            checked += [po_ch]
                            if not po_ch in po_ch_problems.values():
                                allowed_vlan_list[device + ' and '+ device2] = str(portchannels[device][po_ch]['Allowed vlans']).split(',')
                                allowed_vlan_list[device + ' and '+ device2] += [portchannels[device][po_ch]['Native Vlan']]
                            # else:
                            #     Pinfo_trunk_error += '\n \n', 'error checking', po_ch, ': misconfigured between the devices', device, 'and', device2

# Lastly i compare these two dictionaries.
    missing_vlans = {}
    for pair in vlans_between:
        missing_vlans[pair] = []
        if pair in allowed_vlan_list:
            set1 = set(vlans_between[pair])
            set2 = set(allowed_vlan_list[pair])
            if set1 - set2 > set2 - set1:
                missing_vlans[pair] = list(set1 - set2)
            else:
                missing_vlans[pair] = list(set2 - set1)

    for pair in missing_vlans:
        if missing_vlans[pair]:
            Pinfo_trunk_error += '\n \n There is no trunk between', pair, 'to support these vlans:\n '
            Pinfo_trunk_error += [', '.join(missing_vlans[pair])]

    return Pinfo_trunk_error

########################################################################################################################


### This part checks HSRP ##############################################################################################



def HSRP_peers():
    # First we check if the standby ip is within the same network as the interface ip ###
    Pinfo_HSRP_error = []
    dev_mem = []
    standby_ip_fail = {}
    for device in txtfiles:
        dev_mem += [device]
        for int in config[device]['interfaces']:
            if 'standby id' in config[device]['interfaces'][int]:
                # if ipaddress.IPv4Address(config[device]['interfaces'][int]['standby ip']) in ipaddress.IPv4Network('/'.join(str(config[device]['interfaces'][int]['ip address']).split(' '))):
                if not str(ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False)) in standby_ip_fail:
                    standby_ip_fail[str(ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False))] = []
                if not ipaddress.IPv4Address(config[device]['interfaces'][int]['standby ip']) in ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False):

                    standby_ip_fail[str(ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False))] += [device + "'s " + int]
                else: standby_ip_fail[str(ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False))] += ['passed']


# Then we check if those that should be the same are the same ###########################

                for device2 in txtfiles:
                    if device != device2 and not device2 in dev_mem:
                        for int2 in config[device2]['interfaces']:
                            if 'standby id' in config[device2]['interfaces'][int2]:
                                if ipaddress.IPv4Network(('/'.join(config[device2]['interfaces'][int2]['ip address'].split(' '))), strict=False) == ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False):

                                    if not config[device2]['interfaces'][int2]['standby id'] == config[device]['interfaces'][int]['standby id']:
                                        Pinfo_HSRP_error += "\n These standby id's do not match as they should:\n  Standby", config[device]['interfaces'][int]['standby id'], 'on', device + "'s", int, '\n  Standby', config[device2]['interfaces'][int2]['standby id'], 'on', device2 + "'s", int2, '\n'
                                    if not config[device2]['interfaces'][int2]['standby ip'] == config[device]['interfaces'][int]['standby ip']:
                                        if not ipaddress.IPv4Address(config[device]['interfaces'][int]['standby ip']) in ipaddress.IPv4Network(('/'.join(config[device]['interfaces'][int]['ip address'].split(' '))), strict=False):
                                            Pinfo_HSRP_error += '\n', config[device]['interfaces'][int]['standby ip'], int, device, '\n  Should be changed to:', config[device2]['interfaces'][int2]['standby ip'], '\n'
                                        elif not ipaddress.IPv4Address(config[device2]['interfaces'][int2]['standby ip']) in ipaddress.IPv4Network(('/'.join(config[device2]['interfaces'][int2]['ip address'].split(' '))), strict=False):
                                            Pinfo_HSRP_error += '\n The standby ip on', device2 + "'s",int2, 'is', config[device2]['interfaces'][int2]['standby ip'], '\n  But should be changed to:', config[device]['interfaces'][int]['standby ip'], '\n'
                                        else: Pinfo_HSRP_error += '\n The standby ip on', device, int, 'and', device2, int2, 'does not match'
    for item in standby_ip_fail:
        if not 'passed' in standby_ip_fail[item]:
            Pinfo_HSRP_error += '\n No standby-ip was configured correctly for this network:', item, '\n These interfaces were all on a different network:'
            for i in standby_ip_fail[item]:
                Pinfo_HSRP_error += '\n ', i
    # print(prittyfy(standby_ip_fail))
    return Pinfo_HSRP_error

########################################################################################################################

### This part will check the redistribute settings #####################################################################

def redistribute_check():
    Pinfo_redistribute_error = []
    for device in txtfiles:
        for protocol in config[device]['Routing Protocols']:
            for protnum in config[device]['Routing Protocols'][protocol]:
                if 'Redistribute' in config[device]['Routing Protocols'][protocol][protnum]:
                    for item in config[device]['Routing Protocols'][protocol][protnum]['Redistribute']:
                        if item.split(' ')[0] in config[device]['Routing Protocols']:
                            if not item.split(' ')[1] in config[device]['Routing Protocols'][item.split(' ')[0]]:
                                Pinfo_redistribute_error += '\n There is an error with the redistribute command on',device + "'s",  protocol, protnum, '\n ', item, 'does not exist on this device\n'

    return Pinfo_redistribute_error

########################################################################################################################

### This part checks what networks are not being routed ################################################################

def non_routed_networks():
    Pinfo_non_routed_networks = []
    # for device in txtfiles:
    #     if 'bgp' in config[device]['Routing Protocols']:
    #         for AS in config[device]['Routing Protocols']['bgp']:
    #
    for device in not_yet_routed:
        for network in not_yet_routed[device]:
            Pinfo_non_routed_networks += '\n', device + "'s", 'network', network, 'is not being routed through eigrp or ospf\n'

    return Pinfo_non_routed_networks

########################################################################################################################

### This gathers all info ##############################################################################################

try:
    ospflist = ospflistmkr(txtfiles, config)
except:
    print('encountered an error with the ospf check')

# print(json.dumps(config, indent=4))
try:
    portchannels, Pinfo_int_error, Pinfo_po_error, po_ch_problems = portchannel_check(txtfiles, config)
except:
    print('encountered an error with the portchannel check')

# bgp_tshoot(txtfiles, config)
try:
    Pinfo_bgp_error = bgp_tshoot_v2(txtfiles, config)
except:
    print('encountered an error with the bgp check')

try:
    Pinfo_ospf_int_error = OSPF_Connected_net(txtfiles, config, topo)
except:
    print('encountered an error with the ospf check')

try:
    OSPF_int_check(txtfiles, config, topo)
except:
    print('encountered an error with the ospf check')

try:
    Pinfo_ospf_neighbours = ospf_neighbors(config, txtfiles, ospflist)
except:
    print('encountered an error with the ospf check')

try:
    Pinfo_trunk_error = vlan_on_trunks()
except:
    print('encountered an error with the trunk check')

try:
    eigrplist = eigrplistmkr(txtfiles, config)
except:
    print('encountered an error with the EIGRP check')
try:
    Pinfo_EIGRP_error = EIGRP_Connected_net(topo, eigrplist)
except:
    print('encountered an error with the EIGRP check')

try:
    Pinfo_HSRP_error = HSRP_peers()
except:
    print('encountered an error with the HSRP check')
try:
    Pinfo_redistribute_error = redistribute_check()
except:
    print('encountered an error with the Redistribution check')

try:
    Pinfo_non_routed_networks = non_routed_networks()
except:
    print('encountered an error with the routing check')



### This part prints everything#########################################################################################
#
# print('text')
# print('texty')
# print(not_yet_routed)
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_bgp_error))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_trunk_error))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_int_error))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_po_error))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_ospf_int_error))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_ospf_neighbours))
# # print('\n''\x1b[7;30;41m''###########################################################################'+'\x1b[0m')
# # print(' '.join(Pinfo_HSRP_error))

#Detta är outputen. Vad tycker du om färgerna? Tänkte rött och guld som varning men har inga problem med att ändra. /Nathalie
init()
just_fix_windows_console()

RED = "\033[1;31;40m"
WHITE ="\033[1;47;40m"
YELLOW ="\033[4;30;103m"
RESET = "\033[0m"

print(RED + "#################################################################################################")
print(RESET + YELLOW + "Trunks:", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_trunk_error)+'\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "Port-channels:", end='')
try:
    print(RESET + WHITE +' '.join(Pinfo_int_error) + '\n'+' '.join(Pinfo_po_error))
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "OSPF", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_ospf_int_error) + '\n' + ' '.join(Pinfo_ospf_neighbours)+'\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "EIGRP", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_EIGRP_error) +'\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "Redistribute", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_redistribute_error) +'\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")

print(RESET + YELLOW + "BGP", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_bgp_error) + '\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "HSRP", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_HSRP_error) + '\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")
print(RESET + YELLOW + "Non-routed networks", end='')
try:
    print(RESET + WHITE + ' '.join(Pinfo_non_routed_networks) + '\n')
except:
    print(RESET + WHITE + '\n\t ERROR' +'\n')
print(RED + "#################################################################################################")

########################################################################################################################


input("Press Enter to Exit...")


