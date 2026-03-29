#!/usr/bin/env python3
"""一次性生成虚构演示用 .eml（人物、公司与 SN 均为编造）。运行后可直接删除本脚本。"""
from __future__ import annotations

import email.policy
from email.message import EmailMessage
from pathlib import Path

OUT = Path(__file__).resolve().parent
TO = "support@demo-robotics.example"


def save(mid: str, subject: str, frm: str, body: str, date: str) -> None:
    msg = EmailMessage(policy=email.policy.default)
    msg["From"] = frm
    msg["To"] = TO
    msg["Subject"] = subject
    msg["Date"] = date
    msg["Message-ID"] = f"<{mid}@fictional.demo>"
    msg.set_content(body.strip() + "\n", charset="utf-8")
    path = OUT / f"{mid}.eml"
    path.write_bytes(msg.as_bytes(policy=email.policy.SMTP))


def main() -> None:
    demos: list[tuple[str, str, str, str, str]] = [
        (
            "01_lidar_license_nexus",
            "Re: [Issue #9921] Lidar ysn check failed on Orin NX",
            '"Dr. Aris" <a.rivers@nexus-robotics.de>',
            """Hi,

We are testing the Lidar on our new AGV. The pointcloud in RViz is empty.
The terminal shows: "ysn check failed: license not found".
We checked the /etc/udev/rules.d but nothing changed.

By the way, we still haven't received the commercial invoice for the last 3 units.
Our finance team needs it for the Q1 audit. Can you send it?""",
            "Mon, 03 Mar 2025 09:15:22 +0000",
        ),
        (
            "02_lidar_udp_serial",
            "AW: Lidar Connection Timeout",
            '"Li Ming" <liming@z-robot-lab.edu.cn>',
            """你好，我们在连接 Lidar 时一直报错 SDK_TIMEOUT。
我们直接尝试用 UDP Port 2 进行连接，但是 ping 不通。
是不是因为固件版本太低？

---
Reply:
请先不要使用 UDP Port 2。请优先通过 Serial Port 1（串口）进行初始连接和激活。
激活完成后才能切换到以太网模式。""",
            "Mon, 03 Mar 2025 11:02:00 +0800",
        ),
        (
            "03_lidar_vibration_mount",
            "Re: High-speed vibration on Lidar Pointcloud",
            '"Sarah Miller" <s.miller@autotech.com>',
            """The Lidar hardware itself is fine. But when the robot moves at 2.5m/s, the pointcloud jitters.
Could this be a firmware bug in the IMU fusion?

---
Reply:
Please check the mounting structure. We suggest adding 30-degree silicone dampeners.
Structural resonance is often mistaken for sensor failure.""",
            "Tue, 04 Mar 2025 14:33:10 -0500",
        ),
        (
            "04_lidar_mtu_jumbo",
            "Re: Lidar gigabit stream incomplete / MTU",
            '"Jan Vogel" <j.vogel@eu-mobile-robotics.eu>',
            """We only receive partial frames on the Lidar topic over GigE. Wireshark shows fragmentation.
Should we enable jumbo frames (MTU 9000) on the Orin NX interface, or keep 1500 and lower the packet rate?

---
Reply:
Start with MTU 1500 and verify switch port settings. If the network supports end-to-end jumbo frames, MTU 9000 can help for high-rate pointcloud streams; otherwise enable software packet reassembly in the driver.""",
            "Wed, 05 Mar 2025 08:40:00 +0100",
        ),
        (
            "05_lidar_cable_length",
            "Cable length limit for Lidar Ethernet",
            '"Ops Team" <ops@warehouse-bot.jp>',
            """We need to place the Lidar 18m away from the IPC. With Cat6A we still see occasional timeouts.
What is the maximum recommended cable length for your sensor at full rate?

---
Reply:
For full-rate operation we recommend <= 15m passive copper with quality shielding. Beyond that, use a fiber media converter pair or an industrial Ethernet repeater.""",
            "Wed, 05 Mar 2025 22:10:00 +0900",
        ),
        (
            "06_lidar_ros2_dds_qos",
            "ROS2 Foxy pointcloud drops / DDS tuning",
            '"Alex" <alex@ros-field-test.io>',
            """On ROS2 Foxy we subscribe to /points but lose ~5% of messages under load.
Which DDS (Fast-DDS vs Cyclone) do you recommend, and what QoS profile for sensor_data?

---
Reply:
Use RELIABLE only for low-rate commands; for pointclouds prefer BEST_EFFORT with history depth 5–10. Cyclone DDS often behaves better on congested Wi‑Fi; on wired LAN tune recv buffer sizes per our tuning guide.""",
            "Thu, 06 Mar 2025 16:45:00 +0000",
        ),
        (
            "07_lidar_ptp_sync",
            "Multi-Lidar time synchronization (PTP)",
            '"R&D B" <rdb@lidar-testbed.org>',
            """We run two Lidars on the same robot. Pointclouds look misaligned in fusion.
Do we need PTP (IEEE 1588) on the switch, or is NTP on the host enough?

---
Reply:
For motion compensation, PTP hardware timestamping is strongly recommended. NTP-only is usually insufficient above 1 m/s base motion.""",
            "Fri, 07 Mar 2025 10:05:00 +0000",
        ),
        (
            "08_robotdog_payload_lean",
            "Robot Dog leaning 6 degrees during payload test",
            '"Kevin" <k.tech@silicon-valley-robotics.com>',
            """Hi Team,

Our Robot Dog is carrying a 3kg compute pack. It leans to the right by about 6 degrees.
The controller input is neutral. Is it an IMU bias?

---
Reply:
Check if the center of gravity (CoG) is centered.
Even a 1cm offset can cause the pose compensation to tilt.""",
            "Mon, 10 Mar 2025 18:22:00 -0700",
        ),
        (
            "09_humanoid_flip_safety",
            "Humanoid Robot Flip action failed - joint safety trigger",
            '"Research Group A" <rga@robot-institute.org>',
            """We tried the 'Front Flip' command on the Humanoid Robot.
The robot starts the jump but shuts down mid-air.
Error log: "Knee joint torque limit exceeded".

PS: Regarding the refund, please update the wire transfer info.""",
            "Tue, 11 Mar 2025 09:30:00 +0000",
        ),
        (
            "10_humanoid_ppo_latency",
            "Inference latency on Humanoid Robot using PPO policies",
            '"Chen Wei" <chenwei@ai-unit.com>',
            """我们在 Humanoid Robot 上部署了训练好的 PPO 模型，但是推断延迟达到了 15ms。
这导致机器人在不平整地面上无法保持平衡。
你们建议开启哪种 TensorRT 优化模式？""",
            "Tue, 11 Mar 2025 15:18:00 +0800",
        ),
        (
            "11_quadruped_stairs_gait",
            "Quadruped stair climbing gait instability",
            '"Maya" <maya@legged-lab.edu>',
            """Our Robot Dog slips on the third step when using the default stair gait.
IMU looks stable. Do you have a recommended foot placement policy for 18cm risers?""",
            "Wed, 12 Mar 2025 11:00:00 +0000",
        ),
        (
            "12_humanoid_wrist_force",
            "Humanoid wrist force limit during manipulation",
            '"Tom" <tom@manip-ai.co>',
            """We get FORCE_LIMIT on the right wrist when grasping 2.1kg boxes.
Spec says 3kg payload — is that under quasi-static assumption only?""",
            "Wed, 12 Mar 2025 17:45:00 +0000",
        ),
        (
            "13_robotdog_emi_noise",
            "EMI causing encoder glitches near VFD",
            '"Site Eng" <eng@factory-floor.au>',
            """Near variable-frequency drives we see sporadic encoder jumps on two legs.
Any shielding or cable routing checklist for Robot Dog deployments?""",
            "Thu, 13 Mar 2025 02:20:00 +1100",
        ),
        (
            "14_humanoid_com_walking",
            "COM oscillation when walking on soft ground",
            '"Field Test" <field@outdoor-humanoid.org>',
            """On wet grass the Humanoid Robot oscillates in sagittal plane at 0.4Hz.
Is this a terrain estimator issue or controller gain scheduling?""",
            "Thu, 13 Mar 2025 13:10:00 +0000",
        ),
        (
            "15_sim_nvidia_driver",
            "Ubuntu 20.04 NVIDIA Driver for Humanoid Robot simulation",
            '"Lab Manager" <manager@neuro-link.de>',
            """We are setting up the simulation node for the Humanoid Robot.
The default drivers in Ubuntu 20.04 are not working with our RTX 4060.
Should we manually install version 525?
Also, the invoice you sent was missing the VAT number.""",
            "Fri, 14 Mar 2025 09:00:00 +0100",
        ),
        (
            "16_robotdog_bms_20pct",
            "Robot Dog shutdown at low battery voltage",
            '"Field Tech" <tech@agri-bot.io>',
            """Our Robot Dog shuts down unexpectedly when the battery hits 20%.
Is there a BMS firmware update for the 48V system?
We need this fixed before our field test next week.""",
            "Fri, 14 Mar 2025 14:55:00 +0000",
        ),
        (
            "17_finance_cable_holiday",
            "RE: Cable length and Payment confirmation",
            '"Finance Dept" <finance@global-robots.com>',
            """1. We've paid for the 10 units of Robot Dog.
2. Technical: Can we extend the Lidar cable to 5 meters?
3. Our office will be closed from April 4th to 6th for the holiday.""",
            "Mon, 17 Mar 2025 08:30:00 +0000",
        ),
        (
            "18_spare_rma_shipping",
            "RMA: spare knee actuator shipping delay",
            '"Logistics" <ship@parts-depot.eu>',
            """Tracking shows the knee actuator RMA stuck in customs for 5 days.
Can you provide a commercial invoice copy with HS code for clearance?""",
            "Mon, 17 Mar 2025 11:20:00 +0000",
        ),
        (
            "19_noise_fan_throttle",
            "Thermal throttle during outdoor summer demo",
            '"Events" <events@show-floor.us>',
            """Ambient 38C — Jetson throttles and whole-body control latency spikes.
Any chassis airflow mod you recommend for Robot Dog outdoor booths?""",
            "Tue, 18 Mar 2025 19:00:00 -0400",
        ),
        (
            "20_sn_warranty_summary",
            "Re: Annual Maintenance for Humanoid Robot Units",
            '"Inventory Manager" <inv@robot-hub.com>',
            """Please verify the SN list for the 20 Humanoid Robot units in our lab.
Unit #SN-HR-2024-001 is showing battery drain issues.
Is it covered under warranty?

Best Regards,
Sent from my iPad""",
            "Wed, 19 Mar 2025 07:12:00 +0000",
        ),
    ]

    for mid, subject, frm, body, date in demos:
        save(mid, subject, frm, body, date)
    print(f"Wrote {len(demos)} files to {OUT}")


if __name__ == "__main__":
    main()
