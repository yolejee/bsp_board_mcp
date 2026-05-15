# WiFi/BT 调试指南

## 1. WiFi 模组驱动加载

### 1.1 常见 WiFi 模组与驱动
```
模组/芯片         接口      驱动模块              固件路径
────────────────────────────────────────────────────────────
RTL8723BS        SDIO      r8723bs / rtw88       /lib/firmware/rtlwifi/
RTL8723DU        USB       rtl8xxxu / rtw88      /lib/firmware/rtlwifi/
RTL8188FTV       USB       rtl8xxxu              /lib/firmware/rtlwifi/
RTL8821CS        SDIO      rtw88_8821cs          /lib/firmware/rtw88/
RTL8822CE        PCIe      rtw89                 /lib/firmware/rtw89/
AP6212           SDIO      brcmfmac              /lib/firmware/brcm/
AP6255           SDIO      brcmfmac              /lib/firmware/brcm/
AP6275S          SDIO      brcmfmac              /lib/firmware/brcm/
CYW43455         SDIO      brcmfmac              /lib/firmware/brcm/
QCA6174          PCIe      ath10k / ath10k_pci   /lib/firmware/ath10k/
MT7601U          USB       mt7601u               /lib/firmware/mt7601u.bin
AW-NB197NF       PCIe     ath10k_pci            /lib/firmware/ath10k/
```

### 1.2 驱动加载排查
```bash
# 检查模组是否被识别:
lsusb                                  # USB 模组
lspci                                  # PCIe 模组
cat /sys/bus/sdio/devices/*/device     # SDIO 模组

# 检查驱动是否加载:
lsmod | grep -i wifi
lsmod | grep -iE "brcmfmac|rtw|ath|mt76"

# 检查固件:
dmesg | grep -i firmware
# "Direct firmware load for brcm/brcmfmac43455-sdio.bin failed"
# → 缺少固件文件

# 固件文件命名规则 (brcmfmac 为例):
# /lib/firmware/brcm/brcmfmac43455-sdio.bin          # 主固件
# /lib/firmware/brcm/brcmfmac43455-sdio.txt          # NVRAM 配置
# /lib/firmware/brcm/brcmfmac43455-sdio.clm_blob     # 国家码表

# SDIO WiFi DTS 配置示例:
# &sdmmc1 {
#     bus-width = <4>;
#     cap-sd-highspeed;
#     cap-sdio-irq;
#     keep-power-in-suspend;
#     non-removable;
#     sd-uhs-sdr104;
#     status = "okay";
# };
```

## 2. wpa_supplicant 高级配置

### 2.1 完整配置文件
```
# /etc/wpa_supplicant/wpa_supplicant.conf
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0
update_config=1
country=CN

# WPA2-Personal
network={
    ssid="MyWiFi"
    psk="password123"
    key_mgmt=WPA-PSK
    proto=RSN
    pairwise=CCMP
    group=CCMP
    priority=10
}

# WPA2-Enterprise
network={
    ssid="EnterpriseWiFi"
    key_mgmt=WPA-EAP
    eap=PEAP
    identity="user@domain"
    password="password"
    phase2="auth=MSCHAPV2"
    priority=5
}

# 开放网络
network={
    ssid="OpenWiFi"
    key_mgmt=NONE
    priority=1
}

# 隐藏 SSID
network={
    ssid="HiddenWiFi"
    scan_ssid=1
    psk="password"
    key_mgmt=WPA-PSK
}
```

### 2.2 wpa_cli 常用命令
```bash
wpa_cli -i wlan0
> status                    # 当前状态
> scan                      # 触发扫描
> scan_results              # 查看扫描结果
> list_networks             # 已配置网络
> select_network 0          # 选择网络
> disconnect                # 断开
> reconnect                 # 重连
> signal_poll               # 信号强度
> log_level DEBUG           # 设置调试级别
```

## 3. hostapd (AP 模式)

```
# /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=MyAP
hw_mode=g              # a=5GHz, g=2.4GHz
channel=6
ieee80211n=1            # 802.11n
wmm_enabled=1
auth_algs=1
wpa=2
wpa_passphrase=password123
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP

# 启动:
hostapd /etc/hostapd/hostapd.conf -dd   # debug 模式

# 配合 dnsmasq 做 DHCP:
# /etc/dnsmasq.conf
# interface=wlan0
# dhcp-range=192.168.4.2,192.168.4.100,24h
```

## 4. 蓝牙 HCI 调试

### 4.1 HCI 协议栈
```
应用层 (BlueZ)
    ↓
L2CAP / SDP / RFCOMM / A2DP / HFP
    ↓
HCI (Host Controller Interface)
    ↓
传输层: UART (H4/H5) / USB / SDIO
    ↓
蓝牙控制器 (芯片)
```

### 4.2 HCI 调试命令
```bash
# 查看 HCI 设备:
hciconfig -a
# hci0:   Type: Primary  Bus: UART
#         BD Address: AA:BB:CC:DD:EE:FF
#         UP RUNNING

# 复位:
hciconfig hci0 reset

# btmon 实时监控:
btmon &
# 然后执行蓝牙操作, btmon 会显示 HCI 事件和数据

# 常见蓝牙问题:
# 1. "Can't init device hci0: Connection timed out"
#    → 控制器未响应, 检查 UART 波特率/供电/固件
# 2. 扫描不到设备
#    → rfkill unblock bluetooth
#    → hciconfig hci0 piscan  (设为可被发现)
# 3. 配对失败
#    → btmon 查看具体的 HCI 错误码
#    → 清除配对信息: bluetoothctl remove <MAC>
```

## 5. WiFi/BT 共存 (Coexistence)

```
同芯片 WiFi+BT 共存机制:
- TDM (时分复用): WiFi 和 BT 轮流使用天线
- 共存协议: 协调 WiFi TX/RX 和 BT TX/RX 的时序

常见共存问题:
- WiFi 传输时 BT 断连
- BT 音频播放时 WiFi 吞吐显著下降
- 2.4GHz 频段互相干扰

排查:
1. 检查共存固件是否正确加载
2. dmesg 搜索 coex 相关日志
3. 尝试将 WiFi 切到 5GHz 频段避免干扰
4. 某些模组有共存参数可调 (参考模组厂商文档)
```
