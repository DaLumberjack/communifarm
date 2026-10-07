# ESP32-WROOM-32 D1 Mini Clone

Small ESP32-WROOM-32 development board in the D1 Mini footprint. Use it for lightweight Communifarm NFC readers, handheld scanners, and bench fixtures.

| Field | Value |
| --- | --- |
| Working name | ESP32-WROOM-32 D1 Mini clone / D1 Mini32 |
| Exact board class | Generic WEMOS-style D1 Mini ESP32 clone, commonly derived from MH-ET LIVE MiniKit |
| MCU | ESP32-WROOM-32 |
| ESPHome board id | `esp32dev` |
| Size | about 39 mm x 31 mm |
| USB / serial | Micro-USB, commonly CH340C |
| Flash | 4 MB typical |
| Logic voltage | 3.3 V GPIO only |
| Power input | Micro-USB 5 V or `5V` pin; board regulator provides `3V3` |
| Internal source image | `docs/intake/esp devices/esp32 wroom 32 d1 mini clone.png` |

## Safe First-Pick Pins

Prefer these pins before using strap, serial, JTAG, or flash-related pins.

| Purpose | GPIO | Board labels seen in source |
| --- | --- | --- |
| I2C SDA | `GPIO21` | `IO21`, `SDA`, `D2` |
| I2C SCL | `GPIO22` | `IO22`, `SCL`, `D1` |
| SPI MOSI | `GPIO23` | `IO23`, `MOSI`, `D7` |
| SPI MISO | `GPIO19` | `IO19`, `MISO`, `D6` |
| SPI SCK | `GPIO18` | `IO18`, `SCK`, `D5` |
| General output/input | `GPIO25` | `IO25` |
| General output/input | `GPIO26` | `IO26`, `D0` |
| General output/input | `GPIO27` | `IO27` |
| General output/input | `GPIO32` | `IO32` |
| General output/input | `GPIO33` | `IO33` |
| UART2 RX | `GPIO16` | `IO16`, `RX2`, `D4` |
| UART2 TX | `GPIO17` | `IO17`, `TX2`, `D3` |
| General input/output | `GPIO4` | `IO4` |

## Pins To Avoid For NFC Builds

| Pins | Why |
| --- | --- |
| `GPIO6`, `GPIO7`, `GPIO8`, `GPIO9`, `GPIO10`, `GPIO11` | Connected to module flash; do not use. |
| `GPIO0`, `GPIO2`, `GPIO5`, `GPIO12`, `GPIO15` | Boot strapping pins; use only when the connected module cannot pull them to the wrong state during reset. |
| `GPIO1`, `GPIO3` | USB serial/programming console. |
| `GPIO34`, `GPIO35`, `GPIO36`, `GPIO39` | Input-only; not suitable for chip select, reset, LEDs, or buzzers. |
| `GPIO12` | Especially risky: flash-voltage strap on classic ESP32 boards. |

## Recommended Communifarm NFC Pin Budget

| Reader role | Bus | Recommended D1 Mini32 pins | Notes |
| --- | --- | --- | --- |
| PN532 mobile scan-only | I2C | `SDA GPIO21`, `SCL GPIO22` | Lowest wire count. Set the PN532 board switches/jumpers to I2C. |
| RC522 bench/wired R/W test | SPI | `MOSI GPIO23`, `MISO GPIO19`, `SCK GPIO18`, `CS GPIO25`, `RST GPIO26` | Avoid the common ESP32 `GPIO5` CS pick because it is a boot strap pin on this board. |
| PN532 bench writer option | I2C or SPI | I2C pins above, or SPI bus above with unique `CS` | PN532 has ESPHome NDEF write examples; this is the better first choice for writable NFC payload experiments. |
| RC522 wireless test reader | SPI | Same as RC522 bench wiring | Use battery power only after measuring board idle/sleep current; this board is not a low-power battery design. |

## Electrical Notes

| Topic | Guidance |
| --- | --- |
| Voltage | Treat every GPIO as 3.3 V only. Do not feed 5 V signals into NFC pins. |
| Power | Start from USB power. If powering by `5V`, use a regulated 5 V source and common ground. |
| Current | PN532 modules can draw enough current that weak USB ports or long leads cause flaky reads. Keep wiring short for the first bring-up. |
| Antenna clearance | Keep the NFC antenna away from metal rails, wire bundles, and the ESP32 antenna edge. |
| Tag data model | Tags store stable references only, for example `cf://batch/<stable-id>` or `cf://asset/<stable-id>`. Mutable state stays in Communifarm storage. |

## ESPHome Skeleton

```yaml
esp32:
  board: esp32dev
  variant: esp32
  framework:
    type: esp-idf
```

## Sources

- ESPboards, "WEMOS D1 MINI ESP32 Pinout, Specs & Features", captured from `https://www.espboards.dev/esp32/d1-mini32/` on 2026-10-05. Pinout image is credited to ESPboards and licensed CC BY-NC 4.0.
- ESPHome documentation: `rc522` NFC/RFID component, PN532 NFC/RFID component, and SPI bus component.
