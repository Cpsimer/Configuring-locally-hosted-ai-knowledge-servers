network:
  devices:
    - id: ont
      name: "Alcatel‑Lucent G‑240W‑A FBG"
      type: optical_network_terminal
      notes: "Fiber ONT/modem feeding the rest of the network"

    - id: edge_router
      name: "Ubiquiti EdgeRouter X SFP"
      type: router
      notes: "Edge router that connects the ONT to the rest of the network"

    - id: usg1
      name: "UniFi Security Gateway1"
      type: gateway
      model: "First‑gen 3P"
      notes: "Firewall/security gateway with multiple LAN ports"

    - id: usg2
      name: "UniFi Security Gateway2"
      type: gateway
      model: "First‑gen 3P"
      notes: "Firewall/security gateway with multiple LAN ports"

    - id: uc_ap_pro
      name: "Ubiquiti AC Pro"
      type: Access point
      notes: "quantity is 3 that will be used to provide guest and personal connection”

    - id: express7
      name: "UniFi Express 7"
      type: router
      notes: "Unifi Express router whose WAN port uplinks to the edge router and LAN port feeds the switch"

    - id: flex_mini
      name: "UniFi Flex Mini"
      type: switch
      notes: "5‑port 2.5G switch distributing wired connections"

    - id: xps13
      name: "Dell XPS 13"
      type: laptop
      notes: "Personal laptop wired to the switch"

    - id: usb_adapter
      name: "2.5G USB‑C adapter"
      type: network_adapter
      notes: "2.5 Gbit USB‑C to Ethernet adapter connected to the switch"

    - id: desktop
      name: "Desktop workstation"
      type: workstation
      notes: "AI workstation wired directly into the USG"

    - id: xps15
      name: "Dell XPS 15"
      type: server
      notes: "Ubuntu home‑lab server; uses Wi‑Fi for connectivity"

    - id: cloud_key
      name: "UniFi Cloud Key Gen 1"
      type: controller
      notes: "Unifi Cloud Key used for network management"


  connections:
    # Uplink from fiber ONT to edge router
    - from_device: ont 
      from_port: WAN
      to_device: edge_router
      to_port: eth5/sfp
      cable_type: cat6 plus

    # Edge router to USG – USG’s WAN1 connection
    - from_device: edge_router
      from_port: eth4
      to_device: usg
      to_port: wan1
      cable_type: cat5e

    # Edge router to uc_ap_pri node to provide Wi‑Fi backhaul
    - from_device: edge_router
      from_port: eth3
      to_device: uc_ap_pro
      to_port: wan
      cable_type: cat5e

    # Edge router to UniFi Express 7 – Express 7’s WAN connection
    - from_device: edge_router
      from_port: eth0
      to_device: express7
      to_port: wan
      cable_type: cat6_plus STP

    # UniFi Express 7 (LAN) uplink to the Flex Mini switch
    - from_device: express7
      from_port: lan
      to_device: flex_mini
      to_port: eth5
      cable_type: UniFi Etherlighting Patch Cable 

    # Switch port assignments on the Flex Mini switch
    - from_device: flex_mini
      from_port: eth1
      to_device: xps13
      to_port: ethernet
      cable_type: cat6 

    # Flex Mini switch to the AI workstation
    - from_device: flex_mini
      from_port: eth2
      to_device: desktop
      to_port: ethernet
      cable_type: cat6 

    # Flex Mini switch to 2.5G USB‑C adapter
    - from_device: flex_mini
      from_port: eth3
      to_device: usb_adapter
      to_port: ethernet
      cable_type: cat6

    # Flex Mini switch to USG WAN1 (provides WAN segment on the USG)
    - from_device: flex_mini 
      from_port: eth4
      to_device: usg
      to_port: WAN1
      cable_type: cat5e

    # Flex Mini switch to UniFi Express 7 (LAN) uplink
    - from_device: flex_mini
      from_port: eth5
      to_device: UniFi Express 7
      to_port: lan
      cable_type: UniFi Etherlighting Patch Cable 


    # USG LAN1 to the WD NAS
    - from_device: usg
      from_port: lan1
      to_device: wd_nas
      to_port: ethernet
      cable_type: cat5e

    # USG LAN2 to the Unifi Cloud Key (as shown in the drawing)
    - from_device: usg
      from_port: lan2
      to_device: cloud_key
      to_port: ethernet
      cable_type: cat5e

