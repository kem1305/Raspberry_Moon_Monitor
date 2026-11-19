"""Moon Monitor v2 — single source of truth for the electrical design.

Used by build_pcb.py (board) and build_sch.py (schematic).  Coordinates are in millimetres in the
*rear view* of the gadget (looking at the component side, F.Cu):  u to the right, v up, origin at the
centre of the display.
"""

BOARD_R = 28.0          # outline: circle of this radius ...
FLAT_LEFT_U = -13.6     # ... cut by a chord on the left (the ESP32 antenna overhangs it)
FLAT_BOTTOM_V = -24.0   # ... and by a chord at the bottom (case floor)

# reference: (lib, footprint, value, u, v, rotation_deg, {pad: net}, LCSC part, description)
PARTS = {
    "U1": ("RF_Module", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R8", -7.0, 6.5, 90, {
        "1": "GND", "40": "GND", "41": "GND", "2": "+3V3", "3": "EN",
        "13": "USB_DN", "14": "USB_DP", "27": "BTN", "24": "LCD_PWR",
        "23": "P1", "22": "P2", "21": "P3", "20": "P4", "19": "P5", "18": "P6", "17": "P7",
    }, "C2913202", "Wi-Fi MCU module, 16 MB flash, 8 MB PSRAM"),
    "J1": ("Connector_USB", "USB_C_Receptacle_G-Switch_GT-USB-7051x", "USB-C vertical (GT-USB-7051A)", 0.0, -13.5, 0, {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
    }, "C2843970", "USB Type-C receptacle, 16P, vertical, 10.5 mm"),
    "J2": ("Connector_PinHeader_2.54mm", "PinHeader_1x07_P2.54mm_Vertical", "GC9A01 display", 23.5, 7.62, 0, {
        "1": "P1", "2": "P2", "3": "P3", "4": "P4", "5": "P5", "6": "P6", "7": "P7",
    }, "", "plated slots for the display module's own 1x7 pin header"),
    "SW1": ("Button_Switch_THT", "SW_Tactile_SPST_Angled_PTS645Vx39-2LFS", "PTS645VL39-2 LFS", -2.25, 23.4, 0, {
        "1": "BTN", "2": "GND",
    }, "", "right-angle 6 mm tactile switch (through-hole)"),
    "U2": ("Package_TO_SOT_SMD", "SOT-23-5", "AP2112K-3.3", -9.6, -9.9, 0, {
        "1": "VBUS_F", "2": "GND", "3": "VBUS_F", "5": "+3V3",
    }, "C51118", "3.3 V 600 mA LDO"),
    "U3": ("Package_TO_SOT_SMD", "SOT-23-6", "USBLC6-2SC6", 3.6, -6.9, 90, {
        "1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "2": "GND", "5": "VBUS",
    }, "C7519", "USB ESD protection"),
    "Q1": ("Package_TO_SOT_SMD", "SOT-23", "AO3401A", 13.5, 18.6, 0, {
        "1": "LCD_PWR", "2": "+3V3", "3": "VDISP",
    }, "C15127", "P-MOSFET, display power switch"),
    "F1": ("Fuse", "Fuse_1206_3216Metric", "PTC 500mA", -8.6, -15.3, 0, {
        "1": "VBUS_F", "2": "VBUS",
    }, "", "resettable fuse 0.5 A hold, >=6 V, 1206"),
    "R1": ("Resistor_SMD", "R_0603_1608Metric", "5.1k", -2.6, -9.4, 0, {"1": "GND", "2": "CC1"}, "C23186", "USB-C CC pull-down"),
    "R2": ("Resistor_SMD", "R_0603_1608Metric", "5.1k", 2.6, -17.6, 0, {"1": "CC2", "2": "GND"}, "C23186", "USB-C CC pull-down"),
    "R3": ("Resistor_SMD", "R_0603_1608Metric", "10k", -4.6, -5.0, 0, {"1": "EN", "2": "+3V3"}, "C25804", "EN pull-up"),
    "R4": ("Resistor_SMD", "R_0603_1608Metric", "10k", 8.0, 17.6, 0, {"1": "BTN", "2": "+3V3"}, "C25804", "button pull-up"),
    "R5": ("Resistor_SMD", "R_0603_1608Metric", "100k", 12.6, 22.0, 0, {"1": "LCD_PWR", "2": "GND"}, "C25803", "display on by default"),
    "C1": ("Capacitor_SMD", "C_0603_1608Metric", "10u", -9.6, -12.6, 0, {"1": "VBUS_F", "2": "GND"}, "C19702", "LDO input"),
    "C2": ("Capacitor_SMD", "C_0603_1608Metric", "10u", -6.3, -9.4, 90, {"1": "GND", "2": "+3V3"}, "C19702", "LDO output"),
    "C3": ("Capacitor_SMD", "C_0603_1608Metric", "10u", -11.4, -6.6, 0, {"1": "GND", "2": "+3V3"}, "C19702", "ESP32 bulk"),
    "C4": ("Capacitor_SMD", "C_0603_1608Metric", "100n", -11.6, -4.85, 0, {"1": "GND", "2": "+3V3"}, "C14663", "ESP32 decoupling"),
    "C5": ("Capacitor_SMD", "C_0603_1608Metric", "1u", -8.0, -5.0, 0, {"1": "EN", "2": "GND"}, "C15849", "EN power-on delay"),
    "C6": ("Capacitor_SMD", "C_0603_1608Metric", "100n", 8.0, 19.4, 0, {"1": "BTN", "2": "GND"}, "C14663", "button debounce"),
    "C7": ("Capacitor_SMD", "C_0603_1608Metric", "1u", 17.6, 16.0, 0, {"1": "VDISP", "2": "GND"}, "C15849", "display supply"),
    "JP1": ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "VCC@P1", 18.6, 12.4, 0, {"1": "VDISP", "2": "P1"}, "", "close if display pin at P1 is VCC"),
    "JP2": ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "VCC@P7", 18.6, -11.4, 0, {"1": "VDISP", "2": "P7"}, "", "close if display pin at P7 is VCC"),
    "JP3": ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "GND@P2", 14.2, 12.9, 0, {"1": "GND", "2": "P2"}, "", "close if display pin at P2 is GND"),
    "JP4": ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "GND@P6", 14.2, -9.4, 0, {"1": "GND", "2": "P6"}, "", "close if display pin at P6 is GND"),
    "TP1": ("TestPoint", "TestPoint_Pad_D1.5mm", "3V3", 9.0, -19.5, 0, {"1": "+3V3"}, "", "test pad"),
    "TP2": ("TestPoint", "TestPoint_Pad_D1.5mm", "GND", 12.0, -20.5, 0, {"1": "GND"}, "", "test pad"),
    "H1": ("MountingHole", "MountingHole_3.2mm_M3", "M3", -9.5, 22.37, 0, {}, "", "case screw"),
    "H2": ("MountingHole", "MountingHole_3.2mm_M3", "M3", 17.2, -17.2, 0, {}, "", "case screw"),
}

# routed track width per net (mm); everything else uses DEFAULT_WIDTH
DEFAULT_WIDTH = 0.2
NET_WIDTH = {"VBUS": 0.3, "VBUS_F": 0.4, "+3V3": 0.4, "VDISP": 0.3}
ROUTE_ORDER = ["USB_DP", "USB_DN", "VBUS", "VBUS_F", "+3V3", "EN", "BTN",
               "P1", "P2", "P3", "P4", "P5", "P6", "P7", "VDISP", "LCD_PWR"]

# display header: slot geometry (radial tolerance for the module's header position)
J2_SLOT = (5.0, 1.0)     # plated slot length (along u) x width
J2_PAD = (5.9, 1.75)
