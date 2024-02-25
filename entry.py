import shutil
import json
import os
import modules.keygen as keygen
from jinja2 import Environment, FileSystemLoader

folder_path = 'output'  # Replace with the path to your folder

try:
    shutil.rmtree(folder_path)
except Exception as e:
    print(f"Error deleting {folder_path}: {e}")

# opening peer.json config
with open('config.json', 'r') as file:
    # load JSON data from file
    try:
        config = json.load(file)
    except Exception as e:
        print(f"config.json: {e}\nExiting...")
        exit()

# opening data.json working file
try:
    with open('data.json', 'r') as file:
    # load JSON data from file
        try:
            data = json.load(file)
        except Exception as e:
            raise Exception
except Exception as e:
    print(f"data.json: {e}\nCreating new data.json...")
    data = {}


config_ids = set(site["id"] for site in config["sites"])
data_ids = set(int(key) for key in data.keys())

if config_ids != data_ids:
    new_ids = config_ids - data_ids
    for id in new_ids:
        key = keygen.generate()
        data[id] = key
            
    deleted_ids = data_ids - config_ids

    for id in deleted_ids: del data[str(id)]

    for i, (id, value) in enumerate(data.items()):
        print(len(value.get("preshared_key",[])), len(config_ids)-i-1)
        if not value.get("preshared_key"):
            psk_list=[]
            for j in range(len(config_ids)-i-1):
                psk_list.append(keygen.preshared())
            value["preshared_key"] = psk_list
        elif len(value.get("preshared_key")) < len(config_ids)-i-1:
            for j in range(len(config_ids)-i-1 - len(value.get("preshared_key"))):
                value["preshared_key"].append(keygen.preshared())
        elif len(value.get("preshared_key")) > len(config_ids)-i-1:
            value["preshared_key"] = value["preshared_key"][:len(config_ids)-i-1]
            print(value["preshared_key"])

with open('data.json', 'w') as file:
    json.dump(data, file, indent=2)

# generate the wg.conf files
environment = Environment(loader=FileSystemLoader("templates/"))
template = environment.get_template(f"wireguard.tmpl")

for site in config["sites"]:
    
    print(f"Generating configuration files for {site['name']}")
    count = 0

    for peer in config["sites"]:
        if site is not peer:

            # generate matching pair of preshared-keys and ports
            if site['id'] < peer['id']:
                peer_port = site.get("port", config["port"]) + site['id']
                preshared_key = data[str(site["id"])]["preshared_key"][peer['id']-site['id']-1]
            else:
                peer_port = site.get("port", config["port"]) + site['id'] - 1
                preshared_key = data[str(peer["id"])]["preshared_key"][site['id']-peer['id']-1]
            
            listen_port = site.get("port", config["port"]) + count
            count += 1
                
            
            #first render
            content = template.render(
                interface_name=f"wg{site['id']}.{peer['id']}",
                private_key=data[str(site["id"])]["private_key"],
                peer_ip=peer.get("local", f"10.201.{peer['id']}.1"),
                peer_ip_v6=peer.get("local_v6", f"fd09:93c7:f67b:{peer['id']:x}::1"),
                preup=site.get("preup", None),
                postup=site.get("postup", None),
                predown=site.get("predown", None),
                postdown=site.get("postdown", None),
                listen_port=listen_port,
                mtu=min(peer.get("mtu", float('inf')), site.get("mtu", float('inf')), config["mtu"]),
                peer_name=peer["name"],
                peer_public=data[str(peer["id"])]["public_key"],
                preshared_key=preshared_key,
                peer_endpoint=peer.get("endpoint", None),
                peer_port=peer_port,
                keep_alive=min(peer.get("keepalive", float('inf')), site.get("keepalive", float('inf')), config["keepalive"]),
                interface_custom=site.get("interface_custom", None),
                peer_custom=site.get("peer_custom", None)
            )
            
            intermediate = environment.from_string(content)
            
            #second render for post rules
            content = intermediate.render(
                listen_port=listen_port,
                interface_name=f"wg{site['id']}.{peer['id']}",
                interface_mss=min(peer.get("mtu", float('inf')), site.get("mtu", float('inf')), config["mtu"]) - 60 # ipv6 header size
            ).strip()
            
            #output configs
            output_directory = f"output/{site['name']}"
            output_file = f"{output_directory}/wg{site['id']}.{peer['id']}.conf"
            os.makedirs(output_directory, exist_ok=True)

            with open(output_file, mode="w", encoding="utf-8") as message:
                message.write(content)
                print(f"... wrote {output_file}")
            
            listen_port +=1