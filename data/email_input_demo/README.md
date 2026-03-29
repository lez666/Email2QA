# 虚构 `.eml` 演示集（测试 / 展示流程）

本目录中的 **`.eml` 样本为虚构测试数据**：联系人、公司、域名、单号与商业情节均经**去标识化**处理，不指向真实个人或真实客户；适用于在本地**跑通**「EML → Markdown → 脱敏 → QA」流水线，以及作为 **Demo 展示**或**算法回归测试**（正则、LLM 蒸馏等）。当前仓库内为 **20 封**；若你自行扩充，建议继续遵守下文构造原则。

---

## 数据安全与去标识化说明

生成这些测试数据时遵循 **「数据安全」** 与 **「去标识化」** 原则。构造逻辑如下。

### 1. 联系人姓名

- **英文名**：常见组合占位，如 Dr. Aris、Sarah Miller、Kevin 等。
- **中文名**：典型占位名，如 Li Ming（李明）、Chen Wei（陈伟）等。

### 2. 邮箱地址与域名

- **虚构域名**：看起来专业、但与本项目及真实客户无对应关系，例如  
  `nexus-robotics.de`、`z-robot-lab.edu.cn`、`autotech.com`、`silicon-valley-robotics.com`、`global-robots.com` 等。
- **用途**：便于测试 Email2QA 是否能识别**发件域 / 来源**等结构；**不**用于映射任何现实中的个人或组织。

### 3. 序列号 (SN) 与单号

- 如 `SN-HR-2024-001`、`Issue #9921` 等均为**按规则生成的占位符**，不代表真实库存或设备资产。

### 4. 商业噪音（干扰项）

- 文中出现的「发票（Invoice）」「清明假期」「电汇（Wire transfer）」等，用于**提高抽取难度**、模拟真实技术支持线程中的无关信息。
- 相关**金额、税号、银行账号等均无真实性**，不可用于任何财务或法律用途。

### 可以放心做什么

在确认未混入你自己业务中的真实数据的前提下，你可以：

- **公开展示 Demo**：展示 QA 抽取效果，无需担心泄露真实客户隐私（前提是展示内容仍来自本套虚构样本或同等去标识化数据）。
- **训练 / 测试模型**：验证正则、分类或 LLM 流程是否稳健。

本目录样本**不包含**真实微信、电话、详细住址或真实设备 SN 等可识别信息。

---

## 内容分组

| 文件前缀 | 主题 |
|----------|------|
| `01`–`07` | 感知 / Lidar（授权、串口与 UDP、结构共振、MTU、线缆长度、ROS2、PTP 等） |
| `08`–`14` | 运动控制（机器狗带载、人形翻滚安全、PPO 延迟、楼梯步态、力控、EMI、软地面等） |
| `15`–`20` | 硬件与综合（显卡驱动、BMS、财务/线缆/假期、RMA、散热、SN 维保） |

## 如何使用

在仓库根目录用**单独输出目录**，避免覆盖你真实的 `data/md_from_eml`：

```bash
mkdir -p data/md_from_eml_demo data/md_full_demo
chmod +x tools/Toolforeml2QA/batch-eml2md.sh
./tools/Toolforeml2QA/batch-eml2md.sh data/email_input_demo data/md_from_eml_demo
```

后续脱敏、抽 QA 时把 `--input-dir` / `--output-dir`（或 `process_email_qa` 的 `--input-dir` / `--output`）指到对应的 `_demo` 路径即可。

## 重新生成 `.eml`

若需改文案后批量重写文件：

```bash
python3 data/email_input_demo/build_demo_eml.py
```
